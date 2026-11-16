"""Retrieve Day 7 chunks through TF-IDF, Day 6 pgvector, or RRF."""
import json
from pathlib import Path
import sys

from baseline import TfidfIndex
from convert_day6 import convert_chunk


class Day6Dense:
    def __init__(self, day6: Path, database_url: str, chunks: list[dict]):
        # Reuse the original embedding and cosine search implementations.
        sys.path.insert(0, str(day6 / 'starter'))
        from src.embeddings import MyEmbedder
        from src.store import PgVectorStore

        config = json.loads((day6 / 'starter/embedding_config.json').read_text(encoding='utf-8'))
        signature = {key: config[key] for key in (
            'model_name', 'revision', 'pooling', 'query_document_processing', 'max_sequence_tokens'
        )}
        self.store = PgVectorStore(database_url, config['dimensions'], signature)
        with self.store.connect() as conn:
            row = conn.execute('SELECT signature FROM day6_pipeline.embedding_config WHERE id = 1').fetchone()
            if row is None or row[0] != {**signature, 'dimensions': config['dimensions']}:
                raise ValueError('Cấu hình embedding trong pgvector khác Day 6')
            rows = conn.execute(
                """SELECT chunk_id, document_id, source, page, text, metadata
                   FROM day6_pipeline.chunks WHERE strategy = 'C'"""
            ).fetchall()
        fields = ('id', 'source_id', 'source', 'page', 'text', 'metadata')
        self.chunks = {chunk['id']: chunk for chunk in chunks}
        if {row[0]: dict(zip(fields, row)) for row in rows} != self.chunks:
            raise ValueError('Snapshot pgvector C khác corpus Day 7')
        self.embedder = MyEmbedder(config['model_name'], config['revision'], day6 / config['cache_folder'])
        if self.embedder.dimensions != config['dimensions']:
            raise ValueError('Số chiều embedding khác cấu hình pgvector')
        self.config = {**signature, 'dimensions': config['dimensions'], 'index_strategy': 'C'}

    def search(self, query, *, filters, top_k):
        vector = self.embedder.embed_query(query)
        hits = self.store.search('C', vector, filters=filters, top_k=top_k)
        results = []
        for hit in hits:
            chunk = convert_chunk(hit)
            if self.chunks.get(chunk['id']) != chunk:
                raise ValueError('Chunk trả về khác corpus Day 7')
            results.append({**chunk, 'strategy': 'dense', 'score': hit['score'], 'distance': hit['distance']})
        return results


def validate_filter(filters):
    if filters is None:
        return
    if not isinstance(filters, dict) or set(filters) != {'verse_start', 'verse_end'}:
        raise ValueError('Bộ lọc phải có verse_start.lte và verse_end.gte')
    upper = filters['verse_start']
    lower = filters['verse_end']
    if not isinstance(upper, dict) or not isinstance(lower, dict) or set(upper) != {'lte'} or set(lower) != {'gte'}:
        raise ValueError('Bộ lọc phải có verse_start.lte và verse_end.gte')
    if type(upper['lte']) is not int or type(lower['gte']) is not int or not 1 <= lower['gte'] <= upper['lte'] <= 3254:
        raise ValueError('Phạm vi lọc phải nằm trong 1–3254')


class Retrieval:
    def __init__(self, chunks, strategy, *, dense=None, candidate_k=20, rrf_k=60):
        self.strategy = strategy
        self.lexical = TfidfIndex(chunks) if strategy in ('tfidf', 'hybrid') else None
        self.dense = dense
        self.corpus_size = len(chunks)
        self.candidate_k = candidate_k
        self.rrf_k = rrf_k
        if strategy not in ('tfidf', 'dense', 'hybrid') or (strategy != 'tfidf' and dense is None):
            raise ValueError('Cấu hình retrieval không hợp lệ')
        if candidate_k < 1 or rrf_k < 1:
            raise ValueError('candidate_k và rrf_k phải dương')

    def search(self, query, *, filters, top_k):
        validate_filter(filters)
        if self.strategy == 'dense':
            return self.dense.search(query, filters=filters, top_k=top_k)
        depth = top_k if self.strategy == 'tfidf' else max(top_k, self.candidate_k)
        lexical = self.lexical.search(query, self.corpus_size if filters else depth)
        if filters:
            lexical = [
                row for row in lexical
                if row['metadata']['verse_start'] <= filters['verse_start']['lte']
                and row['metadata']['verse_end'] >= filters['verse_end']['gte']
            ][:depth]
        if self.strategy == 'tfidf':
            return lexical

        dense = self.dense.search(query, filters=filters, top_k=depth)
        fused = {}
        for rows in (lexical, dense):
            for rank, chunk in enumerate(rows, 1):
                entry = fused.setdefault(chunk['id'], {
                    **chunk, 'strategy': 'hybrid', 'score': 0.0, 'components': {},
                })
                entry.pop('distance', None)
                entry['components'][chunk['strategy']] = {'rank': rank, 'score': chunk['score']}
                entry['score'] += 1 / (self.rrf_k + rank)
        return sorted(fused.values(), key=lambda row: (-row['score'], row['id']))[:top_k]

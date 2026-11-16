"""Run one retrieval or agent query against the Day 7 Truyện Kiều corpus."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
from time import perf_counter

from agentic import run_agent
from model_controller import ChatController
from retrieval import Day6Dense, Retrieval, validate_filter


ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / 'data/truyen-kieu/chunks.json'
DEFAULT_DAY6 = ROOT.parent / 'K5-L3B-DAY06-NguyenMinhQuan-2A202603794-DataIngestion'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--question', required=True)
    parser.add_argument('--query-id')
    parser.add_argument('--strategy', choices=('tfidf', 'dense', 'hybrid'), required=True)
    parser.add_argument('--retrieve-only', action='store_true')
    parser.add_argument('--provider', choices=('openrouter', 'gemini'), default='openrouter')
    parser.add_argument('--day6-root', type=Path, default=DEFAULT_DAY6)
    parser.add_argument('--verse-range', nargs=2, type=int, metavar=('START', 'END'))
    parser.add_argument('--top-k', type=int, default=3)
    parser.add_argument('--candidate-k', type=int, default=20)
    parser.add_argument('--rrf-k', type=int, default=60)
    parser.add_argument('--budget', type=int, default=800, help='Context budget in characters')
    parser.add_argument('--max-searches', type=int, default=4)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.question.strip() or min(args.top_k, args.candidate_k, args.rrf_k, args.budget, args.max_searches) < 1:
        parser.error('Câu hỏi phải có nội dung và các giới hạn phải dương')
    filters = None
    if args.verse_range:
        start, end = args.verse_range
        filters = {'verse_start': {'lte': end}, 'verse_end': {'gte': start}}
    try:
        validate_filter(filters)
    except ValueError as error:
        parser.error(str(error))

    corpus_bytes = CORPUS.read_bytes()
    chunks = json.loads(corpus_bytes)
    trace = {
        'query_id': args.query_id, 'question': args.question, 'strategy': args.strategy, 'filter': filters,
        'corpus_sha256': sha256(corpus_bytes).hexdigest(), 'chunk_count': len(chunks),
        'top_k': args.top_k, 'candidate_k': args.candidate_k, 'rrf_k': args.rrf_k,
        'context_budget_chars': args.budget, 'max_searches': args.max_searches,
    }
    if not args.retrieve_only:
        trace['provider'] = args.provider
        default_model = 'gemini-3.8-flash' if args.provider == 'gemini' else None
        trace['model'] = os.environ.get(f'{args.provider.upper()}_MODEL') or default_model
    events = []
    controller = None
    started = perf_counter()
    stage = 'setup'
    try:
        if not args.retrieve_only:
            stage = 'model_setup'
            controller = ChatController(trace['model'], os.environ.get(f'{args.provider.upper()}_API_KEY'),
                                        provider=args.provider)
        dense = None
        if args.strategy != 'tfidf':
            stage = 'pgvector_setup'
            database_url = os.environ.get('DATABASE_URL')
            if not database_url:
                raise ValueError('Cần đặt DATABASE_URL cho pgvector Day 6')
            dense = Day6Dense(args.day6_root.resolve(), database_url, chunks)
            trace['embedding'] = dense.config
        retriever = Retrieval(chunks, args.strategy, dense=dense, candidate_k=args.candidate_k, rrf_k=args.rrf_k)
        trace['setup_ms'] = (perf_counter() - started) * 1000
        if args.retrieve_only:
            stage = 'retrieval'
            retrieval_started = perf_counter()
            results = retriever.search(args.question, filters=filters, top_k=args.top_k)
            trace.update(status='retrieved', hits=results,
                         retrieval_ms=(perf_counter() - retrieval_started) * 1000)
        else:
            stage = 'agent'
            trace.update(run_agent(args.question, controller, retriever, filters=filters, top_k=args.top_k,
                                   budget=args.budget, max_searches=args.max_searches, events=events))
    except Exception as error:
        message = str(error)
        for key in ('DATABASE_URL', 'OPENROUTER_API_KEY', 'GEMINI_API_KEY'):
            secret = os.environ.get(key)
            if secret:
                message = message.replace(secret, '[redacted]')
        trace.update(status='error', error={'stage': stage, 'type': type(error).__name__, 'message': message},
                     events=events, citations=[])
        last_search = next((event for event in reversed(events) if event['event'] == 'search'), {})
        trace.update(context=last_search.get('context', ''), context_ids=last_search.get('context_ids', []))
    trace['elapsed_ms'] = (perf_counter() - started) * 1000
    if controller is not None:
        trace['model_calls'] = controller.calls
        costs = [(call.get('usage') or {}).get('cost') for call in controller.calls]
        trace['service_cost_usd'] = sum(costs) if all(isinstance(cost, (int, float)) for cost in costs) else None
    elif args.retrieve_only:
        trace['service_cost_usd'] = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(trace, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if trace['status'] == 'error':
        parser.exit(1, f"{trace['error']['stage']}: {trace['error']['message']}\nTrace: {args.output}\n")
    print(f"{trace['status']}: {args.output}")


if __name__ == '__main__':
    main()

"""Bounded agent loop shared by the adapters and offline tests."""
from time import perf_counter
from typing import Any, Protocol
from baseline import pack_context


class Controller(Protocol):
    def decide(self, question: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        """Call a real model with a search tool; return normalized action.

        Search: {'action': 'search', 'query': '...'}.
        Final: {'action': 'answer', 'answer': '...', 'citations': ['chunk-id']}.
        Citations must also appear as [chunk-id] in the answer text.
        Abstention: {'action': 'abstain'}.
        """
        ...


class Retriever(Protocol):
    def search(self, query: str, *, filters: dict[str, Any] | None, top_k: int) -> list[dict[str, Any]]:
        """Query the real Day 6 vector store with a compatible query embedding.

        Return each chunk's id, text, source_id, source, page, metadata and score.
        The query embedding model and dimension must match the document index.
        """
        ...


def run_agent(question: str, controller: Controller, retriever: Retriever, *,
              filters: dict[str, Any] | None = None, max_searches: int = 4,
              top_k: int = 3, budget: int = 800,
              events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return answer, citation IDs and trace; no benchmark gold enters this loop.

    A final answer without valid citations, an empty context, and a search limit
    lead to abstention. This only checks citation IDs, not semantic grounding.
    Provider/retriever errors propagate; no silent mock fallback.
    """
    if not question.strip() or max_searches < 1 or top_k < 1 or budget < 1:
        raise ValueError('question, max_searches, top_k hoặc budget không hợp lệ')
    history: list[dict[str, Any]] = []
    chunks: dict[str, dict[str, Any]] = {}
    candidates: list[dict[str, Any]] = []
    events = [] if events is None else events

    def finish(status, event, answer='Không đủ bằng chứng để trả lời.', citations=None):
        events.append({'event': event})
        latest = history[0] if history else {}
        return {'status': status, 'answer': answer, 'citations': citations or [], 'events': events,
                'context': latest.get('context', ''), 'context_ids': latest.get('context_ids', [])}

    for _ in range(max_searches + 1):
        action = controller.decide(question, history)
        if action.get('action') == 'search':
            if sum(e['event'] == 'search' for e in events) >= max_searches:
                return finish('abstain', 'search_limit')
            query = action.get('query')
            if not isinstance(query, str) or not query.strip():
                raise ValueError('search query phải là chuỗi không rỗng')
            started = perf_counter()
            try:
                results = retriever.search(query, filters=filters, top_k=top_k)
            except Exception:
                events.append({'event': 'search_error', 'query': query, 'filter': filters,
                               'elapsed_ms': (perf_counter() - started) * 1000})
                raise
            elapsed_ms = (perf_counter() - started) * 1000
            if len(results) > top_k or len({r['id'] for r in results}) != len(results):
                raise ValueError('retriever phải trả tối đa top_k chunk ID duy nhất')
            candidates.extend(results)
            context, ids = pack_context(candidates, budget=budget)
            chunks = {c['id']: c for c in candidates if c['id'] in ids}
            events.append({'event': 'search', 'query': query, 'filter': filters, 'results': results,
                           'context': context, 'context_ids': ids, 'elapsed_ms': elapsed_ms})
            # Send only the latest cumulative context; avoid multiplying the budget.
            history = [{'tool': 'search', 'queries': [e['query'] for e in events if e['event'] == 'search'],
                        'context': context, 'context_ids': ids}]
        elif action.get('action') == 'answer':
            answer, citations = action.get('answer'), action.get('citations')
            if not isinstance(answer, str) or not isinstance(citations, list) or any(not isinstance(i, str) for i in citations):
                raise ValueError('answer/citations không hợp lệ')
            valid = bool(answer.strip() and citations and all(i in chunks and f'[{i}]' in answer for i in citations))
            if valid:
                return finish('answered', 'answer', answer, citations)
            return finish('abstain', 'invalid_or_missing_citations')
        elif action.get('action') == 'abstain':
            return finish('abstain', 'model_abstained' if history else 'abstained_without_search')
        else:
            raise ValueError('action phải là search, answer hoặc abstain')
    return finish('abstain', 'search_limit')

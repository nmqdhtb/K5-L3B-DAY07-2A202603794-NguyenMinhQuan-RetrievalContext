"""Compare configurations on dev or run the frozen pair on held-out test."""
import argparse
from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
from statistics import median
from time import perf_counter

from agentic import run_agent
from baseline import hit, pack_context, validate
from model_controller import ChatController
from retrieval import Day6Dense, Retrieval
from run_truyen_kieu import CORPUS, DEFAULT_DAY6


STOP_GUIDANCE = (
    'Sau mỗi lượt tìm, xác định chi tiết còn thiếu. Chỉ tìm lại nếu có manh mối mới '
    'và query mới nhắm vào chi tiết đó. Khi các đoạn tìm được chỉ nhắc tới chủ đề '
    'mà không cung cấp chi tiết được hỏi, hãy dùng finish với status=abstain '
    'nếu không còn manh mối cụ thể. Không tìm lại chỉ bằng cách lặp tên nhân vật hoặc địa điểm.'
)
CONFIGS = {
    'tfidf': ('tfidf', 800, ''),
    'dense': ('dense', 800, ''),
    'hybrid': ('hybrid', 800, ''),
    'hybrid_budget': ('hybrid', 1600, ''),
    'hybrid_stop': ('hybrid', 800, STOP_GUIDANCE),
}


def write_json(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def metric(values):
    values = list(values)
    count = sum(values)
    return {'n': count, 'N': len(values), 'rate': count / len(values) if values else None}


def total_if_known(values):
    values = list(values)
    return sum(values) if values and all(isinstance(v, (int, float)) for v in values) else None


def summarize(rows, *, retrieval_only):
    positives = [row for row in rows if row['answerable']]
    ranked = [row for row in positives if 'hit3' in row]
    result = {
        'questions': len(rows), 'errors': [row['query_id'] for row in rows if row['status'] == 'error'],
        'ranking_errors': [row['query_id'] for row in positives if 'hit3' not in row],
        'hit1': metric(row['hit1'] for row in ranked),
        'evidence_hit3': metric(row['hit3'] for row in ranked),
        'median_retrieval_ms': median(row['retrieval_ms'] for row in ranked) if ranked else None,
    }
    if retrieval_only:
        result['packed_evidence_rate'] = metric(row['packed_hit'] for row in ranked)
        return result

    successful = [row for row in rows if row['status'] in ('answered', 'abstain')]
    positive_runs = [row for row in successful if row['answerable']]
    negative_runs = [row for row in successful if not row['answerable']]
    result.update(
        context_evidence_rate=metric(row['context_hit'] for row in positive_runs),
        tool_use=metric(row['searches'] > 0 for row in successful),
        search_counts=dict(sorted(Counter(row['searches'] for row in successful).items())),
        search_limits=sum(row['terminal_event'] == 'search_limit' for row in successful),
        searched_then_abstained=metric(row['searches'] > 0 and row['status'] == 'abstain' for row in negative_runs),
        false_abstention=metric(row['status'] == 'abstain' for row in positive_runs),
        median_agent_ms=median(row['agent_ms'] for row in successful) if successful else None,
        agent_ms_total=sum(row.get('agent_ms', 0) for row in rows),
        prompt_tokens=total_if_known(row['prompt_tokens'] for row in rows),
        completion_tokens=total_if_known(row['completion_tokens'] for row in rows),
        service_cost_usd=total_if_known(row['service_cost_usd'] for row in rows),
    )
    return result


def evaluate_case(case, config, retriever, by_id, model, api_key, retrieval_only, *, top_k=3, max_searches=4):
    strategy, budget, guidance = config
    question = case['question']
    filters = case.get('filter')
    gold = case.get('gold', [])
    row = {'query_id': case['id'], 'question': question, 'filter': filters,
           'answerable': bool(gold), 'strategy': strategy, 'events': [], 'status': 'retrieved'}
    stage = 'ranking'
    controller = None
    agent_started = None
    try:
        if gold:
            started = perf_counter()
            hits = retriever.search(question, filters=filters, top_k=top_k)[:3]
            row['retrieval_ms'] = (perf_counter() - started) * 1000
            row.update(original_top3=hits, hit1=any(hit(chunk, gold) for chunk in hits[:1]),
                       hit3=any(hit(chunk, gold) for chunk in hits))
            if retrieval_only:
                context, ids = pack_context(hits, budget)
                row.update(context=context, context_ids=ids, packed_hit=any(hit(by_id[i], gold) for i in ids))
        if not retrieval_only:
            stage = 'agent'
            agent_started = perf_counter()
            controller = ChatController(model, api_key, provider='gemini', search_guidance=guidance)
            row.update(run_agent(question, controller, retriever, filters=filters,
                                 max_searches=max_searches, top_k=top_k, budget=budget, events=row['events']))
            row['context_hit'] = any(hit(by_id[i], gold) for i in row['context_ids'])
    except Exception as error:
        message = str(error)
        for secret in (api_key, os.environ.get('DATABASE_URL')):
            if secret:
                message = message.replace(secret, '[redacted]')
        row.update(status='error', error={'stage': stage, 'type': type(error).__name__, 'message': message})
    if agent_started is not None:
        row['agent_ms'] = (perf_counter() - agent_started) * 1000
    calls = controller.calls if controller else []
    usage = [call.get('usage') or {} for call in calls]
    row.update(
        model_calls=calls, searches=sum(event['event'] == 'search' for event in row['events']),
        terminal_event=row['events'][-1]['event'] if row['events'] else None,
        prompt_tokens=total_if_known(info.get('prompt_tokens') for info in usage),
        completion_tokens=total_if_known(info.get('completion_tokens') for info in usage),
        service_cost_usd=0 if retrieval_only else total_if_known(info.get('cost') for info in usage),
    )
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--day6-root', type=Path, default=DEFAULT_DAY6)
    parser.add_argument('--split', choices=('dev', 'test'), default='dev')
    parser.add_argument('--configs', nargs='+', choices=CONFIGS)
    parser.add_argument('--retrieve-only', action='store_true')
    args = parser.parse_args()
    if args.configs and len(set(args.configs)) != len(args.configs):
        parser.error('Mỗi cấu hình chỉ được chọn một lần')
    configs = {name: CONFIGS[name] for name in (args.configs or CONFIGS)}
    parameters = {'top_k': 3, 'candidate_k': 20, 'rrf_k': 60, 'max_searches': 4}
    corpus_bytes = CORPUS.read_bytes()
    corpus_hash = sha256(corpus_bytes).hexdigest()
    api_key = os.environ.get('GEMINI_API_KEY')
    model = os.environ.get('GEMINI_MODEL') or 'gemini-3.8-flash'
    frozen = None
    if args.split == 'test':
        if args.configs or args.retrieve_only:
            parser.error('Test phải chạy cả hai agent theo cấu hình đã chốt')
        selection_bytes = CORPUS.with_name('selected_config.json').read_bytes()
        frozen = json.loads(selection_bytes)
        if frozen['selection_split'] != 'dev' or frozen['provider'] != 'gemini' or frozen['corpus_sha256'] != corpus_hash:
            parser.error('Cấu hình đã chốt không khớp với runner hoặc corpus')
        configs = {c['name']: (c['strategy'], c['context_budget_chars'], c['search_guidance'])
                   for c in (frozen['baseline'], frozen['selected'])}
        if len(configs) != 2:
            parser.error('Cần hai cấu hình test riêng')
        model = frozen['model']
        parameters = frozen['parameters']
    if not args.retrieve_only and not api_key:
        parser.error('Cần đặt GEMINI_API_KEY trong Terminal')
    needs_dense = any(config[0] != 'tfidf' for config in configs.values())
    database_url = os.environ.get('DATABASE_URL')
    if needs_dense and not database_url:
        parser.error('Cần đặt DATABASE_URL cho pgvector Day 6')
    chunks = json.loads(corpus_bytes)
    positive = [q for q in json.loads(CORPUS.with_name('questions.json').read_text(encoding='utf-8'))
                if q['split'] == args.split]
    validate(chunks, positive)
    negative = [q for q in json.loads(CORPUS.with_name('abstention_cases.json').read_text(encoding='utf-8'))
                if q['split'] == args.split]
    expected = 15 if args.split == 'dev' else 5
    if len(positive) != expected or len(negative) != 2 or len({q['id'] for q in positive + negative}) != expected + 2:
        parser.error(f'Tập {args.split} cần {expected} câu có đáp án và 2 câu thiếu bằng chứng, ID riêng')
    cases = positive if args.retrieve_only else positive + negative
    by_id = {chunk['id']: chunk for chunk in chunks}
    started = perf_counter()
    dense = Day6Dense(args.day6_root.resolve(), database_url, chunks) if needs_dense else None
    if frozen and (dense is None or dense.config != frozen['embedding']):
        parser.error('Embedding hiện tại khác cấu hình test đã chốt')
    args.output.mkdir(parents=True, exist_ok=False)
    retrievers = {s: Retrieval(chunks, s, dense=dense, candidate_k=parameters['candidate_k'],
                              rrf_k=parameters['rrf_k']) for s in dict.fromkeys(c[0] for c in configs.values())}
    summary = {
        'split': args.split, 'retrieve_only': args.retrieve_only, 'model': None if args.retrieve_only else model,
        'corpus_sha256': corpus_hash, 'chunk_count': len(chunks),
        f'{args.split}_cases_sha256': sha256(json.dumps(cases, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
        'embedding': dense.config if dense else None, 'setup_ms': (perf_counter() - started) * 1000,
        **parameters, 'configs': {},
    }
    if frozen:
        summary['selected_config_sha256'] = sha256(selection_bytes).hexdigest()
    for name, config in configs.items():
        strategy, budget, guidance = config
        rows = []
        with (args.output / f'{name}.jsonl').open('x', encoding='utf-8') as output:
            for case in cases:
                row = evaluate_case(case, config, retrievers[strategy], by_id, model, api_key, args.retrieve_only,
                                    top_k=parameters['top_k'], max_searches=parameters['max_searches'])
                rows.append(row)
                output.write(json.dumps(row, ensure_ascii=False) + '\n')
                output.flush()
                print(f"{name} {case['id']}: {row['status']}", flush=True)
        summary['configs'][name] = {
            'strategy': strategy, 'context_budget_chars': budget, 'search_guidance': guidance,
            **summarize(rows, retrieval_only=args.retrieve_only),
        }
        write_json(args.output / 'summary.json', summary)
    print(args.output / 'summary.json')
    return int(any(config['errors'] for config in summary['configs'].values()))


if __name__ == '__main__':
    raise SystemExit(main())

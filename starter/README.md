# Starter Day 7

| File | Công dụng |
|---|---|
| `agentic.py` | Khung agent ví dụ với số lượt search, top-k và context budget có thể cấu hình |
| `baseline.py` | TF-IDF lexical baseline, chạy offline |
| `convert_day6.py` | Chuyển một số trường JSON từ Day 6 |
| `agent_metrics.py` | Tổng hợp nhãn đánh giá do bạn tự chấm |

Starter **chưa phải solution hoàn chỉnh**. Bạn phải nối model và vector store thật, triển khai ít nhất 3 phương pháp retrieval do bạn chọn, gồm dense trên vector store Day 6. Mock chỉ dùng để test code.

## 1. Kết nối agent

Trong `agentic.py`, hiện thực:

- `Controller.decide`: gọi model thật và trả `{action: "search", query: "..."}` hoặc `{action: "answer", answer: "... [chunk-id]", citations: ["chunk-id"]}`.
- `Retriever.search`: tạo query embedding tương thích Day 6, truy vấn vector store thật và trả chunk theo [định dạng dữ liệu](../data/README.md).

Tự viết chương trình nối hai phần với `run_agent`, hoặc thay thế bằng kiến trúc nhiều tool. Tham số `max_searches`, `top_k` và `budget` chỉ là mặc định của ví dụ, không phải giới hạn của đề. Xem `tests/test_agentic.py` để hiểu cách gọi; kết nối trong test là mock. Khung code kiểm tra citation ID có trong context, nhưng bạn phải tự đọc xem nguồn có hỗ trợ câu trả lời. Báo lỗi kết nối, không thay bằng kết quả giả.

## 2. Chạy TF-IDF baseline

Chạy từ thư mục gốc với Python 3.11 trở lên:

```bash
python3 -m unittest discover -s tests -v
python3 starter/baseline.py --chunks data/example_chunks.json --questions data/example_questions.json --split dev --output starter/results/example-dev
```

Kết quả có `summary.json` và `traces.json`. Dữ liệu mẫu chỉ có một câu, không đủ để nộp bài. TF-IDF là lexical retrieval, không dùng filter và không thay dense retrieval.

## 3. Dùng dữ liệu Day 6

Xuất chunk và câu hỏi thành hai JSON array. Starter Day 6 không quy định tên bảng hay cách xuất; bạn cần tự thực hiện. Nếu chunk có `chunk_id`, `document_id`, `source`, `page`, `text`, `metadata` và câu hỏi có `gold_source_id`, `gold_page`, `evidence_quote`, chạy:

```bash
python3 starter/convert_day6.py --chunks <day6_chunks.json> --questions <day6_questions.json> --output starter/data/converted
python3 starter/baseline.py --chunks starter/data/converted/chunks.json --questions starter/data/converted/questions.json --split dev --output starter/results/dev-tfidf
```

Thay phần trong `< >` bằng đường dẫn thật. Script chỉ đổi tên trường, không tự truy cập database hay đoán evidence. Nếu cấu trúc khác, tự viết adapter. Đối chiếu lại nguồn, trang và evidence.

`--split dev` chỉ chấm dev. Sau khi chốt cấu hình, dùng `--split test` và chọn thư mục kết quả khác. Nếu test Day 6 từng dùng để chỉnh hệ thống, tạo test mới theo [GUIDE.md](../GUIDE.md). Baseline mẫu dùng evidence nằm trong một chunk và context từ top-3; cần mở rộng hoặc tự đánh giá nếu dùng multi-hop, context từ nhiều lượt hay schema khác. Khớp nguyên văn bằng code không thay thế đánh giá thủ công.

## 4. Tổng hợp đánh giá agent

Sau khi chạy agent thật và tự chấm, chuẩn bị ba JSON array:

- `cases.json`: mỗi câu có `id`, `split`, `answerable` (`true` nếu có đủ evidence).
- `traces.json`: mỗi kết quả có `query_id`, `status` (`answered`, `abstain`, `error`), `events`, `citations`. Thêm `query_id` vào kết quả `run_agent`; lỗi kết nối ghi riêng với `status: "error"`. Script đếm tool use qua event `search`: nếu dùng nhiều tool, chuẩn hóa mỗi lượt retrieval về event này và ghi tên tool trong trường khác, hoặc tự viết metric tương đương.
- `reviews.json`: mỗi nhãn có `query_id`, `citation_support` là danh sách đúng/sai ứng với từng citation. Câu có đáp án cần `answer_grade` 0–2 theo [BENCHMARK.md](../BENCHMARK.md); nếu bị từ chối, chấm 0. Câu thiếu evidence cần `abstention_correct` (`true`/`false`) do người chấm xác nhận. Lần chạy lỗi không cần nhãn.

```bash
python3 starter/agent_metrics.py --cases <cases.json> --traces <traces.json> --reviews <reviews.json> --split test --output starter/results/agent-test/summary.json
```

Thay đường dẫn trong `< >`. Script tổng hợp nhãn bạn đã chấm, không tự đánh giá nội dung. Mẫu số bằng 0 nghĩa là không áp dụng. Lỗi kết nối được báo riêng, không tính vào chất lượng; giữ trace và nhãn để đối chiếu.

## Lưu ý

TF-IDF dùng cách tách từ đơn giản. `baseline.py` dùng mặc định context budget 800 ký tự, gồm cả nguồn; chunk không vừa bị bỏ. Bạn có thể chọn cách khác. File kết quả cùng tên sẽ bị ghi đè. `starter/data/` và `starter/results/` không được Git theo dõi mặc định; nếu được phép chia sẻ, dùng `git add -f <đường-dẫn>`, hoặc ghi cách tái tạo. Không nộp dữ liệu mật và secret.

Khung agent ưu tiên giữ chunk từ lần search trước. Khi chunk đầu chiếm gần hết budget, lần search sau có thể không thêm được evidence; hãy kiểm tra trace và thử cách chọn context phù hợp trên dev. Citation ID hợp lệ hoặc verifier trả “đúng” không đảm bảo câu trả lời được hỗ trợ; cần chấm thủ công.

## 5. Chạy retrieval và agent Truyện Kiều

Từ thư mục gốc Day 7, dùng Python 3.12 của Day 6 cho dense và hybrid. PostgreSQL phải có snapshot C đã nạp ở bước 1. Nếu hai repo nằm ở vị trí khác, truyền `--day6-root`.

```bash
day6=../K5-L3B-DAY06-NguyenMinhQuan-2A202603794-DataIngestion
export DATABASE_URL=postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab
question='Người con trai trong gia đình viên ngoại họ Vương tên là gì?'
for strategy in tfidf dense hybrid; do
  "$day6/starter/.venv/bin/python" starter/run_truyen_kieu.py \
    --retrieve-only --strategy "$strategy" --query-id q01 --question "$question" \
    --output "starter/results/step3/${strategy}.json"
done
```

Ba chế độ dùng corpus Day 7. Dense kiểm tra chữ ký embedding và snapshot C trước khi truy vấn. Hybrid lấy tối đa 20 ứng viên từ mỗi phương pháp, cộng `1 / (60 + rank)` cho mỗi lần xuất hiện và trả 3 kết quả theo mặc định. Trace giữ hạng và điểm nguồn của từng kết quả hybrid. Dùng `--verse-range START END` cho câu có bộ lọc. TF-IDF trong lệnh này áp dụng cùng bộ lọc như dense, còn lệnh `baseline.py` ở trên giữ hành vi baseline gốc.

Để chạy agent, đặt `OPENROUTER_API_KEY` trong phiên Terminal và chọn một `OPENROUTER_MODEL` hỗ trợ function calling. Mỗi lượt tìm có thể gửi câu hỏi và context chứa trích đoạn sang OpenRouter. Trace lưu model, query, kết quả, context cuối, ID trích dẫn, thời gian và usage khi API trả về. Chi phí thiếu trong usage được ghi `null`.

```bash
# Terminal mặc định của macOS dùng zsh. Nhập key khi có lời nhắc.
read -rs 'OPENROUTER_API_KEY?OpenRouter API key: '
echo
export OPENROUTER_API_KEY
export OPENROUTER_MODEL='openai/gpt-4.1-mini'
"$day6/starter/.venv/bin/python" starter/run_truyen_kieu.py \
  --strategy hybrid --query-id q01 --question "$question" \
  --output starter/results/step3/agent-q01.json

"$day6/starter/.venv/bin/python" starter/run_truyen_kieu.py \
  --strategy hybrid --query-id d17 --question 'Ai là người thiết kế và xây lầu Ngưng Bích trong Truyện Kiều?' \
  --output starter/results/step3/agent-d17.json
```

Lần chạy đầu cần đối chiếu `q01` với câu thơ về Vương Quan ở trang 2 và kiểm tra `d17` có tìm rồi từ chối hay không. Với lỗi cấu hình, kết nối hoặc phản hồi model, lệnh ghi trace trạng thái `error` rồi trả mã thoát khác 0. Chọn cấu hình trên dev trước khi chạy test. [Tài liệu gọi tool của OpenRouter](https://openrouter.ai/blog/tutorials/tool-calling/) · [Model ví dụ](https://openrouter.ai/openai/gpt-4.1-mini)

### Dùng khóa Google AI Studio

Trong cùng phiên Terminal đã đặt `day6` và `DATABASE_URL` ở trên, nhập khóa từ [Google AI Studio](https://aistudio.google.com/apikey) và chọn `--provider gemini`. Mặc định dùng `gemini-3.8-flash`. Đặt `GEMINI_MODEL` nếu muốn chọn model khác hỗ trợ gọi tool. Trace lưu usage do Google trả về. Chi phí là `null` nếu phản hồi thiếu số tiền. [Tài liệu Gemini API](https://ai.google.dev/gemini-api/docs/openai)

```zsh
read -rs 'GEMINI_API_KEY?Gemini API key: '
echo
export GEMINI_API_KEY
"$day6/starter/.venv/bin/python" starter/run_truyen_kieu.py \
  --provider gemini --strategy hybrid --query-id q01 --question "$question" \
  --output starter/results/step3/gemini-q01.json
```

Nếu cả hai API báo lỗi TLS trên macOS với Python 3.12 từ python.org, chạy
`"/Applications/Python 3.12/Install Certificates.command"` trong Terminal.
Kiểm tra bằng Python của Day 6:
`"$day6/starter/.venv/bin/python" -c 'import ssl; print(ssl.get_default_verify_paths().cafile)'`.
Sau khi cài thành công, lệnh in đường dẫn tệp CA. Chạy lại truy vấn trong phiên
Terminal đã đặt API key. [Tài liệu cài đặt Python trên macOS](https://docs.python.org/3/using/mac.html)

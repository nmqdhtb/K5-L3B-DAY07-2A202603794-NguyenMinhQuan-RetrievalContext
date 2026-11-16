# Thực nghiệm dev Truyện Kiều

Chạy ba phương pháp trên cùng 379 chunk và cùng bộ lọc của 17 câu dev. Đo ranking trên câu hỏi nguyên văn cho 15 câu có đáp án. Đo context cuối qua agent chạy thật, với Gemini và tối đa bốn lượt truy xuất. Dùng hai câu thiếu bằng chứng để kiểm tra hành vi từ chối.

| Cấu hình | Truy xuất | Context | Thay đổi cần kiểm tra |
|---|---|---:|---|
| `tfidf` | TF-IDF | 800 ký tự | Baseline từ khóa |
| `dense` | pgvector C | 800 ký tự | Tìm theo nghĩa |
| `hybrid` | RRF | 800 ký tự | Kết hợp hai bảng hạng |
| `hybrid_budget` | RRF | 1.600 ký tự | Giữ thêm chunk trong context |
| `hybrid_stop` | RRF | 800 ký tự | Chỉ tìm lại khi có manh mối cụ thể |

Mỗi lượt lấy tối đa 3 chunk. RRF dùng tối đa 20 ứng viên từ mỗi retriever và hằng số 60. Hai biến thể thay đổi từng yếu tố so với `hybrid`.

## Quan sát trước khi chạy đủ

- Trên 15 câu có đáp án, TF-IDF đạt Hit@1 và Evidence Hit@3 đều 10/15 với bộ lọc của từng câu. `q03` (nghề của Đạm Tiên) yêu cầu câu thơ ở trang 4. TF-IDF trả trang 170, 74, 168. Kiểm tra xem tín hiệu ngữ nghĩa trong Hybrid có đưa trang 4 vào top-3 hay không.
- `d17` hỏi ai xây lầu Ngưng Bích. Trace Hybrid tìm thấy trang 60 ngay lượt đầu nhưng context 781 ký tự đã chứa chunk ở trang 72 và 97. Đóng gói lại cùng kết quả với ngân sách 1.600 ký tự đưa trang 60 vào context 1.348 ký tự. Đoạn này nói về lầu nhưng vẫn thiếu chi tiết người xây. Khi chạy thật, so sánh token, độ trễ và Context Evidence Rate trên các câu có đáp án.
- Cũng ở `d17`, Gemini tiếp tục tìm biến thể của tên lầu và chạm trần 4 lượt. Prompt dừng hướng đến ít lượt tìm lặp hơn, ưu tiên `model_abstained` khi thiếu bằng chứng. Kiểm tra lượt tìm, nguyên nhân dừng, và tỷ lệ từ chối nhầm trên câu có đáp án.

## Chạy trên Terminal macOS

Tại thư mục gốc Day 7, dùng phiên Terminal đã chạy thành công Gemini ở bước 3:

```zsh
day6=../K5-L3B-DAY06-NguyenMinhQuan-2A202603794-DataIngestion
export DATABASE_URL=postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab
export GEMINI_MODEL=gemini-3.8-flash
"$day6/starter/.venv/bin/python" starter/benchmark_dev.py \
  --output "starter/results/step4/dev-$(date +%Y%m%d-%H%M%S)"
```

Nếu mở Terminal mới, nhập `GEMINI_API_KEY` theo [hướng dẫn bước 3](../starter/README.md#dùng-khóa-google-ai-studio). Lệnh chạy tuần tự 17 câu cho mỗi cấu hình và lưu một dòng trace ngay sau mỗi câu. `summary.json` cập nhật sau mỗi cấu hình. Có thể chạy nhóm nhỏ bằng `--configs tfidf dense hybrid` hoặc `--configs hybrid_budget hybrid_stop`, dùng thư mục output mới. Lỗi được ghi riêng. Mẫu số metric chỉ tính lượt đo thành công, nên cần đối chiếu với 15 câu có đáp án và 17 ca tổng cộng trước khi so sánh.

Trace giữ số token và chi phí khi API trả về. Với Gemini, phản hồi có thể chỉ báo token nên chi phí lưu là `null`. Khi tổng hợp, đối chiếu mức sử dụng và hóa đơn của tài khoản Google AI Studio nếu có.

## Chốt trước khi chạy test

Đọc trace và chấm hai lỗi dev từ lượt chạy đủ. Loại cấu hình nếu còn lỗi hệ thống chưa xử lý hoặc nếu số từ chối nhầm tăng so với baseline. Trong các cấu hình còn lại, ưu tiên Context Evidence Rate, sau đó số câu thiếu bằng chứng được tìm rồi từ chối, rồi Evidence Hit@3 và độ trễ agent thấp hơn. Ghi cấu hình chọn, model, prompt, ngân sách, thông số truy xuất, lý do và giới hạn vào báo cáo trước khi dùng test.

## Chạy test với cấu hình đã chốt

Từ thư mục gốc Day 7, trong Terminal đã đặt `GEMINI_API_KEY` và đang chạy pgvector:

```zsh
day6=../K5-L3B-DAY06-NguyenMinhQuan-2A202603794-DataIngestion
export DATABASE_URL=postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab
"$day6/starter/.venv/bin/python" starter/benchmark_dev.py --split test \
  --output "starter/results/step5/test-$(date +%Y%m%d-%H%M%S)"
```

Runner đọc [cấu hình đã chốt](../data/truyen-kieu/selected_config.json), xác minh corpus và chữ ký embedding rồi chạy TF-IDF 800 và Hybrid RRF 1.600 trên đúng 7 câu test. Thư mục kết quả có hai tệp trace `tfidf.jsonl`, `hybrid_budget.jsonl` và `summary.json` ghi hash cấu hình.

Sau khi chạy, đối chiếu đủ 7 trace mỗi cấu hình. Đọc context cuối và chấm 0–2 theo [rubric](../BENCHMARK.md) trên 5 câu có đáp án, đồng thời kiểm tra cả 2 ca thiếu bằng chứng. Chấm câu trả lời 0–2 và từng trích dẫn dựa trên đoạn thực sự gửi model. Ghi nguyên nhân dừng, lỗi hệ thống nếu có, số token và thời gian. Số liệu retrieval và trạng thái trong summary được tính tự động. Điểm nội dung và độ hợp lệ của trích dẫn cần đọc trace để chấm.

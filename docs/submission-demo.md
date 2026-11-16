# Tái lập và trình bày bài nộp Day 7

## Tái lập

1. Đặt repo Day 6 cạnh repo Day 7 hoặc chỉ định đường dẫn bằng `--day6-root`. Dùng Python 3.12 trong môi trường ảo của Day 6. Khởi động Docker Compose, chuẩn bị model embedding và nạp snapshot C theo README Day 6. [Repo Day 6](https://github.com/nmqdhtb/K5-L3B-DAY06-NguyenMinhQuan-2A202603794-DataIngestion)
2. Ở thư mục gốc Day 7, chạy `python3 -m unittest discover -s tests -v`. Kiểm tra kết nối pgvector với câu `q01` theo hướng dẫn dữ liệu. [Hướng dẫn kết nối](../data/README.md#kiểm-tra-dense-retrieval) · [Trace kiểm tra pgvector](../starter/results/day6-dense-smoke.json)
3. Đặt `GEMINI_API_KEY` trong Terminal và chạy benchmark theo hướng dẫn. Khi chạy test, runner dùng cấu hình đã chốt trên dev và đối chiếu hash corpus cùng chữ ký embedding. [Lệnh chạy dev và test](dev-benchmark.md)

## Ba ca trình bày từ test

| Ca | Mở gì trong trace | Kết quả và diễn giải |
|---|---|---|
| `t04` — trả lời có nguồn | Lượt tìm đầu, context cuối và citation của Hybrid. Đối chiếu top-3 và context cuối của TF-IDF. | Hai phương pháp đều xếp trang 153 thứ hai ở lượt truy vấn gốc. Hybrid giữ đoạn này trong context và trả lời **sông Tiền Đường** kèm nguồn hợp lệ. TF-IDF bỏ đoạn này khỏi context và từ chối. |
| `t06` — thiếu bằng chứng | Bốn lượt tìm và sự kiện `search_limit` của Hybrid. | Câu hỏi yêu cầu ngày, tháng và năm sinh Từ Hải. Agent trả lời **không đủ bằng chứng để trả lời** sau khi chạm giới hạn. Bộ câu hỏi ghi những trang và từ khóa đã đối chiếu trong corpus. |
| `t03` — lỗi truy xuất | Bộ lọc dòng thơ 2.001–3.254, top-3 truy vấn gốc và context cuối của Hybrid. | Top-3 là trang 188, 189 và 165, thiếu trang 118 chứa biển **Chiêu ẩn am**. Đoạn nói về một am ở trang 188 thuộc cảnh khác. Agent từ chối sau bốn lượt. |

[Trace Hybrid](../starter/results/step5/test-20261116-123311/hybrid_budget.jsonl) · [Trace TF-IDF](../starter/results/step5/test-20261116-123311/tfidf.jsonl) · [Đáp án và bằng chứng](../data/truyen-kieu/questions.json) · [Ca thiếu bằng chứng](../data/truyen-kieu/abstention_cases.json)

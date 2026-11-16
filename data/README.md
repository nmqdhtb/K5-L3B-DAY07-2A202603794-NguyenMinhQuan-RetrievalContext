# Định dạng dữ liệu

Các file `example_*.json` chỉ minh họa định dạng, không đủ để nộp bài. Dữ liệu thật là JSON array UTF-8; nếu dùng định dạng khác, ghi cách chuyển trong README.

- **Chunk:** `id`, `text`, `source_id`, `source`, `page`, `metadata`. ID phải duy nhất; giữ phiên bản hoặc ngày nếu có.
- **Câu có đáp án:** `id`, `split` (`dev` hoặc `test`), `question`, `expected_answer`, `gold`: danh sách `{source_id, page, evidence}`. Với schema mẫu, mỗi evidence phải nằm trọn trong một chunk đúng nguồn và trang; các phần tử `gold` là evidence thay thế. Với câu multi-hop cần nhiều đoạn, bạn có thể mở rộng schema, ghi rõ nhóm evidence bắt buộc và cách chấm. Có thể thêm `filter` do người dùng cung cấp trước.
- **Câu thiếu evidence:** `id`, `split`, `question`, `answerable: false`, `expected_behavior: "search_and_abstain"`, `absence_reason`. Xem `agent_cases_example.json`.

Không đưa `gold` hoặc nhãn đáp án vào model và retrieval tool. Ghi nguồn dữ liệu và quyền sử dụng. Cách chuyển một số định dạng Day 6: [starter/README.md](../starter/README.md).

## Corpus Truyện Kiều

[chunks.json](truyen-kieu/chunks.json) chứa 379 chunk trên 189 trang nội dung. Day 6 dùng cùng chunk và embedding cho B và C. Corpus này giữ nguyên ID, nguồn, trang, văn bản và metadata của Day 6. Nguồn là bản PDF *Truyện Kiều (trọn bộ)* của Nguyễn Du ghi trong `data/manifest.json` của Day 6. Manifest ghi nhận học viên đã xác nhận quyền chia sẻ bản PDF.

Từ thư mục gốc Day 7, tái tạo bản xuất khi hai repo nằm cạnh nhau:

```bash
day6=../K5-L3B-DAY06-NguyenMinhQuan-2A202603794-DataIngestion
python3 starter/convert_day6.py \
  --chunks "$day6/starter/results/chunking/chunks_B.jsonl" \
  --output data/truyen-kieu
```

SHA-256 đầu vào là `8d2d23c8adba2aba92af2c7e38e3b468e84f2c9fad09d9b6cf264accfcc4ddf3`, trùng với bản Day 6 đã chốt.

### Benchmark Day 7

| Tập | Có đáp án | Thiếu bằng chứng | Tổng |
|---|---:|---:|---:|
| Dev | 15 | 2 | 17 |
| Test | 5 | 2 | 7 |

- [questions.json](truyen-kieu/questions.json) chứa các câu có đáp án, dùng trực tiếp với `starter/baseline.py` và `--split dev` khi thử cấu hình. Mỗi đoạn trích chuẩn nằm trọn trong một chunk đúng nguồn và trang PDF. Khi chấm agent, các câu trong file này có `answerable: true`.
- [abstention_cases.json](truyen-kieu/abstention_cases.json) chứa 4 câu thiếu bằng chứng. Mỗi câu ghi từ khóa tra trên cả corpus và các trang liên quan đã đối chiếu. Dùng các câu này khi đánh giá hành vi từ chối.
- Dev lấy `q01`–`q15` từ `benchmark/questions.json` của Day 6. `q09` thu hẹp về núi xa và trăng gần vì đoạn trích cũ nằm ở hai chunk. `q10` giữ đáp án và rút đoạn trích còn phần đủ để chứng minh trong một chunk. Các bộ lọc theo phạm vi câu thơ đến từ câu hỏi. Metadata Day 6 dùng khoảng câu thơ của trang, nên bộ lọc kiểm tra sự giao nhau của khoảng trang chứa chunk với phạm vi được hỏi.
- Cả 7 câu test được soạn mới cho Day 7. Chỉ dùng test để đo kết quả sau khi chốt cấu hình trên dev. Đầu vào của agent và công cụ tìm kiếm chỉ gồm câu hỏi và bộ lọc nếu có. Đáp án chuẩn, evidence và nhãn được đọc ở bước chấm.

### Kiểm tra dense retrieval

Lượt truy vấn pgvector trực tiếp ngày 16/11/2026 dùng cấu hình C cho câu `q01` “Người con trai trong gia đình viên ngoại họ Vương tên là gì?”. Trace chạy trên máy học viên nằm tại `starter/results/day6-dense-smoke.json`. Chunk `c0088eb0bf44d62bef7b394cbca8ba590eeb7db181bd1b3c6538d3bf60bbdef2` đứng đầu với điểm cosine 0,592797 và có câu “14. Vương Quan là chữ, nối dòng nho gia.” ở trang PDF 2. Cả ba kết quả khớp corpus đã xuất về ID, nguồn, trang, nội dung và metadata. Điểm cosine của mỗi kết quả bằng 1 trừ khoảng cách cosine.

Khi Docker Desktop đã chạy và Day 6 có môi trường Python cùng bộ nhớ đệm model theo `starter/README.md` của Day 6, chạy từ thư mục gốc Day 7:

```bash
docker compose -p day6_student_starter -f "$day6/starter/docker-compose.yml" up -d --wait
mkdir -p starter/results
DATABASE_URL=postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab \
  "$day6/starter/.venv/bin/python" "$day6/starter/scripts/search_vectors.py" \
  --strategy C --question "Người con trai trong gia đình viên ngoại họ Vương tên là gì?" \
  > starter/results/day6-dense-smoke.json
```

Nếu chưa có môi trường Python hoặc model, làm theo mục cài đặt và chuẩn bị model trong README của Day 6. Nếu truy vấn trả về danh sách rỗng, chạy `ingest_vectors.py` theo hướng dẫn Day 6 để khôi phục dữ liệu.

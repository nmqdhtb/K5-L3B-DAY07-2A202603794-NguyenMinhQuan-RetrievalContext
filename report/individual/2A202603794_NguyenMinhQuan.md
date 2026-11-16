# Báo cáo Day 7 — Nguyễn Minh Quân (2A202603794)

## Dữ liệu và benchmark

- **Nguồn, quyền sử dụng, số trang và số chunk.** Corpus gồm 379 chunk từ 189 trang PDF *Truyện Kiều (trọn bộ)* của Nguyễn Du, kế thừa từ Day 6. Manifest Day 6 ghi nhận học viên xác nhận quyền chia sẻ bản PDF. [Nguồn và schema](../../data/README.md)
- **Vector store, embedding model, phiên bản và số chiều.** PostgreSQL/pgvector dùng snapshot C và tìm theo cosine. Model embedding là `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`, 384 chiều. [Cấu hình đã chốt](../../data/truyen-kieu/selected_config.json)
- **Agent model, cách chạy và phân chia dev/test.** Agent dùng Gemini 3.8 Flash (`gemini-3.8-flash`). Dev gồm 17 câu (15 có đáp án, 2 thiếu bằng chứng). Test gồm 7 câu (5 có đáp án, 2 thiếu bằng chứng). Dùng dev để chốt cấu hình trước khi đánh giá test. [Lệnh chạy](../../docs/dev-benchmark.md) · [Câu có đáp án](../../data/truyen-kieu/questions.json) · [Câu thiếu bằng chứng](../../data/truyen-kieu/abstention_cases.json)
- **Cách xác định câu có hoặc thiếu bằng chứng và tiêu chí chấm.** Câu có đáp án đi kèm trích đoạn chuẩn, nguồn và số trang. Câu thiếu bằng chứng ghi các từ khóa và trang đã đối chiếu trong corpus. Hit@1 và Evidence Hit@3 kiểm tra trích đoạn chuẩn nằm trọn trong chunk đúng nguồn và trang ở top 1 hoặc top 3 của truy vấn gốc. Context Evidence Rate kiểm tra bằng chứng đó trong context cuối. Context và câu trả lời được chấm 0–2 trên các ca có đáp án. Trích dẫn hợp lệ khi chunk được dùng có trong context và hỗ trợ nội dung trả lời. [Tiêu chí benchmark](../../BENCHMARK.md)

## Retrieval và thử nghiệm

Mỗi cấu hình dùng top-3 cho mỗi lượt và cùng bộ lọc dòng thơ nếu câu hỏi có chỉ định phạm vi. Hybrid RRF gộp tối đa 20 ứng viên từ mỗi nhánh TF-IDF và dense với hằng số 60. Thời gian trong bảng là trung vị truy xuất và trung vị agent. Cả 85 trace dev và 14 trace test đều hoàn tất, không có lỗi hệ thống. API ghi số token. Chi phí thực tế chưa được xác nhận.

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
| Baseline | TF-IDF, 800 ký tự | Xếp hạng theo từ khóa | dev | 10/15 (66,7%) | 10/15 (66,7%) | 10/15 (66,7%) | 4,8 ms / 10,20 giây |
| Phương pháp 2 | Dense pgvector, 800 ký tự | Tìm theo nghĩa bằng embedding | dev | 4/15 (26,7%) | 7/15 (46,7%) | 4/15 (26,7%) | 99,8 ms / 13,32 giây |
| Phương pháp 3 | Hybrid RRF, 800 ký tự | Gộp hai bảng xếp hạng | dev | 9/15 (60,0%) | 12/15 (80,0%) | 9/15 (60,0%) | 64,5 ms / 10,53 giây |
| Cải thiện 1 | Hybrid RRF, 1.600 ký tự | Giữ thêm chunk có bằng chứng trong context | dev | 9/15 (60,0%) | 12/15 (80,0%) | 12/15 (80,0%) | 63,8 ms / 6,95 giây |
| Cải thiện 2 | Hybrid RRF, 800 ký tự | Hướng dẫn chỉ tìm lại khi có manh mối cụ thể | dev | 9/15 (60,0%) | 12/15 (80,0%) | 9/15 (60,0%) | 95,9 ms / 8,63 giây |
| Cấu hình đã chọn | Hybrid RRF, 1.600 ký tự | Dùng cấu hình đã chốt trên dev | test | 1/5 (20%) | 2/5 (40%) | 2/5 (40%) | 84,0 ms / 12,39 giây |
| Baseline | TF-IDF, 800 ký tự | Đối chứng trên cùng tập test | test | 0/5 (0%) | 1/5 (20%) | 0/5 (0%) | 6,9 ms / 11,94 giây |

### Phân tích lỗi dev và chọn cấu hình

| Ca | Quan sát và nhãn |
|---|---|
| `q02` | Hybrid 800 xếp trang 3 thứ hai nhưng context cuối chỉ có trang 12. Agent hết lượt và từ chối nhầm. Context **0/2**, câu trả lời **0/2**. Với 1.600 ký tự, Gemini trả lời đúng tháng ba, lễ tảo mộ và hội đạp Thanh trong một lượt. Chunk trang 3 hỗ trợ đầy đủ cả ba chi tiết. Context **2/2**, câu trả lời **2/2**. |
| `q03` | Hybrid trả top-3 ở trang 74, 170 và 133, thiếu đoạn trang 4 nói Đạm Tiên là ca nhi. Tăng ngân sách vẫn không đưa bằng chứng chuẩn vào context cuối. Cả hai cấu hình từ chối nhầm. Context **0/2**, câu trả lời **0/2**. Đây là lỗi truy xuất còn tồn tại. |
| `d17` | Hybrid 1.600 giữ được đoạn trang 60 nói về lầu Ngưng Bích, nhưng đoạn này thiếu thông tin người xây. Prompt dừng vẫn chạm trần bốn lượt ở ca này. Tổng số ca chạm trần trên dev cũng giữ nguyên ở 8/17 giữa Hybrid 800 mặc định và biến thể prompt dừng. |

Chốt **Hybrid RRF 1.600 ký tự** vì có Context Evidence Rate cao nhất trên dev. So với Hybrid 800, cấu hình này tăng từ 9/15 lên 12/15. So với baseline TF-IDF, số câu bị từ chối nhầm giảm từ 5/15 xuống 3/15. Cấu hình chốt và baseline được giữ nguyên khi chạy test. [Tổng hợp dev](../../starter/results/step4/dev-20261116-115126/summary.json) · [Cấu hình đã chốt](../../data/truyen-kieu/selected_config.json)

Trên dev, tổng token vào/ra của Hybrid 1.600 là 47.000 / 4.037, so với 40.315 / 3.457 của Hybrid 800 và 35.477 / 3.158 của TF-IDF. [Token theo từng cấu hình](../../starter/results/step4/dev-20261116-115126/summary.json)

## Agent và đánh giá

- **Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi.** Model gọi `search` để gửi query vào retriever, tối đa 4 lượt. Agent gom các chunk qua từng lượt, bỏ trùng theo ID và đưa đoạn vừa ngân sách vào context cuối. Trích dẫn phải trỏ tới chunk trong context. Agent có thể từ chối khi thiếu bằng chứng và dừng tại `search_limit` khi hết lượt. Lỗi API hoặc truy xuất được ghi riêng trong trace. [Mã vòng lặp](../../starter/agentic.py)

| Cấu hình / split | Tool use | Số lượt gọi | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| TF-IDF 800 / test | 7/7 | 7 ca × 4 | 5 / 0 / 0, trung bình 0,00/2 | 0/0 (không áp dụng) | 0/0 (không áp dụng) | 2/2 | 5/5 |
| Hybrid RRF 1.600 / test | 7/7 | 2 ca × 1, 5 ca × 4 | 3 / 0 / 2, trung bình 0,80/2 | 2/2 | 2/2 | 2/2 | 3/5 |

Trên dev, mỗi cấu hình có tool use 17/17 và tìm rồi từ chối đúng 2/2 câu thiếu bằng chứng. Hybrid 1.600 có 11 ca một lượt, một ca hai lượt và năm ca bốn lượt. Trên test, phân bố điểm context 0/1/2 là **5 / 0 / 0** cho TF-IDF và **3 / 0 / 2** cho Hybrid. Cột “Câu có citation” lấy mẫu số từ các ca agent đã trả lời.

### Chấm từng ca test

Điểm trong cột nhãn lần lượt là **context / câu trả lời**, mỗi điểm trên thang 0–2. Các ca thiếu bằng chứng được chấm theo hành vi tìm rồi từ chối.

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| `t01` | Có đáp án | Mỗi cấu hình tìm 4 lượt. | Cả hai cấu hình từ chối. | **TF-IDF** **0/0**. Context lẫn đoạn mười khúc ngâm ở trang 12. Thiếu đoạn bốn câu đề tranh ở trang 23. **Hybrid** **0/0**. Các đoạn về ngâm thơ, quạt và viết kinh không có số câu đề tranh được hỏi. |
| `t02` | Có đáp án | TF-IDF 4 lượt, Hybrid 1 lượt. | TF-IDF từ chối. Hybrid trả lời “thây vô chủ”, dẫn trang 96. | **TF-IDF** **0/0**. Context nói chuyện nhà và việc ép duyên, thiếu cảnh phóng hỏa ở trang 96. **Hybrid** **2/2**. Trả lời “thây vô chủ” lấy bên sông để đánh lạc hướng. Chunk được trích có trong context, đúng trang 96 và hỗ trợ câu trả lời. |
| `t03` | Có đáp án | Mỗi cấu hình tìm 4 lượt. | Cả hai cấu hình từ chối. | **TF-IDF** **0/0**. Context không có tấm biển “Chiêu ẩn am” ở trang 118. **Hybrid** **0/0**. Trang 188 nhắc một am và Giác Duyên nhưng thuộc cảnh khác, không có ba chữ trên tấm biển được hỏi. |
| `t04` | Có đáp án | TF-IDF 4 lượt, Hybrid 1 lượt. | TF-IDF từ chối. Hybrid trả lời “sông Tiền Đường”, dẫn trang 153. | **TF-IDF** **0/0**. Trang 153 đứng thứ hai ở lượt truy vấn gốc nhưng bị loại khỏi context cuối. Hai chunk còn lại nói về đề thơ và bút nghiên. **Hybrid** **2/2**. Trả lời sông Tiền Đường. Chunk được trích có trong context, đúng trang 153 và chứa cả tên sông lẫn chi tiết viết tuyệt bút. |
| `t05` | Có đáp án | Mỗi cấu hình tìm 4 lượt. | Cả hai cấu hình từ chối. | **TF-IDF** **0/0**. Context thiếu đoạn mẹ Kiều nhắc 15 năm lưu lạc ở trang 176. **Hybrid** **0/0**. Context có lời kể ở các cảnh khác nhưng thiếu đoạn đoàn viên và mốc 15 năm. |
| `t06` | Thiếu bằng chứng | Mỗi cấu hình tìm 4 lượt. | Cả hai cấu hình từ chối. | **TF-IDF** **Từ chối đúng** sau 4 lượt. Câu trả lời không đưa ra ngày sinh. **Hybrid** **Từ chối đúng** sau 4 lượt. Các mốc thời gian trong context không xác định ngày sinh Từ Hải. |
| `t07` | Thiếu bằng chứng | Mỗi cấu hình tìm 4 lượt. | Cả hai cấu hình từ chối. | **TF-IDF** **Từ chối đúng** sau 4 lượt. Trang 172 chỉ nêu chức danh thổ tù. **Hybrid** **Từ chối đúng** sau 4 lượt. Tên Từ Hải ở trang 170 thuộc nhân vật khác. Trang 172 chỉ nêu chức danh thổ tù. |

- **Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí.** Nhãn nằm trong bảng chấm từng ca. Tổng thời gian agent trên test là 82,04 giây với TF-IDF và 75,43 giây với Hybrid. Số token vào/ra tương ứng là 25.195 / 773 và 29.824 / 1.016. Trace không có số tiền thực tế. [Tổng hợp test](../../starter/results/step5/test-20261116-123311/summary.json) · [Trace TF-IDF](../../starter/results/step5/test-20261116-123311/tfidf.jsonl) · [Trace Hybrid](../../starter/results/step5/test-20261116-123311/hybrid_budget.jsonl) · [Lệnh chạy](../../docs/dev-benchmark.md)
- **Kết quả trước và sau, ví dụ lỗi, đánh đổi và giới hạn.** Hybrid giữ được bằng chứng ở 2/5 ca test và giảm từ chối nhầm từ 5/5 xuống 3/5. Ở `t04`, TF-IDF tìm được trang 153 trong top-3 nhưng bỏ đoạn đó khỏi context cuối. Ngân sách context tăng đi kèm số token vào cao hơn. Context Evidence Rate của Hybrid giảm từ 12/15 trên dev xuống 2/5 trên test. Cả hai ca thiếu bằng chứng đều dừng tại giới hạn tìm kiếm ở mỗi cấu hình.

## Thử thách nâng cao (nếu thực hiện)

Bài nộp thực hiện phần cơ bản của Day 7.

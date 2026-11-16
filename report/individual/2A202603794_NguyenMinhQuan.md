# Báo cáo Day 7 — Nguyễn Minh Quân

## Dữ liệu và benchmark

Corpus gồm 379 chunk từ 189 trang bản PDF *Truyện Kiều (trọn bộ)* của Nguyễn Du, kế thừa từ Day 6. Manifest Day 6 ghi nhận học viên xác nhận quyền chia sẻ bản PDF. Dense dùng snapshot C trên PostgreSQL/pgvector, embedding đa ngôn ngữ MiniLM-L12-v2, 384 chiều. [Nguồn và schema](../../data/README.md)

Benchmark gồm 17 câu dev (15 có đáp án, 2 thiếu bằng chứng) và 7 câu test (5 có đáp án, 2 thiếu bằng chứng). Một hit yêu cầu đoạn trích chuẩn nằm trọn trong chunk đúng nguồn và trang. Context Evidence Rate kiểm tra chunk đó có trong context cuối. Câu thiếu bằng chứng dùng để đo hành vi tìm rồi từ chối và có ghi cách đối chiếu corpus.

## Kết quả dev

Cả năm cấu hình dùng Gemini 3.8 Flash, tối đa 4 lượt tìm, top-3 mỗi lượt và cùng bộ lọc của từng câu. RRF lấy tối đa 20 ứng viên mỗi nhánh, dùng hằng số 60. Cả 85 ca đều có trace, không có lỗi hệ thống. Thời gian là trung vị trên từng cấu hình.

| Cấu hình | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Từ chối nhầm | Retrieval (ms) | Agent (giây) | Token vào / ra |
|---|---:|---:|---:|---:|---:|---:|---:|
| TF-IDF, 800 ký tự | 10/15 (66,7%) | 10/15 (66,7%) | 10/15 (66,7%) | 5/15 (33,3%) | 4,8 | 10,20 | 35.477 / 3.158 |
| Dense, 800 ký tự | 4/15 (26,7%) | 7/15 (46,7%) | 4/15 (26,7%) | 11/15 (73,3%) | 99,8 | 13,32 | 51.576 / 2.804 |
| Hybrid, 800 ký tự | 9/15 (60,0%) | 12/15 (80,0%) | 9/15 (60,0%) | 6/15 (40,0%) | 64,5 | 10,53 | 40.315 / 3.457 |
| Hybrid, 1.600 ký tự | 9/15 (60,0%) | 12/15 (80,0%) | 12/15 (80,0%) | 3/15 (20,0%) | 63,8 | 6,95 | 47.000 / 4.037 |
| Hybrid, 800 ký tự, prompt dừng | 9/15 (60,0%) | 12/15 (80,0%) | 9/15 (60,0%) | 6/15 (40,0%) | 95,9 | 8,63 | 43.317 / 3.499 |

Mỗi cấu hình có tool use 17/17 và tìm rồi từ chối 2/2 câu thiếu bằng chứng. Với Hybrid 1.600 ký tự, 11 câu có một lượt tìm, một câu có hai lượt và năm câu có bốn lượt. Gemini trả số token nhưng không trả chi phí trong trace. Chi phí thực tế chưa đối chiếu được với hóa đơn.

### Đối chiếu trace

| Ca | Quan sát và nhãn |
|---|---|
| `q02` | Hybrid 800 xếp trang 3 thứ hai nhưng context cuối chỉ có trang 12. Agent hết lượt và từ chối nhầm. Context **0/2**, câu trả lời **0/2**. Với 1.600 ký tự, Gemini trả lời đúng tháng ba, lễ tảo mộ và hội đạp Thanh trong một lượt. Chunk trang 3 hỗ trợ đầy đủ cả ba chi tiết. Context **2/2**, câu trả lời **2/2**. |
| `q03` | Hybrid trả top-3 ở trang 74, 170 và 133, thiếu đoạn trang 4 nói Đạm Tiên là ca nhi. Tăng ngân sách vẫn không đưa bằng chứng chuẩn vào context cuối. Cả hai cấu hình từ chối nhầm. Context **0/2**, câu trả lời **0/2**. Đây là lỗi truy xuất còn tồn tại. |
| `d17` | Hybrid 1.600 giữ được đoạn trang 60 nói về lầu Ngưng Bích, nhưng đoạn này thiếu thông tin người xây. Prompt dừng vẫn chạm trần bốn lượt ở ca này. Tổng số ca chạm trần trên dev cũng giữ nguyên ở 8/17 giữa Hybrid 800 mặc định và biến thể prompt dừng. |

## Cấu hình chốt cho bước test

Chọn **Hybrid RRF với context 1.600 ký tự**. Cấu hình có Context Evidence Rate cao nhất, tăng từ 9/15 lên 12/15 so với Hybrid 800, và giảm từ chối nhầm từ 5/15 xuống 3/15 so với baseline TF-IDF. Chi phí token đầu vào tăng so với cả hai cấu hình đối chiếu. Dùng **TF-IDF 800 ký tự** làm baseline trên cùng test.

Cấu hình, thông số index và hash trace được lưu trong [selected_config.json](../../data/truyen-kieu/selected_config.json). Lượt dev sử dụng `starter/results/step4/dev-20261116-115126/`. [Lệnh tái lập và tiêu chí chọn](../../docs/dev-benchmark.md)

## Kết quả test

Đã đối chiếu đủ 14 trace với đúng 7 câu test và hash cấu hình đã chốt. Cả hai cấu hình dùng Gemini 3.8 Flash. Không có lỗi hệ thống.

| Chỉ số | TF-IDF 800 | Hybrid RRF 1.600 |
|---|---:|---:|
| Hit@1 | 0/5 | 1/5 |
| Evidence Hit@3 | 1/5 | 2/5 |
| Context Evidence Rate | 0/5 | 2/5 |
| Điểm context 0/1/2 | 5 / 0 / 0 | 3 / 0 / 2 |
| Điểm câu trả lời 0/1/2 | 5 / 0 / 0 | 3 / 0 / 2 |
| Trung bình câu trả lời (thang 2) | 0,00 | 0,80 |
| Tool use | 7/7 | 7/7 |
| Tìm rồi từ chối đúng | 2/2 | 2/2 |
| Từ chối nhầm | 5/5 | 3/5 |
| Trích dẫn hợp lệ | 0/0 (không áp dụng) | 2/2 |
| Câu trả lời có citation / câu đã trả lời | 0/0 (không áp dụng) | 2/2 |
| Số lượt tìm theo ca | 7 ca × 4 | 2 ca × 1, 5 ca × 4 |
| Độ trễ truy xuất trung vị | 6,9 ms | 84,0 ms |
| Độ trễ agent trung vị | 11,94 giây | 12,39 giây |
| Tổng thời gian agent | 82,04 giây | 75,43 giây |
| Token vào / ra | 25.195 / 773 | 29.824 / 1.016 |

Chi phí thực tế chưa được xác nhận. API không trả số tiền trong trace.

### Chấm từng ca

Điểm trong bảng lần lượt là **context / câu trả lời**, mỗi điểm trên thang 0–2. Với hai ca thiếu bằng chứng, chấm hành vi tìm rồi từ chối.

| Ca | TF-IDF 800 | Hybrid RRF 1.600 |
|---|---|---|
| `t01` | **0/0**. Context lẫn đoạn mười khúc ngâm ở trang 12. Thiếu đoạn bốn câu đề tranh ở trang 23. | **0/0**. Các đoạn về ngâm thơ, quạt và viết kinh không có số câu đề tranh được hỏi. |
| `t02` | **0/0**. Context nói chuyện nhà và việc ép duyên, thiếu cảnh phóng hỏa ở trang 96. | **2/2**. Trả lời “thây vô chủ” lấy bên sông để đánh lạc hướng. Chunk được trích có trong context, đúng trang 96 và hỗ trợ câu trả lời. |
| `t03` | **0/0**. Context không có tấm biển “Chiêu ẩn am” ở trang 118. | **0/0**. Trang 188 nhắc một am và Giác Duyên nhưng thuộc cảnh khác, không có ba chữ trên tấm biển được hỏi. |
| `t04` | **0/0**. Trang 153 đứng thứ hai ở lượt truy vấn gốc nhưng bị loại khỏi context cuối. Hai chunk còn lại nói về đề thơ và bút nghiên. | **2/2**. Trả lời sông Tiền Đường. Chunk được trích có trong context, đúng trang 153 và chứa cả tên sông lẫn chi tiết viết tuyệt bút. |
| `t05` | **0/0**. Context thiếu đoạn mẹ Kiều nhắc 15 năm lưu lạc ở trang 176. | **0/0**. Context có lời kể ở các cảnh khác nhưng thiếu đoạn đoàn viên và mốc 15 năm. |
| `t06` | **Từ chối đúng** sau 4 lượt. Câu trả lời không đưa ra ngày sinh. | **Từ chối đúng** sau 4 lượt. Các mốc thời gian trong context không xác định ngày sinh Từ Hải. |
| `t07` | **Từ chối đúng** sau 4 lượt. Trang 172 chỉ nêu chức danh thổ tù. | **Từ chối đúng** sau 4 lượt. Tên Từ Hải ở trang 170 thuộc nhân vật khác. Trang 172 chỉ nêu chức danh thổ tù. |

Hybrid đưa bằng chứng vào context ở 2/5 ca test có đáp án, giảm từ chối nhầm từ 5/5 xuống 3/5. Context Evidence Rate giảm từ 12/15 trên dev xuống 2/5 trên test. Ca `t04` cho thấy lý do cần đo context riêng với ranking. Ca `t06` và `t07` đều dừng do chạm giới hạn tìm kiếm ở cả hai cấu hình.

Không điều chỉnh cấu hình sau khi đọc kết quả test. [Tổng hợp test](../../starter/results/step5/test-20261116-123311/summary.json) · [Trace TF-IDF](../../starter/results/step5/test-20261116-123311/tfidf.jsonl) · [Trace Hybrid](../../starter/results/step5/test-20261116-123311/hybrid_budget.jsonl) · [Lệnh chạy và cách chấm](../../docs/dev-benchmark.md#chạy-test-với-cấu-hình-đã-chốt)

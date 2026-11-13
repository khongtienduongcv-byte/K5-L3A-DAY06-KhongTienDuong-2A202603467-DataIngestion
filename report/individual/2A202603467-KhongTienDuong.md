# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline
- Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:
  - Chủ đề: Fifty Famous People: A Book of Short Stories (James Baldwin).
  - Nguồn/quyền: Project Gutenberg eBook #6168, công khai (public domain), giấy phép Project Gutenberg License.
  - Số trang: 47 đơn vị (mỗi chương sách tính là 1 trang/truy vết). Không tính trang bìa, mục lục, trang trống.
  - Quy tắc tính: Tách theo heading chương (viết hoa toàn bộ). Mỗi chương có ID duy nhất (ch_<TEN_CHUONG>), số ký tự ghi trong manifest.json.

- Chuẩn hóa, lỗi và giới hạn:
  - Chuẩn hóa Unicode (CRLF → LF, xóa khoảng trắng dư).
  - Toàn bộ sách được nạp từ file chapters.json (sinh từ book_text.txt).
  - Giới hạn: sách dạng text không có trang vật lý, nên dùng chương làm đơn vị truy vết thay cho số trang PDF.

- Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí:
  - Provider: OpenRouter (openai/text-embedding-3-small, 1536 chiều), fallback Gemini (models/embedding-001, 768 chiều).
  - Vector store: PostgreSQL 16 + pgvector 0.8.7 (Docker), metric cosine distance.
  - Lệnh chạy: `cd starter && python -m src.run` (ingestion), `python -m src.run_eval` (evaluation).
  - Chi phí: 0 USD (dùng API key free tier, chỉ 1 luồng để tiết kiệm rate limit).

- Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn:
  - Bắt buộc: document_id, source, page.
  - Bổ sung: chapter (giá trị lấy từ heading chương trong sách), lý do: dataset benchmark dùng filter chapter cho các câu hỏi metadata.

## Cấu hình và benchmark
- A / B / C (tham số cụ thể, khác biệt duy nhất B–C):
  - A: fixed-size 3000 ký tự, overlap 300, không metadata filter.
  - B: by_paragraph max_size 5000, không metadata.
  - C: by_paragraph max_size 5000, có metadata chapter (gán theo heading chương).
  - Khác biệt duy nhất B–C: C thêm trường metadata `chapter` để filter.

- ≥20 câu: phân chia 15 dev / 5 test, câu metadata filter và cách kiểm chứng evidence:
  - 20 câu (15 dev / 5 test) trong benchmark/dataset.json.
  - Mỗi câu có evidence_quote, gold_source_id, filter (chapter).
  - Evidence được kiểm chứng trực tiếp từ nguồn chương tương ứng.

- Tiêu chí chọn chiến lược đã chốt trước khi xem test:
  - Chốt ưu tiên Hit@3, sau đó grounding, rồi tài nguyên (chi phí/thời gian).

## Kết quả
| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---|---|---|---|---|
| A | dev/test | 50/20 (50%) | 60/20 (60%) | 82 | ~1 phút | 0 USD |
| B | dev/test | 10/20 (10%) | 2/20 (10%) | 47 | ~1 phút | 0 USD |
| C | dev/test | 10/20 (10%) | 2/20 (10%) | 47 | ~1 phút | 0 USD |

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| A | 1.5 (10) | 15/15 | N/A | 1.2 (5) |
| B | 1.8 (10) | 15/15 | N/A | 1.4 (5) |
| C | 1.8 (10) | 15/15 | 5/5 | 1.4 (5) |

Đường dẫn trace, nhãn thủ công và cách chọn mẫu:
- results/evaluation_traces.json (sinh khi chạy eval)
- Nhãn thủ công: 10 vị trí chunk coherence, 5 câu test grounding, 5 câu metadata usefulness

## Phân tích và kết luận
- So sánh A–B và B–C; 2 ví dụ sai có ID câu và nguồn:
  - A–B: Hit@3 từ 60% xuống 10% (A tốt hơn 50 điểm tuyệt đối). Nguyên nhân: chunk fixed-size 3000 của A giữ được câu trả lời gần nhau, còn chunk by_paragraph 5000 của B quá dài, làm vector trung bình bị "đội" và từ khóa câu hỏi bị nhút nhát.
  - Ví dụ sai q17 (test, "How a Prince Learned to Read"): A hit top-3, B/C không hit vì chapter Alfred bị trộn lẫn trong chunk 5000 ký tự.
  - B–C: Hit@3 bằng hệt nhau (10%). Filter chapter của C không giúp ích vì chunk quá lớn, từ khóa câu hỏi bị pha loãng.

- Chiến lược chọn, đánh đổi, điều kiện áp dụng:
  - Chọn **Strategy A** (fixed-size 3000/300) vì Hit@3 cao nhất (60%).
  - Đánh đổi: A có nhiều chunk hơn (82 vs 47), tốn hơn một chút lưu trữ nhưng đáng giá vì độ chính xác cao gấp 6 lần.
  - Điều kiện áp dụng: A phù hợp khi corpus ngắn, câu hỏi cụ thể cần trích đoạn ngắn. B/C phù hợp hơn nếu cần nhóm theo ý nghĩa đoạn văn và corpus lớn.

- Hạn chế của dữ liệu, nhãn, test nhỏ, đo thời gian/chi phí:
  - Test chỉ 5 câu, không đủ đại diện.
  - Sách dạng text không có trang vật lý, dùng chương làm proxy.
  - Chỉ 4/6 OpenRouter keys sống, chạy 1 luồng để tiết kiệm rate limit.

- Nếu làm lại hoặc mở rộng, cải tiến gì?
  - Thử chunk size nhỏ hơn (800-1200) để cân bằng giữa độ chính xác và số chunk.
  - Thêm hybrid retrieval (BM25 + dense) để cải thiện câu hỏi trực tiếp.
  - Tăng số câu test (≥20 test).

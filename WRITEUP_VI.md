# Chibi Diary & Wellbeing Companion

**Track:** Concierge Agents  
**Tác giả:** Z (datlq@mynavitechtus.com)  
**Dự án:** [GitHub Repo](https://github.com/zanykt95-create/chibi-diary-wellbeing-companion) | [Video Demo](https://www.youtube.com/watch?v=8AcrdQWtwEs)

---

## Vấn đề: Viết nhật ký đang bị "gãy" với con người hiện đại

Hầu hết mọi người đều biết rằng viết nhật ký tốt cho họ. Nghiên cứu liên tục chỉ ra rằng thói quen phản tư thường xuyên giúp giảm lo âu, cải thiện điều tiết cảm xúc và nâng cao nhận thức bản thân. Nhưng thói quen đó hiếm khi bền vững. Trang giấy trắng thật đáng sợ. Đọc lại những ghi chú cũ thật nhàm chán. Không có vòng phản hồi — bạn viết vào khoảng trống và chẳng bao giờ biết có gì đang thay đổi hay không.

Nguyên nhân gốc rễ là viết nhật ký truyền thống chỉ là độc thoại một chiều. Bạn đổ suy nghĩ lên trang giấy, và không có gì phản hồi lại. Không có gì ghi nhớ. Không có gì kết nối điểm tâm trạng của bạn hôm thứ Ba tuần trước với hôm nay.

Điều gì sẽ xảy ra nếu cuốn nhật ký của bạn thực sự có thể *lắng nghe*?

---

## Giải pháp: Một Concierge Agent thực sự hiểu bạn

**Chibi Diary & Wellbeing Companion** là agent đồng hành nhật ký cá nhân được xây dựng trên Google ADK. Bạn chia sẻ ngày hôm nay của mình — bằng văn bản hoặc giọng nói — và agent lo phần còn lại: xác thực ghi chú của bạn, phân tích trạng thái cảm xúc, tạo ra một minh hoạ chibi cá nhân hoá phản ánh tâm trạng của bạn, và lưu trữ mọi thứ vào một lớp bộ nhớ bền vững ngày càng thông minh hơn theo thời gian.

Mỗi tương tác là một cuộc trò chuyện hai chiều. Theo ngày, tuần và tháng, agent nhớ lại các xu hướng của bạn, làm nổi bật các mô hình ("bạn đang căng thẳng 5 ngày liên tiếp rồi đấy"), và tổng hợp thành các chibi diary recap theo tuần và tháng — một bản tóm tắt hành trình cảm xúc của bạn dưới dạng hình ảnh sinh động, có thể chia sẻ.

Kết quả là một người bạn đồng hành nhật ký cảm giác ít giống việc viết vào một cuốn sổ hơn và giống như đang nói chuyện với một người bạn chu đáo không bao giờ quên bất cứ điều gì bạn đã nói.

---

## Tại sao cần Agent (không chỉ là một Chatbot)?

Một prompt LLM đơn lẻ không thể làm tốt điều này. Mỗi tác vụ đòi hỏi chuyên môn, công cụ và quyền truy cập bộ nhớ khác nhau:

- **Xác thực một ghi chú** đòi hỏi tư duy khác với **phân tích cảm xúc**.
- **Tạo ảnh chibi** đòi hỏi gọi một mô hình hình ảnh bên ngoài qua công cụ — không phải thứ mà một lần text-completion đơn lẻ có thể thực hiện natively.
- **Lưu trữ và truy vấn bộ nhớ** đòi hỏi các thao tác cơ sở dữ liệu cần đáng tin cậy và có thể lặp lại, không mang tính xác suất.
- **Điều phối tất cả những điều này** đòi hỏi một lớp orchestration đảm bảo mỗi bước nhận được đúng đầu vào và tạo ra đầu ra sạch cho giai đoạn tiếp theo.

Đây chính xác là vấn đề mà hệ thống multi-agent giải quyết. Bằng cách phân rã tác vụ thành các agent chuyên biệt kết nối trong một pipeline, mỗi agent có thể làm tốt một việc, và hệ thống tổng thể trở nên dễ bảo trì, dễ kiểm thử và dễ mở rộng hơn.

---

## Kiến trúc: Bốn Agent, Một Pipeline

Hệ thống sử dụng `SequentialAgent` của Google ADK — agent workflow chạy các sub-agent theo thứ tự cố định, mang tính xác định — để điều phối bốn sub-agent chuyên biệt:

```
Đầu vào từ người dùng
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│                   ORCHESTRATOR                          │
│                  (ADK SequentialAgent)                  │
└──────────┬──────────────────────────────────────────────┘
           │  Truyền state qua chuỗi output_key
           ▼
┌──────────────────┐    ┌───────────────────┐    ┌──────────────────────┐    ┌───────────────────┐
│  Capture Agent   │───▶│ Mood Analysis     │───▶│ Chibi Illustrator    │───▶│  Memory Agent     │
│  Giai đoạn 1     │    │ Agent  Giai đoạn 2│    │ Agent  Giai đoạn 3   │    │  Giai đoạn 4      │
│                  │    │                   │    │                      │    │                   │
│ - Sanitize input │    │ - Phát hiện cảm   │    │ - MCP → Imagen 3     │    │ - Nhớ lại xu hướng│
│ - Kiểm toán bảo  │    │   xúc             │    │ - Map mood thành     │    │ - Lưu vào SQLite  │
│   mật            │    │ - Score + nhãn    │    │   prompt             │    │ - Context insight │
│ - Output: văn bản│    │ - Output: báo cáo │    │ - Output: đường dẫn  │    │ - Đếm streak      │
│   đã làm sạch    │    │   + tâm trạng     │    │   PNG                │    │                   │
└──────────────────┘    └───────────────────┘    └──────────────────────┘    └───────────────────┘
                                                          │
                                              ┌───────────┴───────────┐
                                              │    MCP SERVER         │
                                              │  (FastMCP / stdio)    │
                                              │  Imagen 3 via         │
                                              │  google-genai SDK     │
                                              └───────────────────────┘
```

### Trách nhiệm của từng Agent

**Capture Agent** là điểm đầu vào và cổng bảo mật. Nó nhận đầu vào thô từ người dùng, loại bỏ HTML, cắt ngắn xuống còn 2.000 ký tự, phát hiện các mẫu prompt injection và SQL injection, và ghi vào `SECURITY_AUDIT_LOG` theo thời gian thực. Chỉ có chuỗi đã được xác thực và làm sạch mới được chuyển sang giai đoạn tiếp theo. `output_key="captured_entry"` làm cho đầu ra này khả dụng cho tất cả các agent downstream thông qua session state được chia sẻ của ADK.

**Mood Analysis Agent** nhận ghi chú đã làm sạch và thực hiện phân loại cảm xúc bằng Gemini 2.5 Flash. Nó xuất ra một `mood_report` có cấu trúc chứa nhãn tâm trạng chính thuộc một tập cố định gồm sáu nhóm (`happy`, `sad`, `anxious`, `grateful`, `excited`, `neutral`), điểm cường độ (0.0–1.0) và các từ khoá cảm xúc. Đầu ra có cấu trúc này là thứ điều khiển minh hoạ chibi — không phải văn bản thô.

**Chibi Illustrator Agent** ánh xạ báo cáo tâm trạng thành một prompt tạo ảnh chi tiết (thông qua helper `map_mood_to_chibi_prompt`, được kiểm thử unit test đầy đủ), sau đó gọi công cụ MCP Server để gọi Imagen 3. PNG được tạo ra được lưu cục bộ và đường dẫn của nó được lưu trong `chibi_result`. Nếu tạo ảnh thất bại, agent thoái hóa nhẹ nhàng với một ghi chú lỗi thay vì làm hỏng toàn bộ pipeline.

**Memory Agent** là thành phần có trạng thái nhất. Trước khi lưu, nó nhớ lại xu hướng tâm trạng gần đây và streak hiện tại của người dùng từ SQLite. Ngữ cảnh này được đưa vào đầu ra cuối cùng dưới dạng `context_insight` — một ghi chú ngắn bằng tiếng Việt (ví dụ: "Bạn đang có chuỗi 5 ngày liên tiếp tâm trạng tích cực!"). Sau khi tạo ra insight này, nó lưu trữ toàn bộ ghi chú (văn bản, tâm trạng, đường dẫn chibi, thẻ) vào cơ sở dữ liệu dài hạn.

---

## Chi tiết triển khai quan trọng

### MCP Server: Kết nối Agent với tính năng Tạo ảnh

Khả năng tạo ảnh được hiển thị dưới dạng MCP (Model Context Protocol) server được xây dựng bằng FastMCP, sử dụng transport `stdio`. Server hiển thị một công cụ duy nhất, `generate_chibi_image`, nhận vào một chuỗi `prompt` và trả về đường dẫn PNG cục bộ.

Chibi Illustrator Agent kết nối đến server này tại runtime bằng `McpToolset` của ADK với `StdioConnectionParams` (timeout được đặt là 60 giây để phù hợp với độ trễ của Imagen 3). Việc tách riêng tính năng tạo ảnh thành MCP server có nghĩa là nó có thể được hoán đổi, nâng cấp hoặc thay thế mà không cần chạm vào bất kỳ mã agent nào.

```python
# mcp_server/chibi_mcp_server.py (đơn giản hoá)
from mcp.server.fastmcp import FastMCP
from google import genai

mcp = FastMCP("chibi-image-server")

@mcp.tool()
async def generate_chibi_image(prompt: str) -> str:
    """Tạo minh hoạ chibi và trả về đường dẫn PNG đã lưu."""
    client = genai.Client()
    response = client.models.generate_images(
        model="imagen-3.0-generate-001",
        prompt=prompt,
        config={"number_of_images": 1, "safety_filter_level": "BLOCK_ONLY_HIGH"},
    )
    # Lưu và trả về đường dẫn...
```

### Tính năng Bảo mật

Class `InputSanitizer` trong `capture_agent.py` triển khai bốn lớp bảo vệ:

1. **Loại bỏ HTML** — xóa tất cả các thẻ để ngăn chặn markup injection.
2. **Cắt ngắn độ dài** — giới hạn đầu vào ở mức 2.000 ký tự.
3. **Phát hiện prompt injection** — gắn cờ các mẫu như `ignore previous instructions`, `you are now`, `system:`.
4. **Phát hiện SQL injection** — gắn cờ các mẫu SQL cổ điển như `DROP TABLE`, `UNION SELECT`, `; --`.

Mỗi ghi chú được xử lý đều được ghi vào `SECURITY_AUDIT_LOG` với dấu thời gian, hash đầu vào và các cờ được kích hoạt. Log này nằm trong bộ nhớ cho bản demo nhưng được thiết kế để ghi ra file hoặc sink bên ngoài trong môi trường production.

### Kiến trúc Bộ nhớ

Bộ nhớ dài hạn được lưu trong cơ sở dữ liệu SQLite (`diary.db`) với schema hỗ trợ tìm kiếm toàn văn bản trên các ghi chú nhật ký, truy vấn xu hướng tâm trạng, recap hàng tháng và tính toán streak. Bốn phương thức async (`search_entries`, `get_mood_trend`, `get_monthly_recap`, `get_streak`) được hiển thị dưới dạng ADK tools cho Memory Agent.

Bộ nhớ ngắn hạn sử dụng từ điển `session.state` tích hợp sẵn của ADK, truyền đầu ra có cấu trúc giữa các agent trong một lần chạy pipeline thông qua chuỗi `output_key`.

### Khả năng Triển khai

Dự án đi kèm với `Dockerfile` sẵn sàng cho production (dựa trên `python:3.11-slim` với `uv` để cài đặt dependencies nhanh), `cloudbuild.yaml` cho Google Cloud Build, và script `deploy.sh` build và deploy lên Cloud Run chỉ với một lệnh. Agent sử dụng Application Default Credentials (ADC) với Vertex AI, giúp triển khai an toàn mà không cần hardcode API key.

---

## Xây dựng trong Google Antigravity

Toàn bộ dự án được phát triển bên trong Google Antigravity — IDE agentic của Google sử dụng Gemini 3 hoặc Claude để viết, chạy, kiểm thử và lặp lại trên code thông qua các prompt ngôn ngữ tự nhiên. File spec `GEMINI.md` ở thư mục gốc của dự án định nghĩa kiến trúc, các ràng buộc và hành vi mong đợi cho agent Antigravity.

Cách tiếp cận này — phát triển theo spec với IDE agentic — bản thân nó là một minh chứng cho luận điểm cốt lõi của khoá học: agent không chỉ cung cấp sức mạnh cho các sản phẩm end-user; chúng thay đổi về cơ bản cách phần mềm được xây dựng. Agent Antigravity đã viết hàng trăm dòng code, sửa lỗi, tái cấu trúc schema bộ nhớ và tạo ra bộ kiểm thử đầy đủ — tất cả từ các thông số kỹ thuật ngôn ngữ tự nhiên có cấu trúc.

---

## Kiểm thử và Đánh giá

Dự án bao gồm 59 bài kiểm thử trên bốn file test:

| File Kiểm thử | Số lượng | Phạm vi |
|---|---|---|
| `test_orchestrator.py` | 35 | Pipeline E2E, đầu ra agent, lưu trữ SQLite, ADK tools của Memory Agent (trend, recap, streak) |
| `test_evaluation.py` | 15 | Độ chính xác tâm trạng, chất lượng prompt chibi, tính đúng đắn của bộ nhớ |
| `test_security.py` | 5 | InputSanitizer: HTML, cắt ngắn, phát hiện injection |
| `test_mcp_server.py` | 4 | Schema MCP `generate_chibi_image` + khởi tạo ImagenClient |

Tất cả 59 bài kiểm thử đều pass. Framework đánh giá trong `test_evaluation.py` tạo ra `eval_report.json` với `pass_rate: 1.0`, bao gồm độ chính xác phân tích tâm trạng, điểm chất lượng prompt chibi, tính đúng đắn của truy xuất bộ nhớ và tính toàn vẹn pipeline end-to-end.

---

## Các Khái niệm được Thể hiện

| Khái niệm | Vị trí |
|---|---|
| ✅ Hệ thống Multi-agent (ADK) | `chibi_diary/orchestrator.py` — pipeline 4-agent SequentialAgent/Workflow |
| ✅ MCP Server | `mcp_server/chibi_mcp_server.py` — FastMCP stdio, Imagen 3 |
| ✅ Tính năng Bảo mật | `chibi_diary/agents/capture_agent.py` — InputSanitizer + SECURITY_AUDIT_LOG |
| ✅ Khả năng Triển khai | `Dockerfile`, `cloudbuild.yaml`, `deploy.sh` — sẵn sàng cho Cloud Run |
| ✅ Antigravity | Toàn bộ code được build qua các prompt spec-driven trong Google Antigravity IDE |

---

## Giá trị và Tác động

**Với người dùng**, Chibi Diary giải quyết vấn đề duy trì thói quen viết nhật ký bằng cách loại bỏ rào cản và thêm vào sự thú vị. Các minh hoạ chibi mang lại cho mỗi ghi chú một bản sắc hình ảnh — thứ mà bạn thực sự muốn xem lại. Các insight xu hướng làm nổi bật các mẫu mà bạn sẽ không tự nhận ra được. Bộ đếm streak cung cấp động lực để tiếp tục.

**Với lĩnh vực**, dự án này chứng minh rằng các concierge agent mạnh mẽ nhất khi chúng kết hợp ba khả năng mà không có prompt LLM đơn lẻ nào có thể cung cấp: **bộ nhớ bền vững** (bạn phát triển cùng người dùng của mình), **sử dụng công cụ bên ngoài** (bạn có thể tạo ra, không chỉ phân tích), và **điều phối multi-agent có cấu trúc** (mỗi mối quan tâm được xử lý bởi đúng chuyên gia).

Kiến trúc được thiết kế đủ đơn giản để hiểu và mở rộng, nhưng đủ hoàn chỉnh để chạy end-to-end trên dữ liệu thực. Với 59 bài kiểm thử đều pass, một MCP image server đang hoạt động, một lớp bộ nhớ bền vững, một pipeline đầu vào được bảo vệ bằng bảo mật, và hỗ trợ triển khai Cloud Run, Chibi Diary & Wellbeing Companion không phải là một prototype — đây là một hệ thống đang hoạt động được xây dựng theo các tiêu chuẩn mà khoá học đặt ra để dạy.

---

*Được xây dựng với Google ADK 2.3.0, FastMCP, Imagen 3, Gemini 2.5 Flash và Google Antigravity.*  
*59/59 bài kiểm thử đều pass. 5/6 khái niệm chính được thể hiện.*

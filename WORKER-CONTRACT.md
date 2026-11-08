# Giao tiếp giữa worker và server

Giao thức HTTP đang dùng trong bản 1.2.0. Worker sinh ảnh local và gửi kết quả về server; việc nghiệm thu trên các VM thật thực hiện theo hướng dẫn triển khai.

## Địa chỉ và xác thực

Worker gọi cổng API riêng, mặc định `http://127.0.0.1:8081` khi thử cùng máy. Khi triển khai trên máy khác, đổi `WORKER_BIND` trong `.env` thành IP mạng riêng của máy chủ, rồi khởi động lại dịch vụ API. Cấu hình mạng để worker truy cập IP đó. Cổng website không cho đi vào `/internal`.

Mỗi worker dùng một ID đã đăng ký trong `.credentials/workers.json`, không cần Bearer token. Khóa quản trị API vẫn dùng cho các thao tác quản trị. Worker gửi lựa chọn model trong heartbeat/claim; server kiểm tra model được phép theo ID. ID 3.1 mặc định DreamShaper8 LCM; 2.1 và 4.1 mặc định SD-Turbo.

## Chu kỳ làm việc

1. `POST /internal/workers/2.1/heartbeat` với JSON `{"models":["sd-turbo"]}` khi khởi động; không cần header Authorization cho worker.
2. `POST /internal/workers/2.1/claim`, với JSON lựa chọn models như heartbeat. Nếu `job` là `null`, đợi `poll_after` giây rồi hỏi lại. Worker chỉ nhận một công việc một lúc.
3. Công việc trả về có `id`, `name`, `prompt`, `seed`, `model_id`, `lease`, `lease_seconds`, `heartbeat_after`. Prompt đã ghép phong cách Neon. Worker chạy mô hình local, sinh ảnh PNG hoặc JPEG từ 128 px mỗi chiều.
4. Trong lúc tạo và gửi file, cứ `heartbeat_after` giây gửi `POST .../heartbeat` với JSON `{"job_id":"...","lease":"..."}`. Cần heartbeat chạy song song với quá trình sinh, không đợi sinh xong mới gia hạn.
5. Gửi kết quả bằng `POST /internal/workers/2.1/jobs/<JOB_ID>/complete`, multipart: `lease`, `model_id`, `file`. Tối đa 10 MB; mỗi chiều từ 128 đến 4096 px. Server tự đặt tên, bỏ metadata tệp không cần thiết và lưu PNG.
6. Chỉ xóa ảnh tạm sau khi server xác nhận. Khi mất mạng có thể gửi lại cùng ID và lease; server trả ảnh đã lưu, không ghi trùng.
7. Lỗi sinh: `POST .../jobs/<JOB_ID>/fail` với `{"lease":"...","message":"..."}`. Server quản lý số lần thử. Nếu nhận HTTP 409 vì lease cũ, worker bỏ quyền xử lý cũ, không ép gửi kết quả vào công việc đã giao lại.

## Trạng thái

- `queued`: chờ worker.
- `running`: worker đang giữ lease.
- `succeeded`: file và thông tin đã được lưu.
- `failed`: đã vượt số lần thử, cần thử lại có chủ đích.
- `cancelled`: quản trị đã hủy yêu cầu.

Việc tìm kiếm có ưu tiên 100, sinh nền 10. Ưu tiên áp dụng khi nhận việc mới; không ngắt ảnh đang tạo. Các yêu cầu cùng tên đang chờ hoặc chạy dùng chung một job. Hàng đợi bền vững trong CSDL của server, không nằm trong bộ nhớ worker.

Khi worker khởi động lại sau lỗi, dùng giao thức phục hồi bằng cách chờ lease cũ hết hạn hoặc báo lỗi bằng thông tin lease đã lưu. Không tự nhận nhiều job để giữ trước.

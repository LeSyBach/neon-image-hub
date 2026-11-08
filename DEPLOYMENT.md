# Triển khai phiên bản 1.2.0

Nhóm dùng một VM server và ba VM worker với ID 2.1, 3.1, 4.1.

1. Thực hiện [hướng dẫn server](guides/HUONG-DAN-SERVER-MAY-MOI.md).
2. Cấp đúng ID và địa chỉ API Tailscale cho từng thành viên; không cần token worker.
3. Các thành viên làm [hướng dẫn worker ngắn](guides/HUONG-DAN-WORKER-MAY-MOI.md).
4. Đăng ký agent giám sát cho cả bốn VM và thử log trên điện thoại.
5. Cấu hình Cloudflare Tunnel trên VM server cho hostname kho ảnh, HTTP localhost:8080.

Máy đã có bản cũ dùng [hướng dẫn nâng cấp](guides/NANG-CAP-1.2.0-KHONG-TOKEN.md), không khởi tạo lại trong thư mục có dữ liệu.
Không cần các gói ZIP hoặc gói worker riêng của các phiên bản trước.

Model gốc ở D:\codex-neon-local\models. Ảnh/CSDL trên máy phát triển ở data/hub/.
Thư mục dist/dockerhub-1.2.0 chứa tài nguyên triển khai và xác minh bản mới nhất.

## Vận hành sau khi cài

- Bật/tắt trong đúng thư mục triển khai: `docker compose up -d` / `docker compose stop`.
- Đổi ID/model/IP/CPU/RAM/threads: sửa file ngoài container, rồi tạo lại đúng dịch vụ theo hướng dẫn server/worker.
- Pull image rồi up khi cần cập nhật; Git pull chỉ lấy code/tài liệu, không tự thay image đang chạy.
- Hướng dẫn cập nhật đã có backup, nâng 1.0/1.1 lên 1.2.0, thay web/nginx bind mount và kiểm tra sau cập nhật.
- Model tải bằng curl ngay trên VM worker; không bắt buộc chuyển file từ máy phát triển.

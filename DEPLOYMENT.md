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

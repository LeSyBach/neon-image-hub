# Worker AI local và triển khai

Hướng dẫn cho thành viên trên VM nằm tại [guides/HUONG-DAN-WORKER-MAY-MOI.md](guides/HUONG-DAN-WORKER-MAY-MOI.md).
Tất cả dùng `bachcp10/neon-hub-worker:1.2.0`, chỉ cần ID và địa chỉ server; model AI chuyển riêng.
Phần giám sát có trong [hướng dẫn chi tiết](guides/HUONG-DAN-WORKER-CHI-TIET.md).

## Thử tại Windows/WSL

Trong PowerShell tại D:\neon-image-hub:

```powershell
.\start-worker.ps1
.\start-worker.ps1 -Model dreamshaper-8-lcm
.\stop-worker.ps1
.\stop.ps1
```

Script chạy server và một worker local, dừng worker còn lại khi đổi model để tránh quá tải RAM.
Đây là thử nghiệm cùng một máy, không phải ba VM thành viên.

- Model gốc: D:\codex-neon-local\models, mount chỉ đọc vào container.
- Trạng thái/ảnh tạm/log: data/worker-2.1 hoặc data/worker-3.1.
- Worker dùng CPU, mặc định 6 CPU/5 GiB RAM ở cấu hình thử local; không dùng swap thêm.
- Mỗi job hiện nạp model qua sd-cli, chưa giữ model sẵn trong RAM giữa các job.
- pending.json phục vụ khôi phục việc; không xóa khi đang xử lý.
- File pause chỉ tạm dừng nhận việc mới; ảnh đang tạo được tiếp tục.
- Ảnh hoàn tất được gửi về API và lưu ở kho chung của server.

Không còn cần ba gói handoff cũ chứa các bản sao model. Bản gốc và mã nguồn dùng chung được giữ ở các thư mục trên.

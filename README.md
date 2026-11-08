# Neon Image Hub — bản 1.2.0

Kho ảnh Neon cho nhóm bốn người: một server và ba worker `2.1`, `3.1`, `4.1`.
Worker kết nối bằng ID và địa chỉ API qua Tailscale, không cần token worker.

## Triển khai trên VM Ubuntu

Image công khai, kiến trúc linux/amd64:

- `bachcp10/neon-hub-api:1.2.0`
- `bachcp10/neon-hub-worker:1.2.0`

Các tài liệu chính:

- [Cài server](guides/HUONG-DAN-SERVER-MAY-MOI.md).
- [Cài worker — ngắn gọn](guides/HUONG-DAN-WORKER-MAY-MOI.md).
- [Giám sát và xử lý lỗi worker](guides/HUONG-DAN-WORKER-CHI-TIET.md).
- [Nâng cấp máy đã cài bản cũ](guides/NANG-CAP-1.2.0-KHONG-TOKEN.md).

Image có lệnh setup tạo Compose và cấu hình tại VM; không cần chép ZIP dự án.
Model AI nằm ngoài image; dùng lệnh curl trong hướng dẫn worker để tải trực tiếp vào models/ trên VM.
Không cần gửi model từ Windows, không cần clone code để chạy image đã phát hành.
Kho model gốc trên máy phát triển: `D:\codex-neon-local\models`.

## Bật/tắt, đổi cấu hình và cập nhật

Trong đúng thư mục triển khai: `docker compose up -d` để bật, `docker compose stop` để tắt.
`start` chỉ bật container đã có; `up -d` không tạo trùng bộ container và áp dụng image/.env đã đổi.
Không pull lại mỗi lần bật. Khi có image mới: pull rồi up; khi sửa file JSON bind mount,
tạo lại đúng dịch vụ bằng `up -d --force-recreate` theo hướng dẫn.

- [Server: cài mới, IP/cổng, thêm ID/model được phép](guides/HUONG-DAN-SERVER-MAY-MOI.md).
- [Worker: ID, server_url, model, RAM, CPU, threads, log và WSL](guides/HUONG-DAN-WORKER-MAY-MOI.md).
- [Cập nhật: Docker pull, Git pull, backup, nâng cấp và giao diện bind mount](guides/NANG-CAP-1.2.0-KHONG-TOKEN.md).

Image hiện dùng tag 1.2.0; cập nhật tài liệu trên GitHub không tự tạo image mới.
Web/nginx được xuất ra VM và bind mount nên pull API không tự thay phần giao diện.

## Cấu trúc còn sử dụng

| Thư mục | Nội dung |
|---|---|
| `server/` | API, hàng đợi SQLite, quản lý ảnh, lập lịch nền |
| `worker/` | Client/runner AI và runtime CPU |
| `setupkit/` | Khởi tạo/nâng cấp từ image và payload công khai |
| `web/`, `nginx.conf` | Giao diện và cấu hình web |
| `scripts/`, `tests/` | Công cụ vận hành và kiểm thử |
| `guides/` | Hướng dẫn hiện tại |
| `dist/dockerhub-1.2.0/` | Tài nguyên triển khai, digest và kết quả xác minh bản mới nhất |
| `exports/gallery-import/` | Snapshot và công cụ nhập 35 ảnh cũ vào VM |
| `data/` | CSDL, ảnh, trạng thái worker, dữ liệu giám sát/thông báo |
| `backups/` | Sao lưu dữ liệu và cấu hình |
| `test-results/` | Minh chứng kiểm thử, ảnh thật và screenshot |

`.env` giữ cấu hình cổng, khóa quản trị và thông tin ntfy/Beszel. `.credentials/`
giữ cấu hình worker/agent local; tệp cũ có trường token worker vẫn đọc được nhưng
server 1.2.0 không dùng nó. Không công khai các file chứa khóa quản trị/giám sát.

## Chạy thử tại máy phát triển Windows/WSL

Phần này bật **server local để phát triển**, khác với chỉ chạy worker trong WSL nối tới server trên VM.
Worker 1.1 đang dùng trên máy phát triển có cấu hình riêng ở
`D:\neon-image-hub\data\worker-1.1` (WSL: `/mnt/d/neon-image-hub/data/worker-1.1`),
không nằm trong Git và không được tạo tự động khi clone trên máy khác.
Muốn quản lý riêng worker đó, vào thư mục cấu hình của nó rồi chạy Compose; không chạy start.ps1 của repo.

Trong PowerShell tại `D:\neon-image-hub`:

```powershell
.\start.ps1
.\start-worker.ps1 -Model sd-turbo
.\stop-worker.ps1
.\stop.ps1
```

`start-worker.ps1` chọn một worker AI local tại một thời điểm; đổi sang
`-Model dreamshaper-8-lcm` để thử model B. Đây là kiểm thử một máy, không thay thế
việc nghiệm thu trên bốn VM thật. Các script start giữ WSL chạy bằng helper ẩn.
Docker Engine/cache vẫn ở WSL, chưa chuyển toàn bộ sang ổ D.

## Cổng và dữ liệu

- Website: 8080. Mặc định WEB_BIND=127.0.0.1; để Windows truy cập qua IP LAN của VM, đặt WEB_BIND=0.0.0.0 rồi chạy lại `docker compose up -d`.
- API worker: 8081, bind vào IP Tailscale khi triển khai VM.
- Beszel Hub: 8090; ntfy: 8091. Mở qua mạng riêng theo hướng dẫn.
- Cloudflared cài trực tiếp trên VM server trỏ HTTP tới 127.0.0.1:8080.
- Kho ảnh/CSDL: `data/hub/images/` và `data/hub/hub.sqlite3`.

Ảnh do worker gửi qua API được lưu cùng bản ghi CSDL và tự hiện lên web. Ảnh chép
bằng WinSCP cần nhập metadata; công cụ nhập kho cũ ở `exports/gallery-import/` trên máy phát triển, không có trong bản clone GitHub.

## Kiểm tra và đóng gói

- 46 kiểm thử ứng dụng/worker/setup đã đạt ở bản 1.2.0; bootstrap UID 1000 và nâng cấp giữ dữ liệu đã được kiểm tra.
- `scripts/test.sh` chạy bộ kiểm thử trong container tạm.
- `scripts/build_setup_payload.py` tạo lại payload từ tài nguyên triển khai 1.2.0.
- `scripts/verify_no_token_images.py` kiểm tra hai image; không khởi chạy hệ thống thật.
- `scripts/verify_published_no_token.py` kiểm tra pull công khai và digest trên Hub.

Phần nghiệm thu mạng bốn VM, tên miền, ảnh Neon và thông báo trên điện thoại thực
hiện theo hướng dẫn triển khai, không suy ra từ kiểm thử local.

## Lấy cả mã nguồn và model từ GitHub

Repository có mã nguồn, runtime CPU và cả hai model AI + TAESD trong `models/`. Model lưu bằng Git LFS; xem [hướng dẫn tải model](models/README.md).

```bash
git lfs install
git clone https://github.com/LeSyBach/neon-image-hub.git
cd neon-image-hub
git lfs pull
```

File mật khẩu/token đang dùng, CSDL và kho ảnh cá nhân không được đưa lên GitHub. VM mới vẫn khởi tạo cấu hình riêng bằng image Docker theo hướng dẫn.

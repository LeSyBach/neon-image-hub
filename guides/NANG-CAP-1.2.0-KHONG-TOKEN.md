# Cập nhật và vận hành Neon Image Hub — bản hiện có 1.2.0

Tài liệu này dành cho **máy đã cài**. Server làm trên VM server tại `~/neon-server`;
worker làm trên VM worker tại `~/neon-worker`. Root có thể bỏ sudo trong các lệnh dưới đây.
Nếu dùng thư mục khác, vào đúng nơi có compose.yaml của bộ đó; ví dụ worker 1.1 trong WSL dùng
`/mnt/d/neon-image-hub/data/worker-1.1`. Không chạy setup lần đầu trong thư mục đã có dữ liệu.

## 1. Chọn đúng việc cần làm

| Bạn muốn làm gì? | Cách thực hiện |
|---|---|
| Bật sau khi tắt | `docker compose up -d`; không cần pull |
| Tắt, giữ container và dữ liệu | `docker compose stop` |
| Container đã có, cấu hình không đổi | Có thể dùng `docker compose start` |
| Đổi model/ID/IP/CPU/RAM/threads | Sửa cấu hình, kiểm tra cú pháp, tạo lại đúng dịch vụ; xem phần 5 |
| Tải lại image đang khai báo | `docker compose pull` rồi `docker compose up -d`; xem phần 2 |
| Nâng 1.0/1.1 lên 1.2.0 | Backup, chạy setupkit upgrade, pull và tạo lại; xem phần 3 |
| Cập nhật web/nginx bên ngoài image | Lấy tài nguyên từ bản phát hành vào thư mục tạm, chỉ chép file cần đổi; xem phần 4 |
| Lấy code/tài liệu mới từ GitHub | `git pull --ff-only` tại thư mục clone; không tự cập nhật container; xem phần 6 |

`pull` chỉ tải image, chưa thay container đang chạy. `up -d` áp dụng image/cấu hình đã đổi,
tạo dịch vụ thiếu hoặc bật dịch vụ đã dừng; không nhân thêm container trùng trong cùng dự án.
Model, .env, cấu hình JSON và dữ liệu của bộ triển khai nằm ngoài image, giữ nguyên sau pull/up.
Nguồn: [Docker pull](https://docs.docker.com/reference/cli/docker/compose/pull/),
[Docker up](https://docs.docker.com/reference/cli/docker/compose/up/),
[Docker start](https://docs.docker.com/reference/cli/docker/compose/start/).

## 2. Pull lại tag hiện tại và áp dụng

Phiên bản đang dùng là **1.2.0**. Pull tag 1.2.0 không tự nhảy lên tag khác.
Nếu nhà phát hành chưa đổi image ở tag đó thì sẽ không có code mới.
Chỉ sửa tài liệu trên GitHub không có nghĩa là image Docker Hub cũng đã đổi.

### Server

Chạy trên **VM server**. Sao lưu trước khi thay bản chương trình:

```bash
cd ~/neon-server
sudo python3 scripts/backup.py
NEON_CONFIG_BACKUP="$HOME/neon-server-config-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$NEON_CONFIG_BACKUP"
cp -a compose.yaml nginx.conf web scripts "$NEON_CONFIG_BACKUP/"

sudo docker compose pull api scheduler
sudo docker compose up -d
sudo docker compose ps -a
curl -f http://127.0.0.1:8080/api/health
sudo docker compose logs --tail 40 api scheduler web
```

Script backup tạo snapshot CSDL + ảnh + .env + .credentials/ trong backups/.
Thư mục NEON_CONFIG_BACKUP bổ sung Compose/nginx/web/scripts mà backup lõi chưa có.
Nếu tài khoản thường không đọc được file do root tạo trước đó, dùng sudo cho lệnh sao lưu file tương ứng.
Nếu đã đổi WEB_PORT thì thay 8080 bằng cổng thật trong lệnh kiểm tra.

api và scheduler dùng chung image ứng dụng. Lệnh này không chủ động nâng image bên thứ ba.
Muốn tải toàn bộ image có trong Compose thì dùng `sudo docker compose pull`, rồi up;
việc đó có thể cập nhật thêm Nginx/ntfy đang dùng tag thả nổi.
Giữ nguyên .env, .credentials/, data/; không chạy init/setup lại, không xóa CSDL hay kho ảnh.

### Worker

Chạy trên **VM worker**. Ưu tiên chờ ảnh đang tạo xong rồi cập nhật.
Nếu cần ngừng nhận thêm việc trong lúc chờ, tạo marker pause:

```bash
cd ~/neon-worker
touch worker-state/pause
sudo docker compose logs --tail 30 -f worker
```

Nếu đang làm ảnh, đợi dòng Saved by server; Ctrl+C để thoát xem log.
Nếu đã rảnh thì tiếp tục luôn. Marker pause chỉ ngừng nhận việc mới, không hủy ảnh đang tạo.
Sau đó chạy:

```bash
cd ~/neon-worker
sudo docker compose stop worker
NEON_WORKER_BACKUP="$HOME/neon-worker-before-update-$(date +%Y%m%d-%H%M%S).tar.gz"
tar -czf "$NEON_WORKER_BACKUP" compose.yaml .env worker-settings.json worker-state
sudo docker compose pull worker
sudo docker compose up -d worker
sudo docker compose ps -a
sudo docker compose logs --tail 30 worker
```

Sau khi xác nhận container chạy ổn, bỏ **đúng marker đã tạo ở đầu quy trình** để nhận việc tiếp:

```bash
cd ~/neon-worker
rm -f -- worker-state/pause
```

Không xóa pending.json hoặc toàn bộ worker-state. Backup không chứa model 2 GB, model vẫn nằm nguyên trên đĩa.
Nếu không thực hiện bước pause thì không cần tạo/xóa marker. Pull không đổi ID, server_url, model hoặc giới hạn tài nguyên.

## 3. Nâng từ bản 1.0/1.1 lên 1.2.0

Thực hiện backup như phần 2 và **nâng server trước**, rồi mới nâng từng worker.
Các lệnh dưới đây nâng đúng lên bản 1.2.0 đang phát hành; không thay số phiên bản bằng một tag chưa tồn tại.

### Trên VM server

```bash
cd ~/neon-server
sudo docker pull bachcp10/neon-hub-api:1.2.0
sudo docker run --rm --network none \
  --user "$(id -u):$(id -g)" \
  -v "$PWD:/setup" --entrypoint python3 \
  bachcp10/neon-hub-api:1.2.0 -m setupkit upgrade
sudo docker compose pull api scheduler
sudo docker compose up -d --force-recreate api scheduler
sudo docker compose up -d
sudo docker compose ps -a
curl -f http://127.0.0.1:8080/api/health
```

### Trên từng VM worker

Đợi việc đang làm hoàn tất nếu có, giữ marker pause nếu đã dùng ở phần 2.

```bash
cd ~/neon-worker
sudo docker compose stop worker
sudo docker pull bachcp10/neon-hub-worker:1.2.0
sudo docker run --rm --network none \
  --user "$(id -u):$(id -g)" \
  -v "$PWD:/setup" --entrypoint python3 \
  bachcp10/neon-hub-worker:1.2.0 -m setupkit upgrade
sudo docker compose pull worker
sudo docker compose up -d --force-recreate worker
sudo docker compose logs --tail 30 worker
```

Nếu có marker pause do bạn tạo để cập nhật thì bỏ marker khi sẵn sàng nhận việc lại.

**Upgrade 1.2.0 làm gì:** đổi tag image Neon Hub trong Compose và bỏ token worker cũ trong JSON;
lưu file thay đổi với đuôi `.before-1.2.0` nếu bản sao đó chưa có.
Giữ ID, server_url, .env, model đã chọn, CPU/RAM/threads, CSDL, ảnh, model và trạng thái công việc.
Trường token worker cũ được bỏ; khóa quản trị, Beszel và ntfy là phần riêng, vẫn giữ.

**Upgrade không tự thay web/, nginx.conf, scripts/ hoặc hợp nhất toàn bộ Compose mới.**
Nếu cần cập nhật các file này, làm phần 4. Không chạy `setupkit server` hoặc `setupkit worker`
vào thư mục triển khai đang dùng để cố nâng cấp; công cụ khởi tạo yêu cầu thư mục trống.

Với một phiên bản mới sau 1.2.0, dùng ghi chú phát hành của phiên bản đó: kiểm tra tag đã được đẩy lên Hub,
đổi tag trong compose.yaml hoặc dùng công cụ upgrade của bản mới nếu được hỗ trợ, rồi pull/up.
Không cần gửi lại model nếu phiên bản mới vẫn dùng cùng file/checksum model.

## 4. Khi bản cập nhật thay giao diện hoặc nginx.conf

Server đang mount `./web` và `./nginx.conf` từ VM. Pull image API hoặc Git pull ở một thư mục clone khác
không tự thay các file đang được mount này. Chỉ làm phần này khi bản phát hành yêu cầu cập nhật tài nguyên web.

Ví dụ lấy bộ tài nguyên **1.2.0** vào một thư mục tạm mới, không ghi đè cấu hình thật:

```bash
cd ~/neon-server
sudo docker pull bachcp10/neon-hub-api:1.2.0
NEON_UPDATE_DIR=$(mktemp -d "$HOME/neon-server-assets-XXXXXX")
sudo docker run --rm --network none \
  --user "$(id -u):$(id -g)" \
  -v "$NEON_UPDATE_DIR:/setup" --entrypoint python3 \
  bachcp10/neon-hub-api:1.2.0 \
  -m setupkit server --server-ip "$(tailscale ip -4)"
printf 'Thu muc tai nguyen moi: %s\n' "$NEON_UPDATE_DIR"
```

Lệnh setup tạo thêm .env/.credentials trong thư mục tạm, không đụng đến server thật.
Chỉ chép web/nginx sau khi đã backup ở phần 2:

```bash
cd ~/neon-server
cp -a "$NEON_UPDATE_DIR/web/." ./web/
cp -p "$NEON_UPDATE_DIR/nginx.conf" ./nginx.conf
sudo docker compose config --quiet
sudo docker compose up -d --force-recreate web
curl -f http://127.0.0.1:8080/api/health
```

Không chép `.env`, `.credentials` hoặc `data` từ thư mục tạm sang server thật.
Các tùy chỉnh giao diện/nginx cá nhân cần được giữ/hợp nhất trước khi chép bản mới.
Nếu bản phát hành đổi Compose hoặc scripts, so sánh với bản đang dùng và áp dụng theo ghi chú phát hành,
giữ tên project, đường dẫn data, cổng bind và các file bí mật hiện tại. Quy trình trên chỉ thay web/nginx.
Sau khi đổi giao diện, tải lại trình duyệt bằng Ctrl+F5 để tránh dùng cache cũ.
Thư mục tạm chứa cấu hình do setup tạo; giữ riêng trên VM, không đưa lên GitHub.

## 5. Sửa cấu hình sau khi đã cài

| Muốn đổi | Máy/file cần sửa | Cách áp dụng |
|---|---|---|
| ID worker | Worker: worker-settings.json → worker_id; server: .credentials/workers.json | Đăng ký ID trên server, tạo lại API/scheduler, tạo lại worker |
| Địa chỉ server cho worker | Worker: worker-settings.json → server_url | `up -d --force-recreate worker` |
| Model thực tế | Worker: .env → AI_MODEL; có file model và được server cho phép | `up -d --force-recreate worker` |
| CPU và RAM | Worker: .env → WORKER_CPUS, WORKER_MEMORY | Đủ tài nguyên VM rồi tạo lại worker |
| Luồng tạo ảnh | Worker: worker-settings.json → threads | Nên khớp CPU được cấp; tạo lại worker |
| Model được phép | Server: .credentials/workers.json → allowed_models | Tạo lại api/scheduler để nạp file JSON mới |
| IP/cổng web hoặc API worker | Server: .env → các dòng BIND/PORT | `up -d`; cập nhật Tunnel/worker nếu địa chỉ đích đổi |

Đọc thao tác và ví dụ cụ thể trong [hướng dẫn server, phần 14](HUONG-DAN-SERVER-MAY-MOI.md)
và phần **Sửa cấu hình worker** trong [hướng dẫn worker](HUONG-DAN-WORKER-MAY-MOI.md).
Không phải pull lại image chỉ vì đổi cấu hình. Kiểm tra JSON và Compose trước khi tạo lại container.

Ví dụ trên **worker** sau khi sửa file:

```bash
cd ~/neon-worker
python3 -m json.tool worker-settings.json >/dev/null
sudo docker compose config --quiet
sudo docker compose up -d --force-recreate worker
```

Ví dụ trên **server** sau khi sửa danh sách ID/model:

```bash
cd ~/neon-server
python3 -m json.tool .credentials/workers.json >/dev/null
sudo docker compose config --quiet
sudo docker compose up -d --force-recreate api scheduler
```

Nếu kiểm tra cú pháp lỗi, dừng ở đó và sửa trước. API có thể gián đoạn ngắn khi tạo lại;
worker còn trạng thái để thử kết nối/khôi phục. Ưu tiên cập nhật lúc không có yêu cầu đang chạy.

## 6. Git pull khác Docker pull

GitHub chứa **mã nguồn, Dockerfile, hướng dẫn và model Git LFS**.
Docker Hub chứa **image đã build**, có code/Python/thư viện; model nằm ngoài image hiện tại.
Máy chỉ chạy image phát hành không cần clone repository để vận hành.

Nếu bạn đã clone repository và chỉ muốn lấy tài liệu/code mới, chạy trong **thư mục clone**:

```bash
cd ~/neon-image-hub
git status --short
GIT_LFS_SKIP_SMUDGE=1 git pull --ff-only
```

Đường dẫn `~/neon-image-hub` là ví dụ thư mục clone; không phải ~/neon-server hoặc ~/neon-worker do setup tạo.
Trên máy phát triển WSL, repo có thể ở `/mnt/d/neon-image-hub`.
Nếu có sửa cục bộ, lưu các thay đổi đó trước khi pull; không dùng reset/clean để xóa cấu hình/dữ liệu.
Nếu Git báo nhánh phân kỳ, xử lý thay đổi Git trước, không ép ghi đè.
Biến GIT_LFS_SKIP_SMUDGE tránh tải model dung lượng lớn khi chỉ cập nhật tài liệu.
Repo riêng tư yêu cầu tài khoản GitHub đã được cấp quyền; không gửi mật khẩu/token vào chat.

Khi thật sự cần tải model từ Git LFS, chọn đúng nhóm file:

```bash
# SD-Turbo cho 2.1/4.1 (hoặc worker đã chọn SD-Turbo)
git lfs pull --include="models/sd_turbo-f16-q8_0.gguf,models/taesd.safetensors"
```

```bash
# DreamShaper8 LCM cho 3.1 (hoặc worker đã chọn DreamShaper)
git lfs pull --include="models/DreamShaper8_LCM.safetensors,models/taesd.safetensors"
```

Đối với VM mới, tải model trực tiếp bằng curl trong hướng dẫn worker thường đơn giản hơn.
Git pull không tự cập nhật chương trình đã đóng trong image đang chạy.
Muốn tự sửa code rồi dùng phiên bản đó, cần build image mới và cấu hình bộ triển khai dùng image mới;
muốn các VM khác pull thì phải push image mới lên Hub. Chỉ sửa tài liệu thì không cần build/push image.
Sửa file code trực tiếp bên trong container sẽ bị mất khi container được thay mới; sửa ở mã nguồn rồi build.

## 7. Kiểm tra sau khi cập nhật và khi gặp lỗi

Server: API healthy, website mở được, ảnh/CSDL còn nguyên, các ID có trạng thái đúng trong `/api/stats`.
Worker: không lặp HTTP 403, có nhận việc khi server có việc, cuối cùng có dòng **Saved by server**.
Model in ra trong log phải khớp AI_MODEL đã chọn. Nếu vừa cập nhật web, tải lại trang bằng Ctrl+F5.

```bash
# Trên server
cd ~/neon-server
sudo docker compose ps -a
sudo docker compose logs --tail 80 api scheduler web
```

```bash
# Trên worker
cd ~/neon-worker
sudo docker compose ps -a
sudo docker compose logs --tail 80 worker
```

Không suy ra tạo ảnh thành công chỉ từ dòng Worker ready. Lỗi inference chi tiết nằm trong worker-state/<job_id>.log.
Không xóa data, models hoặc worker-state để sửa lỗi cập nhật. Giữ backup và ghi lại tag/digest trước khi nâng cấp.
Nếu cần quay về bản image trước, dùng tag đã chạy ổn cùng cấu hình triển khai tương ứng;
việc hạ phiên bản phải phù hợp ghi chú tương thích dữ liệu của bản phát hành, không tự khôi phục DB cũ đè lên kho mới.

Thông số tài nguyên/phong cách tạo ảnh và tính năng giao diện chỉ đổi khi có thay đổi chương trình hoặc cấu hình tương ứng.
Trang quản trị hàng đợi, vị trí chờ, nút hủy và giới hạn một yêu cầu mỗi người vẫn là tính năng đang bàn,
chưa được triển khai bởi lần cập nhật tài liệu này.

# Cài worker — bản 1.2.0, không token

Mỗi thành viên làm trên **VM Ubuntu của mình**. Hướng dẫn này dùng tài khoản **root**, giống máy nhóm đang dùng.
Nếu dùng tài khoản thường, thêm `sudo` trước lệnh `docker`, `apt`, `systemctl` và lệnh chạy trình cài.
Lưu nano: **Ctrl+O → Enter → Ctrl+X**. Trong tài liệu, sửa đúng dòng cần đổi và giữ các dòng khác.

| Bạn đang làm gì? | Làm phần nào? |
|---|---|
| VM chưa cài worker | Bước 1 đến 4; cài Docker/Tailscale ở cuối nếu còn thiếu |
| Bật/tắt hằng ngày | Bước 5, dùng `up -d` để bật và `stop` để tắt |
| Đổi ID, IP server, model, CPU, RAM hoặc threads | Phần **Sửa cấu hình worker** |
| Tải lại image / nâng cấp | Phần **Cập nhật worker đã cài** |
| Worker lỗi tạo ảnh | Phần **Xem trạng thái và log** |

Mọi lệnh Docker phải chạy trong thư mục chứa **compose.yaml của đúng worker**.
Không chạy script `start-worker.ps1` của máy phát triển để nối worker vào server VM:
script đó bật thêm server local để thử nghiệm. VM thành viên làm theo tài liệu này.

## 1. Chuẩn bị

- VM Ubuntu 22.04 x86_64. Cấu hình khởi điểm: 4 vCPU, 8 GB RAM.
- Docker/Compose đã cài; Tailscale đã vào cùng mạng của nhóm. Nếu chưa có, làm phần **Cài công cụ** ở cuối tài liệu trước.
- Server đã chạy bản **1.2.0**.
- Server của nhóm dùng IP Tailscale **`100.127.223.79`**, cổng API **`8081`**.
- Mỗi VM phải có IP Tailscale riêng; VM clone không được dùng chung danh tính với VM gốc.

| Thành viên | ID phải dùng | Model mặc định |
|---|---|---|
| 2 | `2.1` | SD-Turbo |
| 3 | `3.1` | DreamShaper8 LCM |
| 4 | `4.1` | SD-Turbo |

Không cần token, không nhận ZIP dự án, không cài thư viện AI trên VM.
Nếu đã có `~/neon-worker/compose.yaml`, không khởi tạo lại. Xem phần **Cập nhật worker đã cài**.
Kiểm tra tài nguyên VM bằng `nproc` và `free -h`. VM 2 vCPU dùng tối đa 2 CPU cho worker;
khởi điểm 4 vCPU/8 GB RAM phù hợp hơn cho model 512 × 512. Thêm CPU phải cấp trong VMware trước.

## 2. Tạo worker lần đầu

Chạy trong **terminal VM worker**:

```bash
mkdir -p ~/neon-worker
cd ~/neon-worker
docker pull bachcp10/neon-hub-worker:1.2.0
```

Trong khối lệnh tiếp theo, **chỉ sửa `WORKER_ID`** theo bảng trên. `SERVER_IP` đã điền sẵn IP của server nhóm.

```bash
WORKER_ID=2.1
SERVER_IP=100.127.223.79
NEON_CPUS=$(nproc)
if [ "$NEON_CPUS" -gt 4 ]; then NEON_CPUS=4; fi

docker run --rm --network none \
  --user "$(id -u):$(id -g)" \
  -v "$PWD:/setup" --entrypoint python3 \
  bachcp10/neon-hub-worker:1.2.0 \
  -m setupkit worker --worker-id "$WORKER_ID" \
  --server-url "http://${SERVER_IP}:8081" --cpus "$NEON_CPUS"
```

Lệnh tự tạo các file sau, không hỏi token:

```text
~/neon-worker/
├── compose.yaml
├── .env
├── worker-settings.json
├── models/
└── worker-state/
```

Chỉ làm bước khởi tạo này **một lần** trong thư mục trống. Không chạy lại để bật worker hằng ngày.
Python trong câu lệnh chạy bên trong image Docker.
Lệnh tự chọn tối đa 4 CPU, không vượt số CPU Ubuntu nhìn thấy, và đặt `threads` tương ứng.
RAM container ban đầu là `5g`; VM nên có 8 GB RAM. Nếu tài nguyên khác, sửa theo phần cấu hình trước khi bật.
Model mặc định: `3.1` chọn DreamShaper8 LCM, `2.1`/`4.1` chọn SD-Turbo.

## 3. Tải model trực tiếp bằng curl

Chạy các lệnh dưới đây trong **terminal Ubuntu VM worker**, không chạy trên Windows.
Không cần nhận file model qua WinSCP, không cần clone GitHub hoặc cài Git LFS.

| Worker | Model mặc định | File cần tải |
|---|---|---|
| `2.1` và `4.1` | SD-Turbo | `sd_turbo-f16-q8_0.gguf` + `taesd.safetensors` |
| `3.1` | DreamShaper8 LCM | `DreamShaper8_LCM.safetensors` + `taesd.safetensors` |

**Tất cả worker:** vào thư mục model và tải TAESD dùng chung:

```bash
mkdir -p ~/neon-worker/models
cd ~/neon-worker/models

curl -fL -C - --retry 3 -o taesd.safetensors \
"https://huggingface.co/madebyollin/taesd/resolve/614f76814bbe30edbe2e627ace1c2234c81a2c0e/diffusion_pytorch_model.safetensors"
```

Tên gốc trên nguồn tải là `diffusion_pytorch_model.safetensors`; lệnh lưu thành
`taesd.safetensors`, đúng tên mà worker cần. Không đổi tên sau khi tải.

**Worker `2.1` và `4.1`:** tải thêm SD-Turbo, khoảng 2 GB:

```bash
cd ~/neon-worker/models

curl -fL -C - --retry 3 -o sd_turbo-f16-q8_0.gguf \
"https://huggingface.co/Green-Sky/SD-Turbo-GGUF/resolve/19a31586d02d64a73b4419bc193b3ecfaf38e1f0/sd_turbo-f16-q8_0.gguf"
```

**Worker `3.1`:** tải thêm DreamShaper8 LCM, khoảng 2,13 GB:

```bash
cd ~/neon-worker/models

curl -fL -C - --retry 3 -o DreamShaper8_LCM.safetensors \
"https://huggingface.co/Lykon/dreamshaper-8-lcm/resolve/4645d8bc6a8e6b106d21606d63e8460cdad4f1a6/DreamShaper8_LCM.safetensors"
```

Chỉ tải **TAESD và một model đã chọn**, không bắt buộc tải cả ba file.
Nếu đổi model sau này, tải thêm file tương ứng và đổi `AI_MODEL` trong `.env`.
Nếu bị ngắt mạng, chạy lại đúng lệnh để tải tiếp phần còn thiếu (`-C -`).
Chờ tải xong hoàn toàn, không có lỗi curl, rồi mới bật worker. Nếu file đã tải đủ thì bỏ qua lệnh đó.

Kiểm tra và trở về thư mục chạy Docker:

```bash
cd ~/neon-worker
ls -lh models/
```

TAESD khoảng 9,8 MB; cần thêm model chính khoảng 2 GB theo bảng trên.
Giữ đúng tên file và chữ hoa/thường, không đặt lồng `models/models/`.
Chỉ cần tải một lần; các lần bật worker sau không tải lại.
Image Docker chứa chương trình chạy AI; những lệnh curl này tải riêng dữ liệu model vào VM.

## 4. Chạy worker

Sau khi đã có model, trên **VM worker**:

```bash
cd ~/neon-worker
docker compose up -d
docker compose logs --tail 30 worker
```

Chạy các lệnh sau để kiểm tra kết nối đến server của nhóm.

```bash
curl -f http://100.127.223.79:8081/api/health
curl -fsS http://100.127.223.79:8081/api/stats
```

Health cần có `"status":"ok"`. Trong JSON stats, đúng ID của bạn phải có `"status":"idle"`
hoặc `"status":"busy"`; giao diện kho ảnh hiện chưa có bảng quản trị worker đầy đủ.
Có việc thì worker tự nhận, tạo ảnh và gửi về server. Không phải bấm tạo thủ công ở worker.
Nếu báo thiếu model: kiểm tra bước 3. Nếu bị từ chối: kiểm tra đúng ID, model và server đã lên 1.2.0.
Không chạy hai VM/container dùng cùng ID.

## 5. Bật/tắt những lần sau

Luôn vào đúng thư mục trước:

```bash
cd ~/neon-worker
```

Dừng:

```bash
docker compose stop
```

Bật lại, dùng thống nhất lệnh này để tạo container còn thiếu hoặc bật container đã dừng:

```bash
docker compose up -d
```

`docker compose start` cũng dùng được khi container đã được tạo và cấu hình không đổi.
`up -d` không tạo trùng container trong cùng dự án Compose; cấu hình không đổi thì giữ nguyên container.

Xem trạng thái hoặc log khi cần:

```bash
docker compose ps
docker compose logs --tail 30 worker
```

Không pull lại, không setup lại, không tải lại model mỗi lần bật.
Nếu đã dùng `docker compose down` thì bật lại bằng `docker compose up -d`.

## Sửa cấu hình worker

Các file dưới đây nằm tại **~/neon-worker trên VM worker**, bên ngoài container.
Pull image không ghi đè chúng. Không sửa file code bên trong container để cấu hình.

| Muốn đổi | Sửa ở đâu? | Ví dụ |
|---|---|---|
| ID worker | `worker-settings.json`: `worker_id` | `"2.1"`, `"2.2"`, `"1.1"` |
| Địa chỉ server | `worker-settings.json`: `server_url` | `"http://100.127.223.79:8081"` |
| Model | `.env`: `AI_MODEL` | `sd-turbo` hoặc `dreamshaper-8-lcm` |
| Giới hạn CPU | `.env`: `WORKER_CPUS` | `2`, `4`, `8` |
| Số luồng tạo ảnh | `worker-settings.json`: `threads` | Số nguyên như `2`, `4`, `8` |
| Giới hạn RAM | `.env`: `WORKER_MEMORY` | `5g` nghĩa là tối đa 5 GiB cho container |
| Nơi chứa model | `.env`: `MODEL_DIRECTORY` nếu cần đổi | Mặc định `./models`; WSL có thể dùng `/mnt/d/neon-image-hub/models` |

**A. Đổi model:** mở `.env`, sửa đúng một dòng `AI_MODEL`:

```bash
cd ~/neon-worker
nano .env
```

```dotenv
AI_MODEL=sd-turbo
```

Hoặc đổi thành `AI_MODEL=dreamshaper-8-lcm`. Model mới phải có file chính và TAESD trong models/;
tải bằng lệnh curl ở bước 3. Không phải sửa steps/sampler hoặc thay toàn bộ JSON.
Model phải thuộc `allowed_models` của ID đó trên server.

**B. Đổi CPU, RAM, threads:** kiểm tra tài nguyên thực mà Ubuntu được cấp:

```bash
nproc
free -h
nano .env
```

Ví dụ **VM 4 vCPU/8 GB RAM**, giữ hoặc đặt hai dòng sau trong `.env`:

```dotenv
WORKER_CPUS=4
WORKER_MEMORY=5g
```

Mở tiếp file JSON:

```bash
nano worker-settings.json
```

Sửa trường `threads` thành `4`; giữ nguyên các trường khác. Ví dụ riêng trường này:

```json
{"threads": 4}
```

Không thay toàn bộ nội dung file bằng ví dụ một trường ở trên.
VM 2 CPU: đặt `WORKER_CPUS=2` và `threads` bằng `2`. VM đã được cấp 8 CPU:
có thể đặt cả hai bằng `8`. Cần tắt VM, tăng tài nguyên trong VMware rồi bật VM trước.
CPU là giới hạn xử lý, threads là số luồng AI sử dụng; nên đặt bằng nhau trong cấu hình bài này.
`WORKER_MEMORY` không tự tăng RAM VM; để thấp hơn RAM VM và chừa RAM cho Ubuntu/agent.
Nhiều container trên cùng máy phải chia tổng tài nguyên. Tăng CPU không bảo đảm tốc độ tăng theo cùng tỷ lệ.

**C. Đổi ID hoặc địa chỉ server:** mở `worker-settings.json`, sửa đúng trường `worker_id`
hoặc `server_url`. ID có dạng `thành_viên.tiến_trình`, ví dụ `2.2`; mỗi container đang chạy có ID riêng.
Server phải đăng ký ID đó trong `.credentials/workers.json`. Xem phần thêm worker trong hướng dẫn server.
IP trong `server_url` là IP **của server**, không phải IP worker; dùng cổng `8081`.

**D. Áp dụng sau khi sửa bất kỳ cấu hình nào:** ưu tiên chờ ảnh đang tạo hoàn tất trước.

```bash
cd ~/neon-worker
python3 -m json.tool worker-settings.json >/dev/null
docker compose config --quiet
docker compose up -d --force-recreate worker
docker compose logs --tail 30 worker
```

Nếu bước kiểm tra JSON hoặc Compose báo lỗi thì sửa cú pháp trước, chưa chạy lệnh tạo lại container.
`--force-recreate` bảo đảm file JSON bind mount mới được dùng kể cả khi trình soạn thảo thay file bằng một file mới.
Chỉ `start`/`restart` không cập nhật môi trường `.env` như việc tạo lại container.
Giữ `worker-state/` để worker khôi phục công việc khi cần; giữ thư mục models/.

## Cập nhật worker đã cài

**Chỉ tải lại chương trình của tag đang ghi trong compose.yaml:**

```bash
cd ~/neon-worker
docker compose pull worker
docker compose up -d worker
docker compose ps -a
docker compose logs --tail 30 worker
```

`pull` tải image nhưng chưa thay container đang chạy; `up -d` mới áp dụng image mới nếu có.
Nếu tag chưa có thay đổi, lệnh giữ bản hiện có. ID, IP, model, CPU/RAM, model trên đĩa và worker-state giữ nguyên.
Không setup lại, không tải lại model, không sửa JSON chỉ vì pull image.

**Nâng từ bản 1.0/1.1 lên bản 1.2.0:** cập nhật server trước, rồi trên VM worker:

```bash
cd ~/neon-worker
docker compose stop worker
NEON_BACKUP="$HOME/neon-worker-before-update-$(date +%Y%m%d-%H%M%S).tar.gz"
tar -czf "$NEON_BACKUP" compose.yaml .env worker-settings.json worker-state
docker pull bachcp10/neon-hub-worker:1.2.0
docker run --rm --network none \
  --user "$(id -u):$(id -g)" \
  -v "$PWD:/setup" --entrypoint python3 \
  bachcp10/neon-hub-worker:1.2.0 -m setupkit upgrade
docker compose pull worker
docker compose up -d --force-recreate worker
docker compose logs --tail 30 worker
```

Ưu tiên để ảnh đang tạo hoàn tất trước khi dừng. File backup chứa cấu hình và trạng thái, không chứa model 2 GB.
Công cụ upgrade giữ ID, IP, lựa chọn model, CPU/RAM; bỏ trường token worker cũ và đổi image sang 1.2.0.
Nếu thay sang một tag phiên bản mới khác, chỉ dùng tag đã phát hành và làm theo ghi chú phát hành.
Xem [hướng dẫn cập nhật đầy đủ](README.md) để phân biệt Docker pull và Git pull.

## Thêm ID khác hoặc chạy hai worker trên một máy

Công cụ setup 1.2.0 chỉ nhận `2.1`, `3.1`, `4.1` ở dòng `--worker-id`.
Để thêm `2.2` hoặc `1.1`, tạo cấu hình trong **thư mục mới trống** bằng một ID có sẵn,
sau đó sửa `worker_id` trong JSON thành ID mới **trước khi bật container**. Đăng ký ID mới trên server.
Model vẫn chọn bằng `.env`, không cần tạo image khác.

Nếu cùng một VM chạy thêm worker, dùng thư mục cấu hình và worker-state riêng, chia CPU/RAM, rồi đặt tên dự án Compose khác:

```bash
cd ~/neon-worker-2.2
docker compose -p neon-worker-2-2 up -d
```

Các lần stop, logs, pull, up của worker này đều giữ cùng `-p neon-worker-2-2`.
Hai bộ có thể dùng chung thư mục model qua `MODEL_DIRECTORY` mount chỉ đọc.
Không dùng `--scale worker=2` với cùng một file ID/state cho cả hai container.

## Xem trạng thái và log

```bash
cd ~/neon-worker
docker compose ps -a
docker compose logs --tail 60 worker
```

`Worker ready` mới xác nhận chương trình khởi động; phải không bị 403 và có heartbeat trên server mới kết nối thành công.
`Generating` là bắt đầu xử lý; `Image generated` là đã tạo ảnh; `Saved by server` xác nhận ảnh đã lưu vào kho.
Chỉ số bước như `1/6` nằm trong log từng công việc:

```bash
cd ~/neon-worker
LOG_FILE=$(ls -t worker-state/*.log 2>/dev/null | head -n 1)
if [ -n "$LOG_FILE" ]; then tail -n 80 "$LOG_FILE"; else echo 'Chua co log tao anh.'; fi
```

Muốn theo dõi tiếp file đó: `tail -f "$LOG_FILE"`. Ctrl+C chỉ dừng xem log.
Khi chỉ thấy `RuntimeError`, lấy log từng việc trên để tìm nguyên nhân; không suy ra ngay là lỗi model.

| Hiện tượng | Cách kiểm tra |
|---|---|
| Docker báo chỉ có 2 CPU | `.env` không được yêu cầu 4/8 khi `nproc` chỉ ra 2; sửa thêm threads cho phù hợp |
| HTTP 403, container restarting | Đúng ID, đúng server, ID đã đăng ký, model thuộc allowed_models |
| Missing model / không nạp được model | Đúng tên, đường dẫn, file tải xong; không phải pointer Git LFS vài trăm byte |
| Thiếu RAM / OOM / tạo lỗi sau nạp model | `free -h`, `docker stats --no-stream`, giới hạn WORKER_MEMORY và log từng job |
| Bật worker nhưng chưa ai tìm mà đã có việc | Sinh ảnh nền mặc định đang bật trên server |
| Tìm ảnh nhưng còn chờ | Worker đang làm ảnh trước đó; tìm kiếm ưu tiên hơn việc nền tiếp theo, chưa ngắt việc đang chạy |

## Worker trong WSL trên máy phát triển

WSL **Ubuntu-22.04** có thể đọc ổ D qua `/mnt/d`. Thư mục hiện dùng cho worker `1.1` trên máy phát triển:

```text
Windows: D:\neon-image-hub\data\worker-1.1
WSL:     /mnt/d/neon-image-hub/data/worker-1.1
```

Trong terminal Ubuntu WSL:

```bash
cd /mnt/d/neon-image-hub/data/worker-1.1
docker compose up -d
docker compose logs --tail 30 worker
```

Đây là cấu hình riêng đã tạo trên máy phát triển, không có trong bản clone GitHub mới.
Docker/worker chạy trong Linux WSL, code ở `/app/worker` trong container; ổ D chỉ giữ cấu hình/model/state.
Thư mục chạy không quyết định ID. Server vẫn ở VM riêng và được chỉ định trong `server_url`.
Với máy khác, tự khởi tạo theo các bước đầu và dùng đường dẫn thực của máy đó.

## Cài công cụ — chỉ làm nếu VM chưa có Docker/Tailscale

Các lệnh dưới đây chạy trong **Ubuntu VM bằng root**.

```bash
apt update
apt install -y ca-certificates curl nano python3
curl -fsSL https://get.docker.com -o /tmp/neon-docker-install.sh
sh /tmp/neon-docker-install.sh
systemctl enable --now docker
docker --version
docker compose version
```

Cài Tailscale:

```bash
curl -fsSL https://tailscale.com/install.sh -o /tmp/neon-tailscale-install.sh
sh /tmp/neon-tailscale-install.sh
```

Nếu VM chưa vào tailnet của nhóm, chạy khối lệnh sau. Khi terminal hỏi, dán auth key do quản trị viên cấp riêng rồi nhấn Enter. Key được nhập ẩn.

```bash
(
  IFS= read -rsp 'Dán auth key Tailscale rồi nhấn Enter: ' NEON_TAILSCALE_AUTH_KEY || exit 1
  printf '\n'
  [ -n "$NEON_TAILSCALE_AUTH_KEY" ] || exit 1
  printf '%s' "$NEON_TAILSCALE_AUTH_KEY" | sudo tailscale up --auth-key=file:/dev/stdin
)
```

Nếu VM đã vào đúng tailnet của nhóm, bỏ qua bước đăng nhập.

Sau khi kết nối, kiểm tra bằng các lệnh sau.

```bash
tailscale ip -4
tailscale status
```

Nếu đã cài Docker hoặc Tailscale, bỏ qua lệnh cài tương ứng.
Nguồn: [Docker](https://docs.docker.com/engine/install/ubuntu/#install-using-the-convenience-script), [Cài Tailscale](https://tailscale.com/docs/install/linux), [nhập auth key Tailscale](https://tailscale.com/docs/features/access-control/auth-keys/how-to/secure-auth-keys).

## Giám sát VM

Worker AI và agent Beszel là hai chương trình khác nhau. Sau khi worker chạy được,
người giữ server cấp cấu hình agent để theo dõi VM của bạn.
Xem phần **Cài agent Beszel** trong tài liệu [worker chi tiết](HUONG-DAN-WORKER-CHI-TIET.md).
Chỉ máy server cần Cloudflare Tunnel; VM worker không cần cài Tunnel.

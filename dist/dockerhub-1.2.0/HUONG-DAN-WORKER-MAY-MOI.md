# Cài worker — bản 1.2.0, không token

Mỗi thành viên làm trên **VM Ubuntu của mình**. Hướng dẫn này dùng tài khoản **root**, giống máy nhóm đang dùng.
Nếu dùng tài khoản thường, thêm `sudo` trước lệnh `docker`, `apt`, `systemctl` và lệnh chạy trình cài.

## 1. Chuẩn bị

- VM Ubuntu 22.04 x86_64. Cấu hình khởi điểm: 4 vCPU, 8 GB RAM.
- Docker/Compose đã cài; Tailscale đã vào cùng mạng của nhóm. Nếu chưa có, làm phần **Cài công cụ** ở cuối tài liệu trước.
- Server đã chạy bản **1.2.0**.
- Hỏi người giữ server **IP Tailscale của server**. Không lấy IP của chính worker.
- Mỗi VM phải có IP Tailscale riêng; VM clone không được dùng chung danh tính với VM gốc.

| Thành viên | ID phải dùng | Model mặc định |
|---|---|---|
| 2 | `2.1` | SD-Turbo |
| 3 | `3.1` | DreamShaper8 LCM |
| 4 | `4.1` | SD-Turbo |

Không cần token, không nhận ZIP dự án, không cài thư viện AI trên VM.
Nếu đã có `~/neon-worker/compose.yaml` từ bản cũ thì bỏ qua bước 2, dùng phần **Nâng cấp** ở cuối.

## 2. Tạo worker lần đầu

Chạy trong **terminal VM worker**:

```bash
mkdir -p ~/neon-worker
cd ~/neon-worker
docker pull bachcp10/neon-hub-worker:1.2.0
```

Trong khối lệnh tiếp theo, **sửa đúng hai dòng đầu trước khi chạy**:

- `WORKER_ID`: ID của thành viên trong bảng trên.
- `SERVER_IP`: IP Tailscale thật mà người giữ server cung cấp. `100.101.102.10` dưới đây chỉ là ví dụ.

```bash
WORKER_ID=2.1
SERVER_IP=100.101.102.10
docker run --rm --network none \
  --user "$(id -u):$(id -g)" \
  -v "$PWD:/setup" --entrypoint python3 \
  bachcp10/neon-hub-worker:1.2.0 \
  -m setupkit worker --worker-id "$WORKER_ID" \
  --server-url "http://${SERVER_IP}:8081" --cpus 4
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

## 3. Chép model

Người giữ file model gửi cho các thành viên. File có sẵn trên máy phát triển tại:

```text
D:\codex-neon-local\models\
```

Dùng WinSCP chép file vào **VM worker**, thư mục:

```text
/root/neon-worker/models/
```

| Model chọn | File cần chép |
|---|---|
| SD-Turbo | `sd_turbo-f16-q8_0.gguf` và `taesd.safetensors` |
| DreamShaper8 LCM | `DreamShaper8_LCM.safetensors` và `taesd.safetensors` |

Có thể chép cả ba file để đổi model dễ hơn. Giữ nguyên tên file; đặt trực tiếp trong models/, không lồng thêm models/models/.
File model chỉ cần chép một lần. Đây là dữ liệu AI; code chương trình đã nằm trong image.

## 4. Chạy worker

Sau khi đã có model, trên **VM worker**:

```bash
cd ~/neon-worker
docker compose up -d
docker compose logs --tail 30 worker
```

Nhờ người giữ server xem đúng ID của bạn đã `idle` hoặc `busy` trên website.
Có việc thì worker tự nhận, tạo ảnh và gửi về server. Không phải bấm tạo thủ công ở worker.
Nếu báo thiếu model: kiểm tra bước 3. Nếu bị từ chối: kiểm tra đúng ID, model và server đã lên 1.2.0.
Không chạy hai VM/container dùng cùng ID.

## 5. Dùng những lần sau

Luôn vào đúng thư mục trước:

```bash
cd ~/neon-worker
```

Dừng:

```bash
docker compose stop
```

Bật lại:

```bash
docker compose start
```

Xem trạng thái hoặc log khi cần:

```bash
docker compose ps
docker compose logs --tail 30 worker
```

Không pull lại, không setup lại, không chép lại model mỗi lần bật.
Nếu đã dùng `docker compose down` thì bật lại bằng `docker compose up -d`.

## Đổi model khi cần

```bash
cd ~/neon-worker
nano .env
```

Chỉ đổi dòng AI_MODEL thành một trong hai lựa chọn:

```dotenv
AI_MODEL=sd-turbo
```

hoặc:

```dotenv
AI_MODEL=dreamshaper-8-lcm
```

Lưu file rồi chạy:

```bash
docker compose up -d
```

Không sửa cả JSON. Model được chọn phải có file tương ứng trong models/.

## Nâng cấp worker đã cài bản cũ

Chỉ làm khi máy đã có compose.yaml và cấu hình worker; server cần lên 1.2.0 trước.

```bash
cd ~/neon-worker
docker pull bachcp10/neon-hub-worker:1.2.0
docker run --rm --network none \
  --user "$(id -u):$(id -g)" \
  -v "$PWD:/setup" --entrypoint python3 \
  bachcp10/neon-hub-worker:1.2.0 -m setupkit upgrade
docker compose pull
docker compose up -d
```

Giữ ID, địa chỉ server, model và trạng thái công việc. Không chạy setup lần đầu trong thư mục đã có dữ liệu.
Nếu trước đây dùng thư mục khác thì cd tới đúng thư mục chứa compose.yaml của worker đó.

## Cài công cụ — chỉ làm nếu VM chưa có Docker/Tailscale

Các lệnh dưới đây chạy trong **Ubuntu VM bằng root**.

```bash
apt update
apt install -y ca-certificates curl
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
tailscale up
```

Mở URL đăng nhập được in ra và đưa VM vào cùng tailnet của nhóm. Kiểm tra:

```bash
tailscale ip -4
tailscale status
```

Nếu Docker/Tailscale đã có thì bỏ qua phần cài, không cài đè.
Nguồn: [Docker](https://docs.docker.com/engine/install/ubuntu/#install-using-the-convenience-script), [Tailscale](https://tailscale.com/docs/install/linux).

## Giám sát VM

Worker AI và agent Beszel là hai chương trình khác nhau. Sau khi worker chạy được,
người giữ server cấp cấu hình agent để theo dõi VM của bạn.
Xem phần **Cài agent Beszel** trong tài liệu [worker chi tiết](HUONG-DAN-WORKER-CHI-TIET.md).
Chỉ máy server cần Cloudflare Tunnel; VM worker không cần cài Tunnel.

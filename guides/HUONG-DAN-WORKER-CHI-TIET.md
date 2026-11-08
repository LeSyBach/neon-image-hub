# Hướng dẫn máy mới — WORKER Neon Image Hub

> Môi trường nhóm đang dùng: **Ubuntu 22.04.5 LTS (Jammy), x86_64**. Dùng được với image 1.2.0; không cần cài lại VM. Nếu VM đã có sẵn, bỏ qua phần tạo VM và bắt đầu kiểm tra Docker/Tailscale.
> Trong ảnh bạn đang đăng nhập root: dấu nhắc thường kết thúc bằng # và ~ là /root. Với tài khoản thường như ubuntu, ~ thường là /home/ubuntu. Các lệnh dùng ~/neon-server hoặc ~/neon-worker đều đi theo home của tài khoản đang chạy; giữ cùng tài khoản trong các bước.

Dành chung cho thành viên 2, 3 và 4. Tất cả dùng image **bachcp10/neon-hub-worker:1.2.0**.
Chỉ cấu hình ID và lựa chọn model khác nhau. Máy chủ cần chạy và cấp ID
trước khi bạn thực hiện bước 4. Trong ví dụ tên VM dùng neon-worker-2; thành viên 3/4
đặt neon-worker-3 hoặc neon-worker-4. Mỗi thành viên làm toàn bộ tài liệu trên VM của mình.
Các giá trị có chữ IP_... hoặc DUONG-DAN-THAT là chỗ cần thay, không phải địa chỉ có thật.

Muốn thao tác gọn từng bước, đọc [hướng dẫn worker chính](HUONG-DAN-WORKER-MAY-MOI.md).
Tài liệu chính đã có bảng sửa ID/IP/model/CPU/RAM/threads, tải curl, bật/tắt, pull image và worker WSL.
Tài liệu này giải thích thêm VM, mạng, agent Beszel và xử lý lỗi. Không cài lại cả hai lần.

## 1. Kiểm tra VM hiện có hoặc tạo VM Ubuntu mới

Thực hiện trên máy Windows của thành viên phụ trách.

1. Tải Ubuntu Server 22.04 LTS (nhóm đang dùng 22.04.5) bản **AMD64 / x86-64** tại [Ubuntu](https://releases.ubuntu.com/22.04/), chọn **server install image**.
2. Trong VMware, tạo máy ảo mới, chọn file ISO vừa tải và loại hệ điều hành Ubuntu 64-bit.
3. Đặt tên VM **neon-worker-2**. Cấp 4 vCPU, 8 GB RAM, ổ đĩa ảo 40 GB. Đây là cấu hình khởi điểm của dự án; tốc độ thực tế cần đo lại trên máy của nhóm.
4. Chọn mạng **NAT** để VM ra Internet. Tailscale sẽ được cài bên trong VM.
5. Khởi động VM, cài Ubuntu Server; dùng ổ đĩa ảo vừa tạo. Chọn tên người dùng **ubuntu** cho thống nhất với ví dụ trong tài liệu, tự đặt mật khẩu.
6. Chọn cài **OpenSSH Server** nếu trình cài hỏi. Hoàn tất, khởi động lại VM và tháo ISO nếu VMware yêu cầu.
7. Đăng nhập Ubuntu. Tất cả lệnh có nhãn **Ubuntu VM** trong hướng dẫn phải chạy ở terminal bên trong VM này.

Kiểm tra trong **Ubuntu VM**:

```bash
uname -m
cat /etc/os-release
```

Kết quả kiến trúc cần là `x86_64`; Ubuntu là bản 22.04 (22.04.5 trong ảnh). Ubuntu 24.04 cũng tương thích nếu thành viên khác đã cài sẵn. Image dự án hiện chỉ phát hành `linux/amd64`.
Nếu tạo nhiều VM, cài mới từng VM hoặc bảo đảm bản sao có danh tính Tailscale riêng.

## 2. Cài Docker, Compose và công cụ cơ bản

Chạy trên **Ubuntu VM mới**. Lệnh sudo hỏi mật khẩu Ubuntu vừa đặt; khi gõ có thể không hiện ký tự.

Nếu đăng nhập root và máy chưa có sudo, chạy đoạn này một lần để dùng nguyên các lệnh bên dưới:

```bash
if [ "$(id -u)" -eq 0 ] && ! command -v sudo >/dev/null 2>&1; then
  apt update
  apt install -y sudo
fi
```

```bash
sudo apt update
sudo apt install -y ca-certificates curl python3 unzip nano openssh-server
curl -fsSL https://get.docker.com -o /tmp/neon-install-docker.sh
sudo sh /tmp/neon-install-docker.sh
sudo systemctl enable --now docker
sudo systemctl enable --now ssh
sudo docker version
sudo docker compose version
```

Đây là trình cài chính thức của Docker, dùng ở đây cho các VM bài tập mới.
Nguồn: [Docker Engine trên Ubuntu](https://docs.docker.com/engine/install/ubuntu/#install-using-the-convenience-script).
Nếu VM đã có Docker thì kiểm tra phiên bản, không chạy lại trình cài để nâng cấp.

Kết quả cần có cả Docker Client/Server và Docker Compose **v2.24 trở lên**.
Hướng dẫn dùng `sudo docker ...` xuyên suốt, không yêu cầu thêm tài khoản vào nhóm docker.
Python 3 trên VM phục vụ thao tác cấu hình; môi trường và thư viện chạy AI đã nằm trong image worker.

## 3. Cài Tailscale và lấy địa chỉ VM

Trong **Ubuntu VM**:

```bash
curl -fsSL https://tailscale.com/install.sh -o /tmp/neon-install-tailscale.sh
sudo sh /tmp/neon-install-tailscale.sh
sudo tailscale up
```

Mở URL đăng nhập mà lệnh hiển thị trên trình duyệt Windows. Đưa VM vào **cùng tailnet của nhóm**.
Nếu thành viên dùng tài khoản riêng, quản trị viên cần mời họ vào tailnet chung.
Không đăng nhập bốn tài khoản vào bốn tailnet tách biệt.
Nếu đăng nhập bằng auth key, dùng khóa mới được cấp riêng; không dùng lại khóa đã lộ trong chat.

Sau khi xác nhận, chạy trong **Ubuntu VM**:

```bash
tailscale status
tailscale ip -4
ip -br -4 address
```

- `tailscale ip -4`: IP riêng của VM, dùng cho kết nối giữa server và worker.
- `ip -br -4 address`: xem thêm địa chỉ mạng NAT của VM trên card như `ens33`, `ens160` hoặc `enp...`.
  IP NAT này dùng khi chép file từ Windows của chính thành viên vào VM bằng SSH/SCP.
- Không lấy địa chỉ `127.0.0.1` hay `docker0` làm IP server cho các worker khác.

Nguồn: [Cài Tailscale trên Linux](https://tailscale.com/docs/install/linux).

## 4. Nhận ID và địa chỉ server

Từ bản 1.2.0, không cần token worker, không cần ZIP cấu hình hoặc mã nguồn.
Quản trị server chỉ cung cấp ID (2.1, 3.1 hoặc 4.1) và địa chỉ API
http://IP-TAILSCALE-SERVER:8081. Server phải được cập nhật 1.2.0 trước.
Hai máy không dùng chung một ID. ID 3.1 mặc định DreamShaper; 2.1/4.1 mặc định SD-Turbo.

## 5. Tải image và tạo cấu hình trên VM worker

Trong **Ubuntu VM worker mới**, sau khi Docker và Tailscale đã hoạt động:

```bash
mkdir -p ~/neon-worker
cd ~/neon-worker
sudo docker pull bachcp10/neon-hub-worker:1.2.0
```

Đặt hai giá trị dưới đây đúng với máy bạn. Ví dụ ID 2.1; thành viên 3/4 thay thành 3.1/4.1.
Thay IP_TAILSCALE_SERVER bằng IP thật của server trước khi chạy:

```bash
WORKER_ID=2.1
SERVER_URL="http://IP_TAILSCALE_SERVER:8081"
NEON_CPUS=$(nproc)
if [ "$NEON_CPUS" -gt 4 ]; then NEON_CPUS=4; fi
sudo docker run --rm --network none \
  --user "$(id -u):$(id -g)" \
  -v "$PWD:/setup" --entrypoint python3 \
  bachcp10/neon-hub-worker:1.2.0 \
  -m setupkit worker --output /setup --worker-id "$WORKER_ID" \
  --server-url "$SERVER_URL" --cpus "$NEON_CPUS"
```

Không có yêu cầu nhập token.
Thư mục đích phải trống ở lần đầu; công cụ giữ nguyên và từ chối ghi đè cấu hình đã có.
Lệnh tạo compose.yaml, .env, worker-settings.json, models/ và worker-state/ ngay trên VM.
AI_MODEL tự chọn theo ID; threads và giới hạn CPU lấy số CPU VM, tối đa 4 trong lệnh mẫu.
WORKER_MEMORY đặt 5g cho VM khởi điểm 8 GB RAM. VM chỉ có 2 CPU thì không đặt WORKER_CPUS=4/8.
Nếu VM có tài nguyên khác, điều chỉnh như bước 7 trước khi chạy AI.

Kiểm tra trong **Ubuntu VM worker**:

```bash
cd ~/neon-worker
ls -la
```

Lệnh setup chỉ tạo cấu hình, chưa chạy worker AI. Bước tiếp theo là tải model vào models/.

## 6. Tải model AI trực tiếp bằng curl

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

Có thể đối chiếu SHA256 với `MODEL-SOURCES.json`. Chỉ chạy lệnh cho file đã tải:

```bash
sha256sum models/taesd.safetensors
# Worker 2.1/4.1:
sha256sum models/sd_turbo-f16-q8_0.gguf
# Worker 3.1:
sha256sum models/DreamShaper8_LCM.safetensors
```

## 7. Chọn model và tài nguyên

Trong **Ubuntu VM worker**:

```bash
cd ~/neon-worker
nano .env
```

Với VM 4 vCPU, 8 GB RAM, có thể đặt như sau cho **máy 2 và máy 4**:

```dotenv
AI_MODEL=sd-turbo
WORKER_CPUS=4
WORKER_MEMORY=5g
```

Riêng **máy 3**:

```dotenv
AI_MODEL=dreamshaper-8-lcm
WORKER_CPUS=4
WORKER_MEMORY=5g
```

Lưu nano bằng Ctrl+O, Enter; thoát Ctrl+X. Đây là giới hạn tài nguyên container, không phải số RAM tự cấp cho VM.
Không đặt WORKER_MEMORY lớn hơn RAM VM; chừa tài nguyên cho Ubuntu và agent giám sát.

Đặt số luồng tạo ảnh theo VM 4 vCPU mà không đụng ID:

```bash
python3 - <<'PY'
from pathlib import Path
import json
p=Path('worker-settings.json')
cfg=json.loads(p.read_text())
cfg['threads']=4
p.write_text(json.dumps(cfg,indent=2))
print('Da dat threads=4; giu nguyen ID/server_url.')
PY
```

Khi dùng số vCPU khác, đổi threads và WORKER_CPUS cho phù hợp.
Chọn model bằng AI_MODEL, không cần thay steps/sampler trong JSON.
Xem phần **Sửa cấu hình worker** trong [hướng dẫn chính](HUONG-DAN-WORKER-MAY-MOI.md)
để đổi ID, server_url, CPU, RAM, threads và kiểm tra cú pháp. Sau sửa JSON/.env, dùng
`sudo docker compose up -d --force-recreate worker` để nạp lại cấu hình; không chỉ dùng start/restart.

## 8. Kiểm tra server trước khi chạy AI

Trong **Ubuntu VM worker**:

```bash
cd ~/neon-worker
SERVER_URL="$(python3 -c "import json; print(json.load(open('worker-settings.json'))['server_url'])")"
printf '%s\n' "$SERVER_URL"
curl -f "${SERVER_URL}/api/health"
```

SERVER_URL cần có dạng `http://IP-TAILSCALE-THAT-CUA-SERVER:8081`; không còn CHANGE_SERVER_IP,
không dùng localhost hay IP của chính worker. Curl cần trả `"status":"ok"`.

Nếu không kết nối, kiểm tra `tailscale status`, cùng tailnet, server đang chạy và WORKER_BIND của server.
IP có thể kiểm tra bằng `tailscale ping IP-TAILSCALE-THAT-CUA-SERVER` sau khi thay IP thật.
Mạng và chính sách Tailscale cần cho phép kết nối worker tới server cổng 8081.
Không cần điền IP worker vào server để nhận việc.

## 9. Tải image worker và khởi chạy

Trong **Ubuntu VM worker**, tại ~/neon-worker:

```bash
sudo docker compose pull
sudo docker compose up -d
sudo docker compose ps
sudo docker compose logs --tail 50 worker
```

Compose tải **bachcp10/neon-hub-worker:1.2.0** và chạy chương trình trong container.
Không cần đăng nhập Docker Hub, không cần build, không cần pip install thư viện AI trên VM.
`pull` tải image; `up -d` mới tạo/chạy container.

Kết quả cần thấy worker ready, không lặp lỗi xác thực, có nhận job khi server có việc.
Worker ready chưa chứng minh server đã nhận: kiểm tra không có HTTP 403 và ID có heartbeat trên `/api/stats`.
`Saved by server` xác nhận ảnh được lưu; log bước như 1/6 ở `worker-state/<job_id>.log`.
Khi rảnh, worker xin việc; đang sinh ảnh vẫn gửi heartbeat; tạo xong gửi ảnh về server.
Lần đầu có thể nhận ngay việc sinh nền dù chưa ai tìm kiếm. Thời gian sinh ảnh phải đo trên VM thật.

Nếu muốn xem log liên tục:

```bash
sudo docker compose logs -f worker
```

Ctrl+C chỉ thoát màn hình xem log; container vẫn chạy.
Quản trị server xem JSON `/api/stats`: ID của máy bạn phải chuyển `idle`/`busy`, số ảnh tăng sau khi lưu thành công.
Giao diện kho ảnh hiện chưa có bảng quản trị hiển thị đầy đủ trạng thái tất cả worker/hàng đợi.

### Các file nằm ở đâu?

```text
VM worker: ~/neon-worker/
├── compose.yaml
├── .env
├── worker-settings.json
├── models/
└── worker-state/

Bên trong container:
├── /app/worker/       ← Code từ image
├── /opt/sd/           ← Công cụ AI từ image
├── /config/worker.json← Nối với worker-settings.json
├── /models/           ← Nối với models/ trên VM
└── /state/            ← Nối với worker-state/ trên VM
```

Ảnh tạm/log nằm ở worker-state; ảnh hoàn tất được lưu tại máy chủ, không coi ảnh tạm là kho ảnh chung.

## 10. Cài agent Beszel để được giám sát

Quản trị server cần mở Hub qua Tailscale, thêm System cho VM này và cung cấp KEY/TOKEN agent cùng HUB_URL.
Đây là khóa của agent giám sát; worker AI không dùng token.

Trong **Ubuntu VM worker**:

```bash
mkdir -p ~/neon-monitor
cd ~/neon-monitor
nano compose.yaml
```

Dán và lưu:

```yaml
name: neon-monitor
services:
  agent:
    image: henrygd/beszel-agent:0.21.1
    restart: unless-stopped
    network_mode: host
    env_file: agent.env
    volumes:
      - ./agent-data:/var/lib/beszel-agent
      - /var/run/docker.sock:/var/run/docker.sock:ro
```

Tạo cấu hình:

```bash
nano agent.env
```

Điền đúng giá trị được cấp:

```dotenv
KEY="DAN_PUBLIC_KEY_TU_HUB"
TOKEN="DAN_TOKEN_TU_HUB"
HUB_URL=http://IP_TAILSCALE_SERVER:8090
LISTEN=IP_TAILSCALE_CUA_VM_NAY:45876
```

Thay tất cả chữ minh họa. `LISTEN` dùng IP của VM worker này; `HUB_URL` dùng IP server.
KEY cần toàn bộ public key như ssh-ed25519 và phần ký tự phía sau.
Trong **Ubuntu VM worker**:

```bash
chmod 600 agent.env
sudo docker compose pull
sudo docker compose up -d
sudo docker compose logs --tail 30 agent
```

Nhờ quản trị kiểm tra Hub đã có CPU/RAM/đĩa của đúng VM này.
Server cần truy cập agent cổng 45876 qua Tailscale, hoặc agent kết nối Hub 8090 theo phương thức đã cấu hình.
Nguồn: [Beszel Agent](https://beszel.dev/guide/agent-installation), [LISTEN host:port](https://beszel.dev/guide/environment-variables).

## 11. Đổi model, bật/tắt và cập nhật

Đổi model: mở .env, chỉ đổi AI_MODEL sang một trong hai tên đã hỗ trợ; bảo đảm file tương ứng vẫn có trong models/.
Sau đó chạy trong **Ubuntu VM worker**:

```bash
cd ~/neon-worker
sudo docker compose up -d
```

Không dùng `docker compose restart` để áp dụng thay đổi .env: cần `up -d` để tạo lại container với môi trường mới.
Giữ cả hai model khi đổi nếu worker còn công việc cũ cần khôi phục.

Dừng worker:

```bash
cd ~/neon-worker
sudo docker compose stop worker
```

Chạy lại:

```bash
cd ~/neon-worker
sudo docker compose up -d
```

Chỉ ngừng nhận việc mới, để việc đang làm hoàn tất:

```bash
cd ~/neon-worker
mkdir -p worker-state
sudo touch worker-state/pause
```

Tiếp tục nhận việc:

```bash
cd ~/neon-worker
sudo rm -- worker-state/pause
```

Chỉ xóa đúng file marker pause khi muốn tiếp tục; không xóa pending.json hoặc cả worker-state để xử lý lỗi.
Agent giám sát chạy riêng trong ~/neon-monitor; dừng worker không dừng agent.

Bật hằng ngày có thể dùng `up -d`; start chỉ dùng khi container đã có và cấu hình không đổi.
Để tải lại image rồi áp dụng:

```bash
cd ~/neon-worker
sudo docker compose pull worker
sudo docker compose up -d worker
sudo docker compose ps -a
sudo docker compose logs --tail 30 worker
```

Ưu tiên đợi ảnh đang làm xong; giữ model và worker-state. `pull` không tự sửa ID/IP/model/CPU/RAM,
không tải lại trọng số AI, cũng không tự chạy image mới cho đến khi up.
Nâng từ 1.0/1.1 hoặc đổi tag mới: làm theo [hướng dẫn cập nhật](NANG-CAP-1.2.0-KHONG-TOKEN.md),
không chạy lại setup lần đầu trong thư mục đang dùng.

## 12. Xử lý lỗi thường gặp

| Lỗi | Cách xử lý |
|---|---|
| Không thấy .env | Dùng `ls -la`; kiểm tra lệnh setup image đã thành công tại đúng thư mục. |
| Không có worker-settings.json | Làm bước 5 bằng image 1.2.0; không cần token worker. |
| Curl server timeout | Kiểm tra Tailscale, IP server:8081, server đang chạy, bind và quyền mạng. |
| 401/403 | Kiểm tra đúng ID/model và server đã cập nhật 1.2.0. |
| Missing local model component | Đúng tên file, chữ hoa/thường, thư mục models/ và file đã tải đủ. |
| OOMKilled / exit 137 | Kiểm tra RAM VM, WORKER_MEMORY và model; gửi log cho người phụ trách, không tăng giới hạn vượt RAM VM. |
| Container báo thiếu CPU | Giảm WORKER_CPUS cho khớp vCPU VM; chỉnh threads tương ứng. |
| Đã đổi model nhưng vẫn dùng cũ | Chạy `up -d` sau sửa .env; việc cũ đang khôi phục có thể hoàn tất trước việc mới. |
| Offline ngay sau khi đóng logs -f | Ctrl+C không dừng container; dùng `sudo docker compose ps` và logs để tìm lý do thật. |

Kiểm tra nhanh khi cần hỗ trợ, trong **Ubuntu VM worker**:

```bash
cd ~/neon-worker
sudo docker compose ps
sudo docker compose logs --tail 80 worker
free -h
df -h
```

Không chia sẻ agent.env chứa khóa giám sát lên nhóm công khai.
Hoàn tất khi server thấy đúng ID online, nhận được ảnh thật từ máy bạn và Beszel có số liệu VM.

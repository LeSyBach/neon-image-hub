# Hướng dẫn máy mới — SERVER Neon Image Hub

> Môi trường nhóm đang dùng: **Ubuntu 22.04.5 LTS (Jammy), x86_64**. Dùng được với image 1.2.0; không cần cài lại VM. Nếu VM đã có sẵn, bỏ qua phần tạo VM và bắt đầu kiểm tra Docker/Tailscale.
> Trong ảnh bạn đang đăng nhập root: dấu nhắc thường kết thúc bằng # và ~ là /root. Với tài khoản thường như ubuntu, ~ thường là /home/ubuntu. Các lệnh dùng ~/neon-server hoặc ~/neon-worker đều đi theo home của tài khoản đang chạy; giữ cùng tài khoản trong các bước.

Dành cho thành viên giữ máy 1. Image ứng dụng: **bachcp10/neon-hub-api:1.2.0**.
Thực hiện theo thứ tự từ VM Ubuntu mới tới website, điều phối, giám sát và tên miền.
Tài liệu này độc lập; không cần đọc hướng dẫn worker để cài server.
Các giá trị có chữ IP_... hoặc DUONG-DAN-THAT là chỗ cần thay, không phải địa chỉ có thật.

## 1. Kiểm tra VM hiện có hoặc tạo VM Ubuntu mới

Thực hiện trên máy Windows của thành viên phụ trách.

1. Tải Ubuntu Server 22.04 LTS (nhóm đang dùng 22.04.5) bản **AMD64 / x86-64** tại [Ubuntu](https://releases.ubuntu.com/22.04/), chọn **server install image**.
2. Trong VMware, tạo máy ảo mới, chọn file ISO vừa tải và loại hệ điều hành Ubuntu 64-bit.
3. Đặt tên VM **neon-server**. Cấp 2 vCPU, 4 GB RAM, ổ đĩa ảo 40 GB. Đây là cấu hình khởi điểm của dự án; tốc độ thực tế cần đo lại trên máy của nhóm.
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

## 4. Tải image và tự tạo bộ server ngay trên VM

Không cần nhận ZIP, không SCP dự án và không tải mã nguồn. Bản **1.2.0** đã chứa
Compose, giao diện và công cụ khởi tạo trong image. Docker sẽ xuất chúng ra thư mục
đích bằng lệnh setup một lần; sau đó Compose chạy các dịch vụ bình thường.

Trong **Ubuntu VM server mới**, sau khi cài Docker và kết nối Tailscale:

```bash
mkdir -p ~/neon-server
cd ~/neon-server
sudo docker pull bachcp10/neon-hub-api:1.2.0
sudo docker run --rm --network none \
  --user "$(id -u):$(id -g)" \
  -v "$PWD:/setup" --entrypoint python3 \
  bachcp10/neon-hub-api:1.2.0 \
  -m setupkit server --output /setup --server-ip "$(tailscale ip -4)"
```

Thư mục ~/neon-server phải trống ở lần khởi tạo. Lệnh từ chối ghi đè thư mục đang
có cấu hình/dữ liệu. Không dùng setup để nâng cấp một server đang có kho ảnh.
`--user` giúp file được tạo thuộc tài khoản Ubuntu của bạn; không cần chép code thủ công.

## 5. Kiểm tra bộ cấu hình vừa tạo

Trong **Ubuntu VM server**, tại ~/neon-server:

```bash
ls -la
```

Phải có compose.yaml, web/, nginx.conf, scripts/, .env, .credentials/ và data/.
Image đăng ký ba ID 2.1, 3.1, 4.1 và điền WORKER_BIND bằng IP Tailscale đã cung cấp. Không phải tự tạo .env hay sửa JSON để bắt đầu.
Worker không dùng token. Khóa quản trị ứng dụng và tài khoản giám sát vẫn được tạo riêng.
Giữ WEB_BIND=127.0.0.1 để dùng cloudflared trực tiếp trên cùng VM.
Ở bước này Beszel và ntfy vẫn nghe trên localhost để khởi tạo trước bước 10.

## 6. Tải image và bật server

Trong **Ubuntu VM server**, tại `~/neon-server`:

```bash
sudo docker compose pull
sudo docker compose up -d
sudo python3 scripts/setup_notifications.py
sudo docker compose ps
```

Không cần `docker build`, `--build`, hoặc đăng nhập Docker Hub để tải hai image công khai của dự án.
Lần đầu tải image cần Internet. Chờ API khởi động/healthy rồi kiểm tra:

```bash
curl -f http://127.0.0.1:8080/api/health
SERVER_IP="$(tailscale ip -4)"
curl -f "http://${SERVER_IP}:8081/api/health"
```

Cả hai cần trả JSON có `"status":"ok"`. Nếu một lệnh lỗi:

```bash
sudo docker compose logs --tail 80 api web scheduler
```

Container `beszel-agent` trong profile riêng chưa bật là bình thường. Bước 10 hướng dẫn chạy agent trong bộ riêng, không bật trùng cả hai cách.
Nếu một lần init/setup lỗi, sửa lỗi và chạy lại đúng bước; không xóa dữ liệu để làm lại.

### Mở giao diện thử từ Windows trước khi có tên miền

Website đang bind localhost của VM, nên localhost trên Windows không phải website này.
Trong **PowerShell Windows**, thay IP NAT thật của VM:

```powershell
ssh -L 18080:127.0.0.1:8080 ubuntu@IP_NAT_THAT_CUA_VM
```

Giữ terminal SSH này mở. Trên trình duyệt Windows, vào **http://127.0.0.1:18080**.
Đóng terminal SSH sẽ ngắt đường truy cập thử này; hệ thống server vẫn chạy.

## 7. Cung cấp ID và địa chỉ server cho ba thành viên

Từ bản 1.2.0, worker không cần token. Server đã đăng ký sẵn ba ID.
Chạy trên VM server để lấy IP:

```bash
tailscale ip -4
```

Gửi cho từng thành viên ID đúng và địa chỉ http://IP-TAILSCALE-SERVER:8081.

| Thành viên | ID | Model mặc định |
|---|---|---|
| 2 | 2.1 | sd-turbo |
| 3 | 3.1 | dreamshaper-8-lcm |
| 4 | 4.1 | sd-turbo |

Không có bước lấy, gửi hoặc nhập token worker. Mỗi máy dùng một ID riêng.
Chỉ cần cài server 1.2.0 trước khi kết nối các worker 1.2.0.
Beszel/ntfy có cấu hình tài khoản riêng ở bước giám sát; đó là dịch vụ khác.

## 8. Kiểm tra worker và kho ảnh

Khi các thành viên đã chạy worker, trên **Ubuntu VM server**:

```bash
cd ~/neon-server
curl -fsS http://127.0.0.1:8080/api/stats | python3 -m json.tool
```

Kiểm tra `2.1`, `3.1`, `4.1` chuyển sang `idle` hoặc `busy` và hiển thị đúng model.
Danh sách có ID nhưng báo `offline` chưa chứng minh máy đó đã kết nối.
Khi không tìm kiếm, scheduler vẫn giao việc sinh nền nếu có worker online.

Thử tìm một chủ đề tiếng Anh trên giao diện. Nếu chưa có, chờ AI tạo ảnh và giao diện tự hiển thị.
Tìm lại cùng tên phải dùng ảnh đã lưu. Hai người tìm cùng tên mới cần chỉ có một yêu cầu tạo đang chờ.
Ảnh Neon cần được duyệt về chủ thể, tên và chất lượng trước khi đưa vào minh chứng bài tập.

Nơi lưu dữ liệu trên VM server:

```text
~/neon-server/
├── .env
├── .credentials/workers.json
└── data/
    ├── hub/hub.sqlite3
    ├── hub/images/
    ├── beszel/
    └── ntfy/
```

## 9. Đưa website lên tên miền bằng Cloudflare Tunnel

Chỉ thực hiện trên **VM server**, sau khi website local đã hoạt động.

1. Thêm tên miền vào tài khoản Cloudflare và hoàn tất DNS/nameserver theo hướng dẫn của Cloudflare nếu chưa có.
2. Trong Cloudflare One, vào Networking/Tunnels, tạo **Tunnel mới**, đặt tên phân biệt với Tunnel website cũ.
3. Chọn connector cloudflared, nền tảng Debian/Ubuntu Linux 64-bit. Chạy các lệnh cài và kết nối do dashboard cung cấp trong **Ubuntu VM server**. Lệnh có token riêng, không chia sẻ token đó.
4. Đợi connector báo kết nối. Thêm route **Published application**.
5. Chọn subdomain mới, ví dụ `anh`, cùng tên miền hiện có. Chọn dịch vụ HTTP, URL **127.0.0.1:8080**.
6. Lưu route và kiểm tra truy cập bằng tên miền HTTPS từ điện thoại dùng mạng di động.

Ở đây cloudflared cài trực tiếp trên VM, không chạy trong container. Chạy dưới dạng dịch vụ để tự bật lại.
Kiểm tra trong **Ubuntu VM server**:

```bash
sudo systemctl status cloudflared --no-pager
```

Giữ nguyên Tunnel/hostname của website cũ. Không trỏ hostname công khai tới IP Tailscale, và không công khai API nội bộ 8081.
Worker tiếp tục dùng IP Tailscale:8081, không chuyển sang domain website.
Nguồn: [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/).

## 10. Bật truy cập giám sát qua Tailscale

Chỉ làm sau khi `setup_notifications.py` ở bước 6 đã báo thành công.
Trong **Ubuntu VM server**:

```bash
cd ~/neon-server
SERVER_IP="$(tailscale ip -4)"
python3 - "$SERVER_IP" <<'PY'
from pathlib import Path
import ipaddress
import sys
ip = str(ipaddress.IPv4Address(sys.argv[1].strip()))
changes = {'MONITOR_BIND': ip, 'BESZEL_URL': 'http://' + ip + ':8090',
           'NTFY_BIND': ip, 'NTFY_BASE_URL': 'http://' + ip + ':8091'}
p = Path('.env')
lines = p.read_text().splitlines()
seen = set()
for index, line in enumerate(lines):
    key = line.split('=', 1)[0]
    if key in changes:
        lines[index] = key + '=' + changes[key]
        seen.add(key)
lines += [key + '=' + value for key, value in changes.items() if key not in seen]
p.write_text('\n'.join(lines) + '\n')
PY
sudo docker compose up -d
```

Máy mở trình duyệt quản trị cần Tailscale cùng tailnet. Vào **http://IP-TAILSCALE-SERVER:8090**.
Tạo tài khoản quản trị Beszel lần đầu. Tài khoản này tạo trong giao diện, không tự đăng nhập chỉ vì đã có các biến BESZEL_EMAIL/PASSWORD trong .env.

### Đăng ký và cài agent trên VM server

Trong Beszel chọn **Add System**, đặt tên `neon-server`, Host/IP là IP Tailscale VM server, cổng `45876`.
Lấy KEY và TOKEN từ hộp cấu hình agent do Hub cung cấp, gửi cấu hình tương ứng cho từng máy khi thêm các worker.
KEY/TOKEN này dành riêng cho Beszel; worker AI chỉ dùng ID và địa chỉ server.

Trong **Ubuntu VM server**:

```bash
mkdir -p ~/neon-monitor
cd ~/neon-monitor
nano compose.yaml
```

Dán nội dung sau vào compose.yaml, lưu bằng Ctrl+O, Enter; thoát Ctrl+X:

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

Tạo file cấu hình:

```bash
nano agent.env
```

Điền các giá trị thật từ Hub và IP máy này:

```dotenv
KEY="DAN_PUBLIC_KEY_TU_HUB"
TOKEN="DAN_TOKEN_TU_HUB"
HUB_URL=http://IP_TAILSCALE_SERVER:8090
LISTEN=IP_TAILSCALE_CUA_VM_NAY:45876
```

Không để nguyên các chữ minh họa. KEY cần toàn bộ public key, bao gồm tiền tố như ssh-ed25519.
Sau đó:

```bash
chmod 600 agent.env
sudo docker compose pull
sudo docker compose up -d
sudo docker compose logs --tail 30 agent
```

Trong Hub, thêm tiếp ba hệ thống `worker-2.1`, `worker-3.1`, `worker-4.1`, dùng IP Tailscale từng VM và cấp cấu hình agent tương ứng.
Mỗi thành viên cài agent theo tài liệu worker. Chưa bật profile monitor-agent trong Compose server vì đã chạy bộ `neon-monitor` riêng.
Chính sách mạng cần cho worker gọi server 8081/8090 và cho Hub kết nối agent 45876 trên các IP Tailscale theo cách đã chọn.
Không cần mở những cổng này ra Internet.
Nguồn: [Beszel Agent](https://beszel.dev/guide/agent-installation), [biến môi trường LISTEN](https://beszel.dev/guide/environment-variables).

### Kết nối điện thoại với ntfy

Trên điện thoại, kết nối Tailscale cùng tailnet, cài/mở ứng dụng ntfy.
Thêm địa chỉ server **http://IP-TAILSCALE-SERVER:8091**.
Trong .env server có NTFY_USER, NTFY_PASSWORD, NTFY_TOPIC: dùng chúng để đăng nhập và đăng ký topic trong ứng dụng.
Không dùng localhost của điện thoại. Thử tạo ảnh/lỗi thử để kiểm tra log và nhận thông báo trên chính điện thoại.
Khả năng nhận khi ứng dụng ở nền cần kiểm tra theo hệ điều hành điện thoại thực tế.

## 11. Dừng, chạy lại, sao lưu

Lệnh cho **Ubuntu VM server**:

```bash
cd ~/neon-server
sudo docker compose ps
sudo docker compose logs --tail 80 api scheduler web
sudo python3 scripts/backup.py
```

Backup lưu ở `~/neon-server/backups/`, gồm CSDL, ảnh được tham chiếu và khóa cấu hình lõi.
Muốn sao lưu cả lịch sử Beszel/ntfy, sao lưu thêm các thư mục dữ liệu tương ứng khi đã dừng dịch vụ.
Giữ các bản sao chứa token riêng, không đưa lên Docker Hub.

Dừng server, giữ dữ liệu:

```bash
cd ~/neon-server
sudo docker compose down
```

Bật lại:

```bash
cd ~/neon-server
sudo docker compose up -d
```

Agent giám sát chạy riêng ở ~/neon-monitor, dừng/bật tại thư mục đó bằng các lệnh Compose tương tự.
Cloudflared là dịch vụ riêng; dừng nếu cần bằng `sudo systemctl stop cloudflared`.
Thay image chỉ khi đã có bản phát hành mới; giữ nguyên .env, .credentials và data/.

## 12. Xử lý lỗi thường gặp

| Hiện tượng | Kiểm tra |
|---|---|
| Không tìm thấy compose.yaml | `pwd`, rồi `cd ~/neon-server`. |
| Port bind lỗi/IP không có | `tailscale ip -4`, so WORKER_BIND; Tailscale phải đang kết nối. |
| API unhealthy | `sudo docker compose logs --tail 80 api`; kiểm tra .env và .credentials/workers.json. |
| Worker 401/403 | Kiểm tra ID/model đã đăng ký và server đã cập nhật 1.2.0; worker không cần token. |
| Ba worker offline | Kiểm tra từ từng worker tới IP server:8081, ID không trùng và model có đủ. |
| Website mở được trên VM nhưng Windows không vào localhost | Dùng SSH forward 18080 như bước 6 hoặc domain Tunnel. |
| Tunnel 502 | Kiểm tra curl localhost:8080 trong VM và URL dịch vụ của Tunnel. |
| Điện thoại không xem được ntfy | Cùng tailnet, dùng IP server:8091, đăng nhập/topic đúng; kiểm tra NTFY_BIND. |
| Chạy lại setup_notifications.py sau khi đã đổi NTFY_BIND | Script 1.0.0 kiểm tra localhost; lần khởi tạo đầu chạy trước khi đổi bind ở bước 10. Nếu cần khởi tạo lại, tạm đưa NTFY_BIND về 127.0.0.1, up ntfy, chạy setup rồi áp dụng lại bước 10. |

## 13. Nếu muốn chuyển kho ảnh cũ trên ổ D

Dừng server cũ và sao lưu trước. Chuyển `.env`, `.credentials/` và `data/` từ D:\neon-image-hub vào `~/neon-server` của VM mới,
giữ web/, nginx.conf và Compose của gói phát hành. Không chép SQLite khi server cũ đang ghi.
Nếu .env và .credentials đã được chuyển, init chỉ giữ chúng; không thay token bằng bộ mới từ VM khác.
Sửa WORKER_BIND theo IP mới, cấp gói worker từ server này. Giám sát WSL cũ không được coi là giám sát bốn VM mới;
đăng ký lại agent thực. Không chạy đồng thời hai server phục vụ cùng kho.

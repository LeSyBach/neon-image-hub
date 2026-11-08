# Hướng dẫn máy mới — SERVER Neon Image Hub

> Môi trường nhóm đang dùng: **Ubuntu 22.04.5 LTS (Jammy), x86_64**. Dùng được với image 1.2.0; không cần cài lại VM. Nếu VM đã có sẵn, bỏ qua phần tạo VM và bắt đầu kiểm tra Docker/Tailscale.
> Trong ảnh bạn đang đăng nhập root: dấu nhắc thường kết thúc bằng # và ~ là /root. Với tài khoản thường như ubuntu, ~ thường là /home/ubuntu. Các lệnh dùng ~/neon-server hoặc ~/neon-worker đều đi theo home của tài khoản đang chạy; giữ cùng tài khoản trong các bước.

Dành cho thành viên giữ máy 1. Image ứng dụng: **bachcp10/neon-hub-api:1.2.0**.
Thực hiện theo thứ tự từ VM Ubuntu mới tới website, điều phối, giám sát và tên miền.
Tài liệu này độc lập; không cần đọc hướng dẫn worker để cài server.
Các giá trị có chữ IP_... hoặc DUONG-DAN-THAT là chỗ cần thay, không phải địa chỉ có thật.

| Việc cần làm | Xem phần |
|---|---|
| Cài server lần đầu trên VM | 1 đến 8 |
| Cho người ngoài truy cập bằng tên miền | 9 |
| Giám sát máy và thông báo điện thoại | 10 |
| Bật/tắt hằng ngày và sao lưu | 11 |
| Sửa IP/cổng, thêm ID hoặc đổi model được phép | 14 |
| Pull lại image, cập nhật giao diện hoặc nâng cấp | 15 và hướng dẫn cập nhật được liên kết |

Chạy các lệnh server trong **VM server**, tại `~/neon-server`, nơi có compose.yaml.
Root có thể bỏ `sudo`; giữ cùng tài khoản để dấu `~` luôn trỏ đúng thư mục.
Lưu nano bằng **Ctrl+O → Enter → Ctrl+X**. Chỉ sửa dòng cần đổi, giữ các dòng khác.

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
Mặc định WEB_BIND=127.0.0.1 phù hợp khi cloudflared chạy trực tiếp trên cùng VM.
Muốn mở web từ Windows bằng `http://IP-LAN-CUA-VM:8080`, sửa WEB_BIND thành 0.0.0.0 trong .env rồi `up -d`.
Cloudflare vẫn trỏ HTTP `127.0.0.1:8080` được khi bind 0.0.0.0; không đổi API worker sang bind công khai.
Ở bước này Beszel và ntfy vẫn nghe trên localhost để khởi tạo trước bước 10.

## 6. Tải image và bật server

Trong **Ubuntu VM server**, tại `~/neon-server`:

```bash
sudo docker compose pull
sudo docker compose up -d
sudo docker compose ps -a
```

Bộ server mặc định có 5 dịch vụ: **api, scheduler, web, ntfy, beszel**.
api và scheduler dùng chung image neon-hub-api; các dịch vụ khác dùng image của nhà phát hành.
Agent giám sát là tùy chọn chạy riêng ở bước 10; không tính worker AI vào 5 dịch vụ server này.
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

Beszel giám sát CPU/RAM/đĩa/mạng; ntfy nhận log sự kiện và thông báo.
Hai dịch vụ có trang web riêng. Beszel chưa tự hiển thị tên ảnh/hàng đợi; website hiện chưa có bảng quản trị công việc đầy đủ.

Trước khi đổi cổng bind ntfy, khởi tạo tài khoản thông báo một lần trên **VM server**:

```bash
cd ~/neon-server
sudo python3 scripts/setup_notifications.py
```

Python ở lệnh trên là công cụ cấu hình tài khoản trên VM, không phải cài thư viện AI trên host.
Nếu chỉ cần website trước thì có thể để phần này làm sau. Khi script thành công, tiếp tục trong **Ubuntu VM server**:

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

## 11. Bật/tắt hằng ngày và sao lưu

**Bật server** sau khi VM/Docker đã sẵn sàng:

```bash
cd ~/neon-server
sudo docker compose up -d
sudo docker compose ps -a
```

`up -d` bảo đảm các dịch vụ đã khai báo được tạo và bật; không tạo thêm bộ container trùng.
Nếu image/cấu hình không đổi thì giữ nguyên container đang chạy. Không pull hay tải model mỗi lần bật.
Không chạy thêm setup lần đầu trong thư mục này.

**Tắt server**, giữ container và dữ liệu:

```bash
cd ~/neon-server
sudo docker compose stop
```

`start` chỉ bật container đã tồn tại, không tạo phần còn thiếu hoặc áp dụng image/.env mới.
Nếu đã tạo đủ container và không đổi cấu hình thì có thể dùng `sudo docker compose start`.
Để tránh nhầm, hướng dẫn này dùng thống nhất **up -d khi bật, stop khi tắt**.
`down` xóa container/network của bộ Compose, nhưng dữ liệu dự án nằm ở thư mục bind mount vẫn còn;
sau `down` phải dùng `up -d`, không dùng `start` để tạo lại.

Compose dùng `restart: unless-stopped`: container đang chạy có thể tự bật khi Docker khởi động lại.
Container đã bị bạn stop thì không tự bật lại chỉ vì reboot; chạy `up -d` sau khi vào VM nếu cần.
Tailscale phải có IP đã ghi trong WORKER_BIND trước khi server bind cổng 8081.

**Xem log và sao lưu trước khi cập nhật:**

```bash
cd ~/neon-server
sudo docker compose logs --tail 80 api scheduler web
sudo python3 scripts/backup.py
```

Backup ở `~/neon-server/backups/`, gồm snapshot CSDL, ảnh được tham chiếu, .env và .credentials/.
Compose/web/nginx không nằm trong backup lõi đó; cách sao lưu cấu hình triển khai có trong hướng dẫn cập nhật.
Muốn giữ lịch sử Beszel/ntfy, sao lưu thêm dữ liệu tương ứng khi đã dừng các dịch vụ đó.
Không đưa bản sao chứa khóa quản trị/giám sát lên GitHub hoặc nhóm công khai.

Agent ở `~/neon-monitor` chạy độc lập: vào thư mục đó rồi dùng `sudo docker compose up -d` hoặc `stop`.
Cloudflared là dịch vụ VM riêng: `sudo systemctl status cloudflared --no-pager` để xem,
`sudo systemctl start cloudflared` để bật và `sudo systemctl stop cloudflared` để dừng.
Dừng web không tự dừng Tunnel hoặc agent; Tunnel có thể báo 502 trong lúc web đã tắt.

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
| Chạy lại setup_notifications.py sau khi đã đổi NTFY_BIND | Script hiện tại kiểm tra localhost; lần khởi tạo đầu chạy trước khi đổi bind ở bước 10. Nếu cần khởi tạo lại, tạm đưa NTFY_BIND về 127.0.0.1, up ntfy, chạy setup rồi áp dụng lại bước 10. |

## 13. Nếu muốn chuyển kho ảnh cũ trên ổ D

Chỉ cập nhật image thì không cần chuyển kho: data/hub vẫn được giữ nguyên.
Kho ảnh gồm **cả CSDL `hub.sqlite3` và các file trong `images/`**, không chỉ PNG.
Chỉ chép PNG vào thư mục thì website chưa biết ảnh nào cần hiển thị.

Nếu VM đích chưa có ảnh và muốn chuyển toàn bộ kho cũ, dừng server nguồn trước để không ghi SQLite khi chép;
sao lưu cả nguồn/đích, dừng server đích và chuyển nguyên bộ `data/hub/` sang `~/neon-server/data/hub/`.
Giữ .env/.credentials/Compose của server đích; không ghi đè cấu hình mạng và danh sách worker bằng cấu hình máy cũ.
Sau khi chép đủ dữ liệu, vào ~/neon-server và `sudo docker compose up -d`, kiểm tra ảnh cùng thống kê.

Nếu VM đích đã có kho ảnh, cần công cụ nhập/ghép metadata để giữ cả hai kho;
không ghi đè CSDL đích bằng CSDL cũ. Bộ công cụ nhập 35 ảnh cũ hiện nằm trên máy phát triển ở
`D:\neon-image-hub\exports\gallery-import`, không nằm trong repository công khai/riêng tư đã push.
Không dùng thư mục model hoặc thư mục worker-state làm kho ảnh chung.
Giám sát WSL cũ không được coi là giám sát các VM mới: đăng ký agent đúng máy thực tế.

## 14. Sửa cấu hình server và đăng ký worker mới

**Các file chỉnh trên VM server**, không phải trên Docker Hub:

| File | Nội dung cần sửa |
|---|---|
| `.env` | WEB_BIND/WEB_PORT, WORKER_BIND/WORKER_PORT, địa chỉ Beszel/ntfy |
| `.credentials/workers.json` | ID worker, model mặc định và model được phép |
| `compose.yaml` | Tag image, dịch vụ, giới hạn và cách mount; thông thường giữ nguyên |
| `nginx.conf`, `web/` | Cấu hình proxy và giao diện; nằm ngoài image API |

Không đổi ID worker bằng cách đổi tên container hoặc tên thư mục. Đổi ID phải khớp ở server và worker.

### Đổi IP/cổng website hoặc địa chỉ API worker

```bash
cd ~/neon-server
nano .env
```

Ví dụ muốn Windows vào bằng IP LAN VM: đặt `WEB_BIND=0.0.0.0`, giữ `WEB_PORT=8080`.
Sau khi sửa:

```bash
sudo docker compose config --quiet
sudo docker compose up -d
```

Chỉ chạy lệnh up sau khi kiểm tra cấu hình không lỗi. `start`/`restart` không áp dụng thay đổi .env đầy đủ.
WEB_PORT đổi thì sửa URL dịch vụ trên Cloudflare Tunnel theo cổng mới. Chỉ đổi WEB_BIND sang 0.0.0.0,
giữ cổng 8080 và cloudflared trên cùng VM thì Tunnel vẫn dùng `http://127.0.0.1:8080`.
`127.0.0.1` ở đây là VM đang chạy cloudflared, không phải Windows hoặc VM khác.

Nếu thay IP Tailscale server: sửa WORKER_BIND trên server và server_url trên từng worker.
Nếu các cổng Beszel/ntfy đang bind IP cũ, cập nhật thêm MONITOR_BIND/NTFY_BIND, BESZEL_URL/NTFY_BASE_URL
và cấu hình agent/điện thoại liên quan. API worker dùng Tailscale:8081, không công khai qua domain kho ảnh.

### Models và allowed_models có nghĩa gì?

Trong `.credentials/workers.json`, mỗi ID có:

```json
{
  "2.1": {
    "models": ["sd-turbo"],
    "allowed_models": ["sd-turbo", "dreamshaper-8-lcm"]
  }
}
```

Đây là ví dụ cho một ID, không thay toàn bộ file thực tế bằng ví dụ nếu file còn các ID khác.
`models` là mặc định khi worker không gửi lựa chọn; `allowed_models` là danh sách server cho phép.
Worker thực tế chọn model bằng AI_MODEL trong .env trên máy worker và gửi lựa chọn khi kết nối.
Ví dụ mặc định sd-turbo nhưng worker chọn DreamShaper vẫn được nếu DreamShaper thuộc allowed_models.
Muốn chỉ cho dùng SD-Turbo thì cả hai danh sách đặt `["sd-turbo"]`.
Đổi danh sách trên server không tự đổi model đang nạp trên worker, không tải file AI và không bật worker.

### Thêm ID 1.1, 2.2 hoặc worker trên máy mới

Server không giới hạn cứng ở ba ID; mỗi container phải dùng ID khác nhau.
Mở danh sách hiện có:

```bash
cd ~/neon-server
cp -p .credentials/workers.json .credentials/workers.json.before-edit
nano .credentials/workers.json
```

Nếu file đang có đúng ba ID mặc định, đây là **nội dung đầy đủ sau khi thêm 1.1**, giữ cả ba ID cũ:

```json
{
  "2.1": {
    "models": ["sd-turbo"],
    "allowed_models": ["sd-turbo", "dreamshaper-8-lcm"]
  },
  "3.1": {
    "models": ["dreamshaper-8-lcm"],
    "allowed_models": ["sd-turbo", "dreamshaper-8-lcm"]
  },
  "4.1": {
    "models": ["sd-turbo"],
    "allowed_models": ["sd-turbo", "dreamshaper-8-lcm"]
  },
  "1.1": {
    "models": ["sd-turbo"],
    "allowed_models": ["sd-turbo", "dreamshaper-8-lcm"]
  }
}
```

Nếu đã đăng ký thêm ID khác hoặc giới hạn model riêng, giữ các mục/tùy chỉnh đó và chỉ thêm mục 1.1 theo cấu trúc trên.
Muốn thêm 2.2 thay vì 1.1 thì đổi khóa mới thành "2.2", không đổi ID của các worker đang chạy.

Không để dấu phẩy sau mục cuối của JSON. Lưu rồi kiểm tra và nạp lại file bind mount:

```bash
python3 -m json.tool .credentials/workers.json >/dev/null
sudo docker compose config --quiet
sudo docker compose up -d --force-recreate api scheduler
curl -fsS http://127.0.0.1:8080/api/stats | python3 -m json.tool
```

Nếu lệnh kiểm tra JSON báo lỗi thì sửa trước khi chạy lệnh up. Tạo lại API/scheduler giúp dùng đúng file
kể cả khi trình soạn thảo thay file trên host; dữ liệu `data/` và cấu hình vẫn giữ nguyên.
ID mới hiện offline cho đến khi worker kết nối. Trên worker sửa `worker_id` đúng ID mới,
`server_url` đúng server, chọn model có file và thuộc allowed_models. Worker dùng chung image, không cần build image riêng.
Xem [cách sửa worker](HUONG-DAN-WORKER-MAY-MOI.md).

## 15. Pull lại image và cập nhật server đã cài

Chỉ cần bật hằng ngày thì không pull. Khi cần tải bản image hiện được khai báo:

```bash
cd ~/neon-server
sudo python3 scripts/backup.py
sudo docker compose pull api scheduler
sudo docker compose up -d
sudo docker compose ps -a
curl -f http://127.0.0.1:8080/api/health
```

Pull chỉ tải image, không thay container đang chạy; `up -d` mới áp dụng image mới nếu có.
Giữ .env, .credentials và data/, không khởi tạo lại server. Nếu tag không đổi nội dung, không có bản mới để áp dụng.
Nginx/Beszel/ntfy là các image riêng; không cần cập nhật chúng chỉ vì code API/worker đổi.

**Giao diện web/ và nginx.conf đang bind mount từ VM nên pull API không tự ghi đè giao diện.**
`setupkit upgrade` 1.2.0 chỉ sửa tag image và bỏ token worker cũ, không tự thay toàn bộ web/nginx/Compose.
Xem [hướng dẫn cập nhật đầy đủ](README.md) cho nâng từ bản cũ,
cập nhật riêng giao diện, giữ cấu hình cá nhân và phân biệt Docker pull/Git pull.

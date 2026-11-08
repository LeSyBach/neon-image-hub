# Bản 1.2.0 — worker chỉ dùng ID và địa chỉ server

Không còn bước lấy, gửi hoặc nhập token worker. Ba ID vẫn là 2.1, 3.1, 4.1.
API worker tiếp tục dùng mạng Tailscale, cổng 8081. Cổng website và Cloudflare giữ như trước.
Tài khoản giám sát/ntfy và khóa quản trị ứng dụng là phần riêng.

## Server đã cài 1.1.0

Trên VM server, cập nhật server trước:

```bash
cd ~/neon-server
sudo docker pull bachcp10/neon-hub-api:1.2.0
sudo docker run --rm --network none \
  --user "$(id -u):$(id -g)" -v "$PWD:/setup" --entrypoint python3 \
  bachcp10/neon-hub-api:1.2.0 -m setupkit upgrade
sudo docker compose pull
sudo docker compose up -d
```

Lệnh upgrade cập nhật tham chiếu image và bỏ token cũ trong danh sách worker.
Nó sao lưu các file đã sửa với đuôi .before-1.2.0, giữ nguyên .env, WEB_BIND/WEB_PORT,
CSDL, ảnh và model. Không chạy lại setup server trong thư mục đang có dữ liệu.

## Worker mới

Trong VM worker mới, sau khi đã cài Docker và kết nối Tailscale:

```bash
mkdir -p ~/neon-worker
cd ~/neon-worker
sudo docker pull bachcp10/neon-hub-worker:1.2.0
WORKER_ID=2.1
SERVER_URL="http://IP_TAILSCALE_SERVER:8081"
sudo docker run --rm --network none \
  --user "$(id -u):$(id -g)" -v "$PWD:/setup" --entrypoint python3 \
  bachcp10/neon-hub-worker:1.2.0 -m setupkit worker \
  --worker-id "$WORKER_ID" --server-url "$SERVER_URL" --cpus 4
```

Thay ID và IP bằng giá trị thật. Thư mục mới cần trống. Không có ô nhập token.
Tải model trực tiếp bằng curl theo bước 3 trong [hướng dẫn worker](HUONG-DAN-WORKER-MAY-MOI.md).
Worker 3.1 dùng DreamShaper8 LCM; 2.1/4.1 dùng SD-Turbo. Chọn AI_MODEL trong .env nếu cần, rồi:

```bash
sudo docker compose pull
sudo docker compose up -d
```

## Worker đã cài bản cũ

Sau khi server đã nâng cấp, trên VM worker:

```bash
cd ~/neon-worker
sudo docker pull bachcp10/neon-hub-worker:1.2.0
sudo docker run --rm --network none \
  --user "$(id -u):$(id -g)" -v "$PWD:/setup" --entrypoint python3 \
  bachcp10/neon-hub-worker:1.2.0 -m setupkit upgrade
sudo docker compose pull
sudo docker compose up -d
```

Giữ ID, server_url, AI_MODEL và thư mục model/trạng thái hiện có.
Nếu worker cũ dùng thư mục khác ~/neon-worker thì cd tới đúng thư mục chứa compose.yaml của nó.
Không chạy hai máy với cùng ID.

## Server mới hoàn toàn

```bash
mkdir -p ~/neon-server
cd ~/neon-server
sudo docker pull bachcp10/neon-hub-api:1.2.0
sudo docker run --rm --network none \
  --user "$(id -u):$(id -g)" -v "$PWD:/setup" --entrypoint python3 \
  bachcp10/neon-hub-api:1.2.0 -m setupkit server --server-ip "$(tailscale ip -4)"
sudo docker compose pull
sudo docker compose up -d
```

Phần khởi tạo thông báo và giám sát có trong hướng dẫn server đầy đủ; không phải bước nhập token worker.

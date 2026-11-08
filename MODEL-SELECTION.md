# Chọn model của worker

Trong thư mục triển khai worker, sửa đúng dòng AI_MODEL của .env:

```dotenv
AI_MODEL=sd-turbo
```

Hoặc:

```dotenv
AI_MODEL=dreamshaper-8-lcm
```

Sau khi lưu, chạy `docker compose up -d` để áp dụng môi trường mới.
Worker tự lấy bộ đường dẫn/steps/sampler đã kiểm thử trong image; không phải thay JSON.

| Model | Tệp cần có trong models/ |
|---|---|
| SD-Turbo | sd_turbo-f16-q8_0.gguf và taesd.safetensors |
| DreamShaper8 LCM | DreamShaper8_LCM.safetensors và taesd.safetensors |

Có thể để cả ba tệp trên mỗi VM. Model không nằm trong image và không được tải ngầm.
Model gốc của máy phát triển ở D:\codex-neon-local\models.
ID 2.1 và 4.1 mặc định SD-Turbo; ID 3.1 mặc định DreamShaper. Server 1.2.0 cho phép cả hai lựa chọn, không cần token worker.

Nếu còn job cũ khi đổi model, worker thử khôi phục nó trước khi nhận việc mới; giữ file model cũ để khôi phục.
VM mới xem hướng dẫn worker; VM đã cài dùng hướng dẫn nâng cấp ở guides/.

# Model AI đi kèm repository

Ba file trọng số được lưu bằng **Git LFS**:

| Tệp | Nguồn | Giấy phép được công bố |
|---|---|---|
| sd_turbo-f16-q8_0.gguf | Green-Sky/SD-Turbo-GGUF, từ stabilityai/sd-turbo | Stability AI Community License Agreement |
| DreamShaper8_LCM.safetensors | Lykon/dreamshaper-8-lcm, fine-tune từ Stable Diffusion 1.5 | CreativeML Open RAIL-M |
| taesd.safetensors | madebyollin/taesd | MIT |

Model được phân phối lại theo các điều kiện của nguồn, không đổi giấy phép thành giấy phép của code dự án.
Xem bản giấy phép trong `notices/`, nguồn/revision/checksum trong `../MODEL-SOURCES.json`.
File SD-Turbo là bản chuyển đổi/quantize do Green-Sky công bố; dự án này không huấn luyện hoặc quantize lại model.

## Tải đầy đủ

Cài Git LFS rồi clone repository. Git LFS tải trọng số thật khi checkout.
Nếu đã clone nhưng chỉ nhận file pointer nhỏ, chạy tại thư mục dự án:

```bash
git lfs install
git lfs pull
```

## Chỉ tải model cần cho một worker

Để giảm tải xuống, có thể clone mà chưa tải trọng số:

```bash
GIT_LFS_SKIP_SMUDGE=1 git clone https://github.com/LeSyBach/neon-image-hub.git
cd neon-image-hub
```

SD-Turbo:

```bash
git lfs pull --include="models/sd_turbo-f16-q8_0.gguf,models/taesd.safetensors"
```

DreamShaper8 LCM:

```bash
git lfs pull --include="models/DreamShaper8_LCM.safetensors,models/taesd.safetensors"
```

Với repository riêng tư, người tải cần được chủ repository cấp quyền GitHub.
Đặt các file đã tải vào thư mục models/ của worker như hướng dẫn triển khai.
GitHub quản lý hạn mức lưu trữ/tải xuống LFS riêng với mã nguồn Git.

Nguồn model:

- https://huggingface.co/Green-Sky/SD-Turbo-GGUF/tree/19a31586d02d64a73b4419bc193b3ecfaf38e1f0
- https://huggingface.co/Lykon/dreamshaper-8-lcm/tree/4645d8bc6a8e6b106d21606d63e8460cdad4f1a6
- https://huggingface.co/madebyollin/taesd/tree/614f76814bbe30edbe2e627ace1c2234c81a2c0e

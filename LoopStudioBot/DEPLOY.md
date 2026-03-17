# Deploy LoopStudioBot qua Portainer + GitHub

Hướng dẫn deploy bot hoàn toàn bằng Docker qua Portainer, pull code từ GitHub.

## Chuẩn bị

1. **Tạo Bot trên Telegram**: Lấy `BOT_TOKEN` từ [@BotFather](https://t.me/BotFather)
2. **Lấy Chat ID**: Dùng [@userinfobot](https://t.me/userinfobot) để lấy `REPORT_CHAT_ID`
3. **Push code lên GitHub**: Đảm bảo repo đã có đầy đủ code (không commit file `.env`)

## Deploy trên Portainer

### Bước 1: Tạo Stack mới

1. Vào **Portainer** → **Stacks** → **Add stack**
2. Đặt tên stack: `loopstudiobot`

### Bước 2: Cấu hình Deploy từ GitHub

1. Chọn **Web editor** hoặc **Git repository**
2. Nếu dùng **Git repository**:
   - **Repository URL**: `https://github.com/YOUR_USERNAME/YOUR_REPO.git`
   - **Repository reference**: `main` (hoặc nhánh bạn dùng)
   - **Compose path**: `LoopStudioBot/docker-compose.yml`
   - **Build**: Bật **Build the image**

3. Nếu dùng **Web editor**: Copy nội dung `docker-compose.yml` vào, sau đó cấu hình build context là thư mục `LoopStudioBot`

### Bước 3: Thêm Environment Variables

Trong phần **Environment variables** của Stack, thêm:

| Name | Value |
|------|-------|
| `BOT_TOKEN` | Token từ BotFather |
| `REPORT_CHAT_ID` | Chat ID của bạn |

(Tùy chọn)

| Name | Value |
|------|-------|
| `NETSTAT_INTERVAL_SECONDS` | `7200` (2 giờ, mặc định) |
| `TIMEZONE` | `Asia/Ho_Chi_Minh` |

### Bước 4: Deploy

1. Click **Deploy the stack**
2. Portainer sẽ clone repo, build image và chạy container

### Bước 5: Kiểm tra

- Vào **Containers** → tìm `loopstudiobot` → **Logs**
- Gửi `/start` cho bot trên Telegram để test

## Cập nhật Bot (sau khi push code mới)

1. Vào **Stacks** → `loopstudiobot`
2. Click **Editor** → **Pull and redeploy** (hoặc **Update the stack**)
3. Portainer sẽ pull code mới, build lại và restart container

## Lưu ý

- **Không commit** file `.env` lên GitHub (đã có trong `.gitignore`)
- Biến môi trường nhạy cảm nên đặt trong Portainer, không hardcode trong code
- Nếu dùng **Portainer Webhook**: có thể cấu hình auto-deploy khi push lên GitHub

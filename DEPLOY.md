# Deploy Loop Studio (Bot + Web) qua Portainer + GitHub

Deploy cả **LoopStudioBot** và **LoopStudioWeb** bằng 1 file docker-compose duy nhất.

## Chuẩn bị

1. **BOT_TOKEN**: Lấy từ [@BotFather](https://t.me/BotFather)
2. **REPORT_CHAT_ID**: Lấy từ [@userinfobot](https://t.me/userinfobot)
3. **SECRET_KEY**: Chuỗi bí mật cho Flask (tạo ngẫu nhiên)
4. **POSTGRES_PASSWORD**: Mật khẩu PostgreSQL (mặc định: loopstudio)

## Deploy trên Portainer

### Bước 1: Tạo Stack

1. **Portainer** → **Stacks** → **Add stack**
2. Tên: `loopstudio`

### Bước 2: Deploy từ GitHub

- **Repository URL**: `https://github.com/YOUR_USERNAME/YOUR_REPO.git`
- **Compose path**: `docker-compose.yml` (ở thư mục gốc repo)
- **Build**: Bật

### Bước 3: Environment Variables

| Name | Value |
|------|-------|
| `BOT_TOKEN` | Token từ BotFather |
| `REPORT_CHAT_ID` | Chat ID nhận báo cáo |
| `SECRET_KEY` | Chuỗi bí mật (tùy chọn, mặc định: change-me-in-production) |
| `POSTGRES_PASSWORD` | Mật khẩu DB (tùy chọn) |

### Bước 4: Deploy

Click **Deploy the stack**. Portainer sẽ chạy:
- **db**: PostgreSQL
- **loopstudioweb**: Web app (port 5000)
- **loopstudiobot**: Telegram bot

## Truy cập

- **Web**: `http://YOUR_SERVER:5000`
- **Đăng nhập mặc định**: `admin` / `admin` → **Đổi mật khẩu ngay!**

## Chỉ deploy Bot (không Web)

Dùng `LoopStudioBot/docker-compose.yml` - xem `LoopStudioBot/DEPLOY.md`.

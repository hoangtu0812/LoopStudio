# LoopStudioBot - Telegram Bot Đa Năng

Bot giám sát hệ thống LoopStudioBot: Speedtest, CPU, RAM, Disk, IP Public.

## Deploy (Bot + Web cùng lúc)

**→ Xem [DEPLOY.md](../DEPLOY.md)** - Deploy cả Bot và Web bằng 1 docker-compose.

## Chỉ deploy Bot

Dùng `LoopStudioBot/docker-compose.yml` - xem [DEPLOY.md](DEPLOY.md).

## Test local

### Cách 1: Python (nhanh khi dev)

```powershell
cd LoopStudioBot
copy .env.example .env
# Sửa .env: BOT_TOKEN, REPORT_CHAT_ID
pip install -r requirements.txt
python -m src.main
```

### Cách 2: Docker (giống môi trường production)

```powershell
cd LoopStudioBot
copy .env.example .env
# Sửa .env: BOT_TOKEN, REPORT_CHAT_ID
docker-compose up --build
# Ctrl+C để dừng
```

## Lệnh Bot

| Lệnh | Mô tả |
|------|-------|
| `/start` | Chào mừng |
| `/help` | Danh sách lệnh |
| `/netstat` | Báo cáo Speedtest + CPU/RAM/Disk + IP Public |

Báo cáo tự động gửi mỗi 2 giờ vào `REPORT_CHAT_ID`.

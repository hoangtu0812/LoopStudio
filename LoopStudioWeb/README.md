# LoopStudioWeb - Web App Loop Studio

Trang chủ Loop Studio - tập trung các ứng dụng: Bot Admin, Thời khóa biểu.

## Chạy cùng Bot (1 docker-compose)

Xem hướng dẫn tại thư mục gốc: `../DEPLOY.md`

```bash
# Từ thư mục gốc (LoopStudioTeleBot)
docker-compose up -d --build
# Web: http://localhost:5000
```

## Chạy riêng (dev)

```bash
cd LoopStudioWeb
pip install -r requirements.txt
# Cần PostgreSQL chạy sẵn, set DATABASE_URL
# Tạo user admin: python -c "
# from src.app import create_app; from src.models import User; from src.app import db
# app = create_app()
# with app.app_context():
#     u = User(username='admin'); u.set_password('admin'); u.is_admin = True
#     db.session.add(u); db.session.commit()
# "
python run.py
```

## Tính năng

- **Trang giới thiệu** (không cần đăng nhập)
- **Đăng nhập/Đăng ký**
- **Bot Admin**: Lịch sử truy cập bot, gửi thông báo đến chat
- **Thời khóa biểu**: Tạo/sửa lịch, check-in, task, cấu hình thông báo Telegram

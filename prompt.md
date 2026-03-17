Prompt: Phát triển Đa năng Telegram Bot cho Dự án Antigravity
1. Tổng quan hệ thống
Hãy đóng vai một Senior Python Developer để xây dựng một Telegram Bot đa năng. Bot này sẽ được tích hợp vào hệ sinh thái Antigravity, tuân thủ các tiêu chuẩn về cấu trúc code sạch, dễ bảo trì và sẵn sàng triển khai qua Docker.

2. Yêu cầu kỹ thuật (Tech Stack)
Ngôn ngữ: Python 3.10+

Thư viện chính: python-telegram-bot (hoặc aiogram) để xử lý logic bot.

Tiện ích hệ thống: speedtest-cli, psutil để lấy thông tin server.

Lập lịch (Scheduling): apscheduler để chạy tác vụ định kỳ.

Triển khai: Docker & Docker Compose.

Cấu trúc: Tách biệt rõ ràng giữa handlers, services, và config.

3. Các tính năng cốt lõi
Lệnh cơ bản
/start: Chào mừng người dùng và giới thiệu ngắn gọn về bot.

/help: Liệt kê danh sách tất cả các lệnh hiện có và mô tả cách dùng.

Giám sát hệ thống (/netstat)
Thực hiện đo tốc độ internet (Download, Upload, Ping).

Lấy thông tin tài nguyên server (CPU usage, RAM usage, Disk space).

Hiển thị thông tin địa chỉ IP Public của server.

Tác vụ tự động
Định kỳ mỗi 2 giờ: Tự động chạy lệnh /netstat và gửi báo cáo vào Telegram của tôi.

4. Cấu trúc Source Code yêu cầu
Yêu cầu tổ chức thư mục theo phong cách Antigravity:

Plaintext
antigravity_bot/
├── src/
│   ├── handlers/       # Xử lý các lệnh telegram (start, help, netstat)
│   ├── services/       # Logic lấy speedtest, thông số hệ thống
│   ├── utils/          # Scheduler, logger, helpers
│   ├── config.py       # Quản lý Token, Interval time từ Env vars
│   └── main.py         # Điểm chạy ứng dụng
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
5. Tiêu chuẩn mã nguồn (Coding Standards)
Đơn giản & Dễ hiểu: Code viết theo phong cách Junior -> Middle, có comment giải thích các đoạn phức tạp.

Chặt chẽ: Sử dụng logging thay vì print. Quản lý lỗi (Error handling) tốt khi speedtest thất bại hoặc mất mạng.

Environment Variables: Mọi thông tin nhạy cảm (Bot Token, Chat ID) phải được đọc từ file .env.

Docker: Viết Dockerfile tối ưu (Lightweight image như python-slim).

Output yêu cầu: Hãy cung cấp chi tiết mã nguồn cho từng file trong cấu trúc trên và hướng dẫn các bước để deploy lên server qua Docker.
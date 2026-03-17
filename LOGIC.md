# Loop Studio - Logic & Kiến trúc Hệ thống

> Tài liệu mô tả logic code, luồng xử lý và kiến trúc. Dùng làm prompt/context khi phát triển tiếp.

---

## 1. Tổng quan hệ thống

Hệ thống gồm 3 thành phần chính:

- **LoopStudioBot**: Telegram bot (Python, python-telegram-bot)
- **LoopStudioWeb**: Web app (Python, Flask)
- **PostgreSQL**: Database dùng chung

Triển khai bằng 1 file `docker-compose.yml` duy nhất.

---

## 2. LoopStudioBot - Logic

### 2.1 Khởi động

```
main.py
  → Application.builder().token(BOT_TOKEN).build()
  → register_handlers(application)   # /start, /help, /netstat
  → setup_scheduler(application)    # netstat mỗi NETSTAT_INTERVAL_SECONDS
  → application.run_polling()
```

### 2.2 Handlers (commands.py)

| Lệnh | Logic |
|------|-------|
| `/start` | `_log_access(update, "/start")` → Gửi lời chào |
| `/help` | `_log_access(update, "/help")` → Gửi danh sách lệnh |
| `/netstat` | `_log_access(update, "/netstat")` → Gọi `NetstatService.get_netstat()` → Format message → `edit_text()` |

**Log access**: Mỗi lệnh gọi `log_bot_access()` gửi POST tới `WEB_APP_URL/api/bot/log` với JSON: `telegram_user_id`, `telegram_username`, `telegram_first_name`, `command`, `chat_id`. Không chặn nếu thất bại.

### 2.3 NetstatService (netstat_service.py)

```
get_netstat()
  ├── _run_speedtest()     → speedtest.Speedtest(), trả về (download_mbps, upload_mbps, ping_ms, error)
  ├── _get_public_ip()     → urllib.request.urlopen("https://api.ipify.org")
  ├── psutil.cpu_percent()
  ├── psutil.virtual_memory()
  └── psutil.disk_usage("/")
  → NetstatResult (dataclass)
```

`format_netstat_message(result)`: Format Markdown cho Telegram.

### 2.4 Scheduler (scheduler.py)

- **APScheduler** (AsyncIOScheduler), timezone từ config
- Job mỗi `NETSTAT_INTERVAL_SECONDS` giây:
  - Gọi `NetstatService.get_netstat()`
  - `application.bot.send_message(chat_id=REPORT_CHAT_ID, text=message)`

### 2.5 Bot Logger (bot_logger.py)

- Đọc `WEB_APP_URL` từ env
- `log_bot_access(...)`: POST JSON tới `{WEB_APP_URL}/api/bot/log`
- Timeout 3s, bỏ qua lỗi

---

## 3. LoopStudioWeb - Logic

### 3.1 Khởi động (app.py)

```
create_app()
  → db.init_app(), login_manager.init_app(), csrf.init_app()
  → Đăng ký blueprints: main, api, auth, bot, schedule
  → db.create_all()
  → Nếu User.query.count() == 0: tạo admin/admin (is_admin=True)
  → start_scheduler(app)   # schedule_notifier
  → return app
```

### 3.2 Routes & Phân quyền

| Route | Auth | Logic |
|-------|------|-------|
| `/` | Không | Trang giới thiệu |
| `/auth/login` | Không | POST: kiểm tra username/password, login_user() |
| `/auth/register` | Không | POST: tạo User, set_password, redirect login |
| `/auth/logout` | Cần | logout_user() |
| `/dashboard` | Cần | Trang tổng hợp app |
| `/api/bot/log` | Không | POST JSON → tạo BotAccessLog, return 204 |
| `/bot/` | Admin | Lấy BotAccessLog 200 mới nhất |
| `/bot/send` | Admin | POST: gọi send_telegram_message(chat_id, message) |
| `/schedule/*` | Cần | Xem bên dưới |

### 3.3 Schedule - Logic chi tiết

**Tạo thời khóa biểu (create)**:
- POST: name, day_of_week (0=Th2), start_time, end_time, start_date, end_date
- Tạo Schedule → commit
- `_generate_sessions(schedule)`: Duyệt từ start_date đến end_date, nếu `date.weekday() == day_of_week` thì tạo ScheduleSession
- Tạo tất cả ScheduleSession → commit

**Sửa (edit)**:
- Xóa tất cả sessions cũ
- Cập nhật Schedule
- Gọi lại `_generate_sessions()` → tạo sessions mới

**Sinh sessions (day_of_week)**:
- Python: 0=Monday, 6=Sunday
- `current.weekday() == schedule.day_of_week` thì tạo session

**Check-in**:
- POST `/session/<id>/checkin`
- Nếu session chưa có check_ins: tạo CheckIn(session_id=id)
- Mỗi session chỉ 1 check-in

**Task**:
- POST `/session/<id>/task`: title, deadline (optional)
- Tạo Task(session_id, title, deadline)
- POST `/task/<id>/done`: toggle task.done
- POST `/session/<id>/task/<task_id>/delete`: xóa task

**Cấu hình thông báo (notifications)**:
- NotificationConfig: config_type (schedule_reminder | task_reminder), chat_id, minutes_before, enabled
- Nếu chưa có: tạo 2 config mặc định (schedule_reminder 15min, task_reminder 60min)
- POST: cập nhật chat_id, minutes_before, enabled cho từng config

### 3.4 Schedule Notifier (schedule_notifier.py)

**Chạy mỗi 1 phút** (BackgroundScheduler):

**Nhắc buổi học**:
- Lấy config `schedule_reminder` (enabled, có chat_id)
- now = datetime.now()
- lo = now + (minutes_before - 2), hi = now + (minutes_before + 2)
- Với mỗi ScheduleSession có reminder_sent=False:
  - session_dt = datetime.combine(session_date, start_time)
  - Nếu lo <= session_dt <= hi: gửi Telegram, đặt reminder_sent=True

**Nhắc task**:
- Lấy config `task_reminder`
- target = now + minutes_before
- tasks: done=False, deadline có, deadline >= now, deadline <= target
- Gửi mỗi task qua Telegram (không đánh dấu đã gửi - có thể gửi trùng)

### 3.5 Telegram Service (telegram_service.py)

- `TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"`
- `send_telegram_message(chat_id, text)`: POST `{TELEGRAM_API}/sendMessage`, json={chat_id, text}
- Trả về True nếu status 200

---

## 4. Database Models

### User
- id, username, password_hash, is_admin
- set_password(), check_password()

### BotAccessLog
- telegram_user_id, telegram_username, telegram_first_name, command, chat_id, created_at

### Schedule
- name, day_of_week, start_time, end_time, start_date, end_date
- sessions → ScheduleSession[]

### ScheduleSession
- schedule_id, session_date, start_time, end_time, reminder_sent
- check_ins → CheckIn[], tasks → Task[]

### CheckIn
- session_id, checked_at

### Task
- session_id, title, deadline, done

### NotificationConfig
- config_type, chat_id, minutes_before, enabled

---

## 5. Luồng dữ liệu

```
User gửi /start cho Bot
  → Bot: cmd_start() → _log_access() → POST Web /api/bot/log
  → Web: api_bp.bot_log() → BotAccessLog.create()
  → Bot: reply_text(welcome)

User gửi /netstat
  → Bot: cmd_netstat() → NetstatService.get_netstat()
  → Bot: edit_text(format_netstat_message())

Admin Web: /bot/send
  → send_telegram_message(chat_id, message)
  → POST api.telegram.org/bot{token}/sendMessage

Mỗi 2h: Bot scheduler
  → NetstatService.get_netstat()
  → bot.send_message(REPORT_CHAT_ID, text)

Mỗi 1 phút: Web scheduler
  → _check_schedule_reminders: sessions sắp bắt đầu → send_telegram_message(chat_id)
  → _check_task_reminders: tasks sắp deadline → send_telegram_message(chat_id)
```

---

## 6. Environment Variables

| Biến | Dùng bởi | Mô tả |
|------|----------|-------|
| BOT_TOKEN | Bot, Web | Telegram bot token |
| REPORT_CHAT_ID | Bot | Chat nhận báo cáo netstat định kỳ |
| WEB_APP_URL | Bot | URL Web (http://loopstudioweb:5000) |
| DATABASE_URL | Web | postgresql://... |
| SECRET_KEY | Web | Flask secret |
| POSTGRES_PASSWORD | docker-compose | Mật khẩu DB |
| NETSTAT_INTERVAL_SECONDS | Bot | 7200 (2h) mặc định |
| TIMEZONE | Bot | Asia/Ho_Chi_Minh |

---

## 7. Cấu trúc thư mục

```
LoopStudioTeleBot/
├── docker-compose.yml      # db, loopstudiobot, loopstudioweb
├── LoopStudioBot/
│   ├── src/
│   │   ├── handlers/commands.py
│   │   ├── services/netstat_service.py
│   │   └── utils/scheduler.py, logger.py, bot_logger.py
│   └── main.py
└── LoopStudioWeb/
    ├── src/
    │   ├── app.py
    │   ├── models/
    │   ├── routes/         # main, auth, api, bot_admin, schedule
    │   ├── services/       # telegram_service, schedule_notifier
    │   └── templates/
    └── run.py
```

---

## 8. Prompt mẫu khi mở rộng

Khi thêm tính năng mới, tham khảo:

```markdown
1. Thêm route mới: tạo Blueprint trong routes/, đăng ký trong app.py
2. Trang cần đăng nhập: @login_required
3. Trang cần admin: kiểm tra current_user.is_admin
4. Gửi Telegram: gọi send_telegram_message(chat_id, text) từ telegram_service
5. Thêm model: định nghĩa trong models/, db.create_all() tự tạo bảng
6. Thêm task định kỳ: thêm job trong schedule_notifier hoặc tạo scheduler riêng
```

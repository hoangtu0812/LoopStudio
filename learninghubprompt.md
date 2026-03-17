# Language: Vietnamese
# Prompt: Build a Study Schedule Management Web App

You are a senior full-stack software engineer.
Your task is to build a **production-ready web application** for managing my personal study schedule.

The system must be simple, maintainable, and optimized for **self-hosting**.

---

# 1. Tech Stack Requirements

Use the following technologies:

Backend

* Python
* FastAPI
* SQLite
* SQLAlchemy ORM
* APScheduler (for background scheduled jobs)
* python-telegram-bot (for sending Telegram notifications)

Frontend

* Server-side rendering preferred
* Jinja2 templates
* HTMX or AlpineJS allowed
* TailwindCSS allowed
* Avoid using NodeJS / npm as much as possible

Authentication

* Simple username + password login
* Session based authentication
* Password hashed using bcrypt

Deployment

* Docker
* docker-compose
* Must be deployable via **Portainer**
* Source code hosted on **GitHub**

---

# 2. Main Features

The application manages my **weekly study schedule** and **tasks related to each study session**.

---

# 3. Pages / UI Structure

The web app must contain these pages:

### 1. Dashboard (Home page)

This is the main page.

Show:

* Today's study sessions
* Upcoming study sessions
* Tasks due soon
* Tasks overdue
* Quick statistics

Example information:

Today:

* Subject: Math
* Time: 18:15 → 21:00
* Status: Not checked-in yet
* Tasks to do:

  * Homework 3

Also show:

* Button to check-in attendance
* Button to open session details

---

### 2. Schedule Creation Page

Allow creating recurring study sessions.

Fields:

Subject name
Day of week (Mon → Sun)
Start time
End time
Start date
End date

Example:

Subject: Math
Day: Monday
Time: 18:15 → 21:00
Start date: 01/02/2026
End date: 31/05/2026

The system must automatically generate sessions every week.

---

### 3. Schedule List Page

Display all created study schedules.

Features:

* List view
* Edit schedule
* Delete schedule
* View generated sessions

---

### 4. Session Detail Page

Each study session should have:

Information:

* Subject
* Date
* Time
* Check-in status

Actions:

* Check-in attendance
* Add tasks
* Attach documents

Attachments allowed:

* File upload
* External link

---

### 5. Task Management Page

Each session can have tasks.

Task fields:

Task title
Description
Deadline
Completion status

Example:

Task: Homework chapter 2
Deadline: 05/02/2026

---

# 4. Telegram Notification System

The app must send Telegram messages via a bot.

Use environment variables:

TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID

Notifications required:

### Study Reminder

Send reminder **15 minutes before study session starts**

Example message:

Reminder:
You have a study session soon.

Subject: Math
Time: 18:15 - 21:00

---

### Task Deadline Reminder

Send reminder **1 day before deadline**

Example:

Task Reminder
Homework chapter 2 is due tomorrow.

Deadline: 05/02/2026

---

# 5. Statistics

Provide charts for:

### Attendance Statistics

By subject
By week

Examples:

* Number of attended sessions per subject
* Number of sessions attended per week

Use a lightweight chart library such as:

Chart.js (via CDN)

Do not require npm.

---

# 6. Database Schema

Design a SQLite schema.

Suggested tables:

users

* id
* username
* password_hash

subjects

* id
* name

schedules

* id
* subject_id
* weekday
* start_time
* end_time
* start_date
* end_date

sessions

* id
* schedule_id
* date
* checked_in (boolean)

tasks

* id
* session_id
* title
* description
* deadline
* completed

attachments

* id
* session_id
* file_path
* external_link

---

# 7. Scheduler System

Use **APScheduler** to:

1. Generate study sessions automatically
2. Send reminders:

   * 15 minutes before session
   * 1 day before task deadline

Scheduler must run inside FastAPI startup event.

---

# 8. UI/UX Requirements

Modern design

Features:

* Dark mode / Light mode toggle
* Responsive layout
* Sidebar navigation

Pages:

Dashboard
Create Schedule
View Schedule
Tasks
Statistics

---

# 9. Homepage Priority Logic

When opening dashboard, prioritize showing:

1️⃣ Today’s study sessions
2️⃣ Tasks due today
3️⃣ Upcoming sessions

---

# 10. GitHub Project Structure

Recommended structure:

project-root

app
routers
models
services
templates
static
database

main.py

docker
Dockerfile
docker-compose.yml

README.md

---

# 11. Docker Requirements

Provide:

Dockerfile
docker-compose.yml

Expose port:

8000

Persist:

SQLite database
uploaded files

---

# 12. Security

Minimum requirements:

* Login required for all pages
* Password hashing with bcrypt
* Session authentication

---

# 13. README.md

Include instructions:

How to run locally
How to run with Docker
How to deploy with Portainer

---

# 14. Extra Features (Optional but Recommended)

Calendar view (weekly calendar)

Search tasks

Export schedule

---

# 15. Code Quality Requirements

* Clean architecture
* Modular structure
* Python typing
* Clear comments
* Use services layer

---

# Final Deliverable

Generate the **complete project codebase**, including:

* FastAPI backend
* HTML templates
* SQLite models
* Telegram integration
* Scheduler
* Docker deployment

The project must run with:

docker compose up

and be ready for deployment via Portainer.

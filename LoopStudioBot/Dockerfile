# Lightweight Python image
FROM python:3.11-slim

WORKDIR /app

# Copy requirements trước để tận dụng cache layer
COPY requirements.txt .

# Cài đặt Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Chạy từ thư mục LoopStudioBot (context)
ENV PYTHONPATH=/app
CMD ["python", "-m", "src.main"]

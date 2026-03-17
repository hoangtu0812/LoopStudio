FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir psycopg2-binary

COPY . .
ENV PYTHONPATH=/app
EXPOSE 5000
CMD ["python", "run.py"]

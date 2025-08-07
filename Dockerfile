FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    sqlite3 \
    libsqlite3-dev \
    && echo "SQLite installed OK" \
    || (echo "Failed to install SQLite" && exit 1)

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker","--timeout", "24000","--bind", "0.0.0.0:8000", "api:app"]
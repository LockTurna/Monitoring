FROM python:3.11-slim

# Install Docker CLI (untuk jalankan docker restart)
RUN apt-get update && apt-get install -y \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY app.py .

RUN pip install flask

EXPOSE 5001

CMD ["python", "app.py"]

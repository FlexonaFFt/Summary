FROM python:3.10-slim
WORKDIR /app
COPY ./app /app
RUN pip install --no-cache-dir fastapi[all] aiokafka aioredis uvicorn loguru python-docx
RUN pip install -r requirements.txt
RUN apt-get update && \
    apt-get install -y netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*
COPY wait-for-kafka.sh /wait-for-kafka.sh
RUN chmod +x /wait-for-kafka.sh
CMD ["/wait-for-kafka.sh"]
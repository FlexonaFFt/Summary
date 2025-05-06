from kafka import KafkaConsumer
import redis
from loguru import logger
import os
import time

logger.add("/var/log/worker/worker.log", rotation="1 day")
r = redis.Redis(host='redis', port=6379)

bootstrap_servers = os.getenv("BOOTSTRAP_SERVERS", "kafka:9092")

while True:
    try:
        consumer = KafkaConsumer(
            "summarize",
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset='earliest',
            group_id="summarizer-group"
        )
        print("✅ Connected to Kafka")
        break
    except Exception:
        print("❌ Kafka not available yet. Retrying in 5s...")
        time.sleep(5)

for msg in consumer:
    key, text = msg.value.decode().split("|", 1)
    logger.info(f"Получено сообщение: {key}")
    summary = text[:150] + '...'  # простая имитация суммаризации
    r.set(key, summary)
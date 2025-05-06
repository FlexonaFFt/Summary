from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uuid
from aiokafka import AIOKafkaProducer
import aioredis
import asyncio, os
from loguru import logger

app = FastAPI()
redis = None
producer = None

class TextRequest(BaseModel):
    text: str
while True:
    try:
        redis = aioredis.from_url("redis://redis")
        @app.on_event("startup")
        async def startup_event():
            bootstrap_servers = os.getenv("BOOTSTRAP_SERVERS", "kafka:9092")
            global redis, producer
            redis = aioredis.from_url("redis://redis")
            producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)
            await producer.start()
            logger.add("/var/log/fastapi/app.log", rotation="1 day")
            logger.info("FastAPI запущен")
        break
    except Exception:
        print("❌ Redis or Kafka is not available yet. Retrying in 5s...")
        asyncio.sleep(5)


@app.on_event("shutdown")
async def shutdown_event():
    await producer.stop()

@app.post("/summarize")
async def summarize(data: TextRequest):
    request_id = str(uuid.uuid4())
    await redis.set(request_id, "processing")
    await producer.send_and_wait("summarize", f"{request_id}|{data.text}".encode())
    return {"request_id": request_id}

@app.get("/status/{request_id}")
async def check_status(request_id: str):
    result = await redis.get(request_id)
    if result:
        result = result.decode()
        if result != "processing":
            return {"status": "done", "summary": result}
        else:
            return {"status": "processing"}
    return {"status": "not_found"}
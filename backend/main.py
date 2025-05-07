from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uuid
from aiokafka import AIOKafkaProducer
import aioredis
import asyncio, os
from loguru import logger
from contextlib import asynccontextmanager

redis = None
producer = None

class TextRequest(BaseModel):
    text: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    global redis, producer
    
    connected = False
    while not connected:
        try:
            bootstrap_servers = os.getenv("BOOTSTRAP_SERVERS", "localhost:9092")  # Изменено с kafka:9092 на localhost:9092
            redis = aioredis.from_url("redis://localhost")  # Изменено с redis://redis на redis://localhost
            producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)
            await producer.start()
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
            os.makedirs(log_dir, exist_ok=True)
            logger.add(os.path.join(log_dir, "app.log"), rotation="1 day")
            logger.info("FastAPI запущен")
            connected = True
        except Exception as e:
            print(f"❌ Redis or Kafka is not available yet. Retrying in 5s... Error: {e}")
            await asyncio.sleep(5)
    
    yield  # This yield separates startup from shutdown logic
    
    # Shutdown logic
    if producer:
        await producer.stop()
    logger.info("FastAPI остановлен")

app = FastAPI(lifespan=lifespan)

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
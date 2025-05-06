from aiokafka import AIOKafkaProducer
import json

producer = None

async def start_kafka():
    global producer
    producer = AIOKafkaProducer(bootstrap_servers="kafka:9092")
    await producer.start()

async def send_to_kafka(topic, message):
    await producer.send_and_wait(topic, json.dumps(message).encode())
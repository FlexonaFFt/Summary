#!/bin/sh

KAFKA_HOST=${KAFKA_HOST:-kafka}
KAFKA_PORT=${KAFKA_PORT:-9092}

echo "Waiting for Kafka at $KAFKA_HOST:$KAFKA_PORT..."

while ! nc -z $KAFKA_HOST $KAFKA_PORT; do
  sleep 1
done

echo "✅ Kafka is available, starting app..."
exec uvicorn main:app --host 0.0.0.0 --port 8000

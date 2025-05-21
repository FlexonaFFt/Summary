FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir aiogram aiohttp loguru aioredis aiofiles uuid
CMD ["python", "bot.py"]
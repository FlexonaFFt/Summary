from kafka import KafkaConsumer
import redis
import os
import time
from loguru import logger
import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer

# Настройка логирования
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
logger.add(os.path.join(log_dir, "worker.log"), rotation="1 day")

# Глобальные переменные для модели и токенизатора
model = None
tokenizer = None

# Функция для загрузки модели
def load_model():
    global model, tokenizer
    try:
        logger.info("Загрузка модели rut5-base-sum...")
        model_name = "IlyaGusev/rut5_base_sum_gazeta"
        tokenizer = T5Tokenizer.from_pretrained(model_name)
        model = T5ForConditionalGeneration.from_pretrained(model_name)
        logger.info("Модель успешно загружена")
        return True
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели: {e}")
        return False

# Функция для суммаризации текста с использованием модели rut5-base-sum
def summarize_text(text, max_length=250):
    try:
        # Проверяем, загружена ли модель
        if model is None or tokenizer is None:
            if not load_model():
                logger.error("Не удалось загрузить модель для суммаризации")
                return "Ошибка при суммаризации текста"
        
        # Подготовка входных данных
        input_ids = tokenizer.encode("summarize: " + text, return_tensors="pt", max_length=1024, truncation=True)
        
        # Генерация суммаризации
        with torch.no_grad():
            summary_ids = model.generate(
                input_ids,
                max_length=max_length,
                min_length=40,
                length_penalty=2.0,
                num_beams=4,
                early_stopping=True
            )
        
        # Декодирование результата
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        return summary
    except Exception as e:
        logger.error(f"Ошибка при суммаризации: {e}")
        return "Ошибка при суммаризации текста"

# Основная функция
def main():
    # Подключение к Redis
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    
    # Предварительная загрузка модели
    logger.info("Инициализация модели суммаризации...")
    load_model()
    
    # Ожидание доступности Kafka
    connected = False
    while not connected:
        try:
            # Подключение к Kafka
            consumer = KafkaConsumer(
                'summarize',
                bootstrap_servers='localhost:9092',
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                group_id='summary-worker',
                value_deserializer=lambda x: x.decode('utf-8')
            )
            connected = True
            logger.info("Подключено к Kafka")
        except Exception as e:
            logger.error(f"Ошибка подключения к Kafka: {e}")
            logger.info("Повторная попытка через 5 секунд...")
            time.sleep(5)
    
    # Обработка сообщений
    logger.info("Начало обработки сообщений")
    for message in consumer:
        try:
            # Разбор сообщения
            value = message.value
            request_id, text = value.split('|', 1)
            
            logger.info(f"Получено сообщение: ID={request_id}, длина текста={len(text)}")
            
            # Суммаризация текста
            summary = summarize_text(text)
            
            # Сохранение результата в Redis
            redis_client.set(request_id, summary)
            
            logger.info(f"Суммаризация завершена: ID={request_id}")
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")

if __name__ == "__main__":
    main()
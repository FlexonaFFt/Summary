from kafka import KafkaConsumer
import redis
import os
import time
from loguru import logger
import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer, AutoModelForQuestionAnswering, AutoTokenizer

log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
logger.add(os.path.join(log_dir, "worker.log"), rotation="1 day")

model, qa_model = None, None 
tokenizer, qa_tokenizer = None, None 

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

def load_qa_model():
    global qa_model, qa_tokenizer
    try:
        logger.info("Загрузка модели для ответов на вопросы...")
        model_name = "distilbert-base-cased-distilled-squad"
        qa_tokenizer = AutoTokenizer.from_pretrained(model_name)
        qa_model = AutoModelForQuestionAnswering.from_pretrained(model_name)
        logger.info("Модель для ответов на вопросы успешно загружена")
        return True
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели для ответов на вопросы: {e}")
        return False

def summarize_text(text, max_length=250):
    try:
        if model is None or tokenizer is None:
            if not load_model():
                logger.error("Не удалось загрузить модель для суммаризации")
                return "Ошибка при суммаризации текста"
        
        input_ids = tokenizer.encode("summarize: " + text, return_tensors="pt", max_length=1024, truncation=True)
        with torch.no_grad():
            summary_ids = model.generate(
                input_ids,
                max_length=max_length,
                min_length=40,
                length_penalty=2.0,
                num_beams=4,
                early_stopping=True
            )
        
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
        return summary
    except Exception as e:
        logger.error(f"Ошибка при суммаризации: {e}")
        return "Ошибка при суммаризации текста"

def answer_question(context, question):
    try:
        if qa_model is None or qa_tokenizer is None:
            if not load_qa_model():
                logger.error("Не удалось загрузить модель для ответов на вопросы")
                return "Ошибка при обработке вопроса"
        
        max_length = 512
        if len(context) > max_length:
            context = context[:max_length]
        
        inputs = qa_tokenizer(question, context, return_tensors="pt", max_length=512, truncation=True)
        with torch.no_grad():
            outputs = qa_model(**inputs)
            answer_start = torch.argmax(outputs.start_logits)
            answer_end = torch.argmax(outputs.end_logits)
            
            # Проверка валидности ответа
            if answer_end < answer_start:
                return "Не удалось найти ответ на ваш вопрос в предоставленном контексте."
            
            tokens = qa_tokenizer.convert_ids_to_tokens(inputs.input_ids[0])
            answer = qa_tokenizer.convert_tokens_to_string(tokens[answer_start:answer_end+1])
            
            # Дополнительная проверка на специальные токены
            if not answer or len(answer) < 2 or answer == "[CLS]" or answer == "[SEP]":
                # Попробуем использовать другой подход - взять несколько токенов с наивысшими вероятностями
                start_scores = outputs.start_logits[0].cpu().numpy()
                end_scores = outputs.end_logits[0].cpu().numpy()
                
                # Найдем топ-5 начальных и конечных позиций
                start_indexes = (-start_scores).argsort()[:5]
                end_indexes = (-end_scores).argsort()[:5]
                
                # Перебираем комбинации и ищем валидный ответ
                for start_idx in start_indexes:
                    for end_idx in end_indexes:
                        if end_idx < start_idx or end_idx - start_idx > 20:  # Ограничиваем длину ответа
                            continue
                        
                        candidate = qa_tokenizer.convert_tokens_to_string(
                            tokens[start_idx:end_idx+1]
                        )
                        
                        # Проверяем, что ответ не содержит только специальные токены
                        if candidate and len(candidate) > 2 and candidate != "[CLS]" and candidate != "[SEP]":
                            return candidate
                
                # Если все еще не нашли ответ, возвращаем сообщение
                return "Не удалось найти ответ на ваш вопрос в предоставленном контексте."
            
            return answer
    except Exception as e:
        logger.error(f"Ошибка при ответе на вопрос: {e}")
        return "Ошибка при обработке вопроса"

def main():
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    logger.info("Инициализация моделей...")
    load_model()
    load_qa_model()
    
    connected = False
    while not connected:
        try:
            consumer = KafkaConsumer(
                'summarize', 'question',  
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
    
    logger.info("Начало обработки сообщений")
    for message in consumer:
        try:
            topic = message.topic
            value = message.value
            
            if topic == 'summarize':
                request_id, text = value.split('|', 1)
                logger.info(f"Получено сообщение для суммаризации: ID={request_id}, длина текста={len(text)}")
                
                summary = summarize_text(text)
                redis_client.set(request_id, summary)
                
                logger.info(f"Суммаризация завершена: ID={request_id}")
            
            elif topic == 'question':
                parts = value.split('|', 2)
                if len(parts) == 3:
                    request_id, context, question = parts
                    logger.info(f"Получен вопрос: ID={request_id}, вопрос={question}, длина контекста={len(context)}")
                    
                    answer = answer_question(context, question)
                    redis_client.set(request_id, answer)
                    
                    logger.info(f"Ответ на вопрос подготовлен: ID={request_id}")
                else:
                    logger.error(f"Неверный формат сообщения для вопроса: {value}")
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")

if __name__ == "__main__":
    main()
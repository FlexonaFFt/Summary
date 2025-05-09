from kafka import KafkaConsumer
import redis
import os
import time
import numpy as np 
from loguru import logger
import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer, AutoModelForQuestionAnswering, AutoTokenizer, pipeline, MarianMTModel, MarianTokenizer

log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(log_dir, exist_ok=True)
logger.add(os.path.join(log_dir, "worker.log"), rotation="1 day")

model, qa_model = None, None 
tokenizer, qa_tokenizer = None, None 
translator_ru_en, translator_en_ru = None, None
translator_tokenizer_ru_en, translator_tokenizer_en_ru = None, None

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
        model_name = "allenai/t5-small-squad11"  
        qa_tokenizer = T5Tokenizer.from_pretrained(model_name)
        qa_model = T5ForConditionalGeneration.from_pretrained(model_name)
        logger.info("Модель для ответов на вопросы успешно загружена")
        return True
    except Exception as e:
        logger.error(f"Ошибка при загрузке модели для ответов на вопросы: {e}")
        return False

def load_translation_models():
    global translator_ru_en, translator_en_ru, translator_tokenizer_ru_en, translator_tokenizer_en_ru
    try:
        logger.info("Загрузка моделей для перевода...")
        ru_en_model = "Helsinki-NLP/opus-mt-ru-en"
        translator_tokenizer_ru_en = MarianTokenizer.from_pretrained(ru_en_model)
        translator_ru_en = MarianMTModel.from_pretrained(ru_en_model)
        
        en_ru_model = "Helsinki-NLP/opus-mt-en-ru"
        translator_tokenizer_en_ru = MarianTokenizer.from_pretrained(en_ru_model)
        translator_en_ru = MarianMTModel.from_pretrained(en_ru_model)
        
        logger.info("Модели для перевода успешно загружены")
        return True
    except Exception as e:
        logger.error(f"Ошибка при загрузке моделей для перевода: {e}")
        return False

def translate_ru_to_en(text):
    try:
        if translator_ru_en is None or translator_tokenizer_ru_en is None:
            if not load_translation_models():
                logger.error("Не удалось загрузить модели для перевода")
                return text
        
        max_length = 512
        if len(text) > max_length:
            chunks = []
            for i in range(0, len(text), max_length):
                chunks.append(text[i:i+max_length])
            
            translated_chunks = []
            for chunk in chunks:
                inputs = translator_tokenizer_ru_en(chunk, return_tensors="pt", padding=True, truncation=True, max_length=512)
                with torch.no_grad():
                    outputs = translator_ru_en.generate(**inputs)
                translated_chunk = translator_tokenizer_ru_en.batch_decode(outputs, skip_special_tokens=True)[0]
                translated_chunks.append(translated_chunk)
            
            return " ".join(translated_chunks)
        else:
            inputs = translator_tokenizer_ru_en(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
            with torch.no_grad():
                outputs = translator_ru_en.generate(**inputs)
            return translator_tokenizer_ru_en.batch_decode(outputs, skip_special_tokens=True)[0]
    except Exception as e:
        logger.error(f"Ошибка при переводе с русского на английский: {e}")
        return text

def translate_en_to_ru(text):
    try:
        if translator_en_ru is None or translator_tokenizer_en_ru is None:
            if not load_translation_models():
                logger.error("Не удалось загрузить модели для перевода")
                return text
        
        inputs = translator_tokenizer_en_ru(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
        with torch.no_grad():
            outputs = translator_en_ru.generate(**inputs)
        return translator_tokenizer_en_ru.batch_decode(outputs, skip_special_tokens=True)[0]
    except Exception as e:
        logger.error(f"Ошибка при переводе с английского на русский: {e}")
        return text

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
        
        logger.info(f"Перевод вопроса на английский: {question}")
        en_question = translate_ru_to_en(question)
        logger.info(f"Переведенный вопрос: {en_question}")
        

        max_context_length = 3000 
        short_context = context[:max_context_length]
        logger.info(f"Перевод контекста на английский (первые {len(short_context)} символов)")
        en_context = translate_ru_to_en(short_context)
        logger.info(f"Контекст переведен на английский (длина: {len(en_context)})")
        
        input_text = f"question: {en_question} context: {en_context} Give a detailed and comprehensive answer based on the context."
        input_ids = qa_tokenizer.encode(input_text, return_tensors="pt", max_length=1024, truncation=True)
        
        with torch.no_grad():
            output_ids = qa_model.generate(
                input_ids,
                max_length=200, 
                min_length=30,   
                length_penalty=2.5, 
                num_beams=5,   
                early_stopping=True,
                no_repeat_ngram_size=3, 
                temperature=0.8,  
                top_k=50,      
                repetition_penalty=1.2  
            )
        
        en_answer = qa_tokenizer.decode(output_ids[0], skip_special_tokens=True)
        logger.info(f"Получен ответ на английском: {en_answer}")
        if not en_answer or len(en_answer) < 5:
            return "Не удалось найти ответ на ваш вопрос в предоставленном контексте."
        
        ru_answer = translate_en_to_ru(en_answer)
        logger.info(f"Ответ переведен на русский: {ru_answer}")
        
        return ru_answer
    except Exception as e:
        logger.error(f"Ошибка при ответе на вопрос: {e}")
        return "Ошибка при обработке вопроса"

def preprocess_question(question):
    question = question.strip()
    if not question.endswith('?'):
        question += '?'
    
    return question

def main():
    redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
    logger.info("Инициализация моделей...")
    load_model()
    load_qa_model()
    load_translation_models()
    
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
                    # Предварительная обработка вопроса
                    question = preprocess_question(question)
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
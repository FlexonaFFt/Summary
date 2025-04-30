from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
from typing import Tuple
import os
import re

# Кэш для модели и токенизатора
_model = None
_tokenizer = None

def load_model():
    """Загружает модель и токенизатор"""
    global _model, _tokenizer
    if _model is None:
        model_name = "IlyaGusev/rut5_base_sum_gazeta"
        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    return _model, _tokenizer

def clean_text(text: str) -> str:
    """Очищает текст от лишних пробелов и специальных символов"""
    text = re.sub(r'\s+', ' ', text)  # Удаляем множественные пробелы
    text = re.sub(r'[^\w\s.,;:!?()-]', ' ', text)  # Удаляем спецсимволы
    return text.strip()

def count_words(text: str) -> int:
    """Подсчитывает количество слов в тексте"""
    return len(text.split())

def split_into_chunks(text: str, max_chunk_words: int = 500) -> list:
    """Разбивает текст на части по предложениям"""
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    chunks = []
    current_chunk = []
    current_length = 0
    
    for sentence in sentences:
        words_in_sentence = len(sentence.split())
        if current_length + words_in_sentence > max_chunk_words and current_chunk:
            chunks.append(' '.join(current_chunk))
            current_chunk = []
            current_length = 0
        current_chunk.append(sentence)
        current_length += words_in_sentence
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

def summarize_text_chunk(text: str, max_words: int, min_words: int, do_sample: bool) -> str:
    """Суммаризирует одну часть текста"""
    model, tokenizer = load_model()
    
    # Конвертируем слова в токены с запасом
    max_tokens = max_words * 2  # Эмпирический коэффициент
    min_tokens = min_words * 1
    
    inputs = tokenizer(
        text,
        max_length=1024,
        truncation=True,
        return_tensors="pt"
    )
    
    summary_ids = model.generate(
        inputs["input_ids"],
        max_length=max_tokens,
        min_length=min_tokens,
        num_beams=4,
        early_stopping=True,
        no_repeat_ngram_size=3,
        length_penalty=1.5,
        do_sample=do_sample,
    )
    
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return clean_text(summary)

def summarize_text(
    text: str,
    max_words: int = 150,
    min_words: int = 50,
    do_sample: bool = False
) -> str:
    """Основная функция суммаризации с обработкой больших текстов"""
    text = clean_text(text)
    if count_words(text) <= max_words:
        return text  # Если текст уже короткий
    
    chunks = split_into_chunks(text)
    summaries = []
    
    for chunk in chunks:
        chunk_summary = summarize_text_chunk(
            chunk,
            max_words=max_words // len(chunks),
            min_words=min_words // len(chunks),
            do_sample=do_sample
        )
        summaries.append(chunk_summary)
    
    # Объединяем суммаризации и проверяем длину
    final_summary = ' '.join(summaries)
    final_words = final_summary.split()
    
    if len(final_words) > max_words:
        final_summary = ' '.join(final_words[:max_words])
    elif len(final_words) < min_words:
        # Если суммаризация слишком короткая, пробуем еще раз
        return summarize_text_chunk(text, max_words, min_words, do_sample)
    
    return final_summary

def process_file(file_path: str, **kwargs) -> Tuple[str, str]:
    """Обрабатывает файл и возвращает оригинал и суммаризацию"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Файл {file_path} не найден")
    
    with open(file_path, 'r', encoding='utf-8') as file:
        text = file.read()
    
    if not text.strip():
        raise ValueError("Файл пуст")
    
    text = clean_text(text)
    summary = summarize_text(text, **kwargs)
    return text, summary

def calculate_metrics(original: str, summary: str, request_params: dict) -> dict:
    """Вычисляет метрики суммаризации"""
    orig_len = count_words(original)
    summ_len = count_words(summary)
    
    return {
        "original_length": orig_len,
        "summary_length": summ_len,
        "compression_ratio": round(orig_len / summ_len, 2) if summ_len > 0 else 0,
        "requested_length": {
            "max_words": request_params.get('max_words', 150),
            "min_words": request_params.get('min_words', 50),
            "request_fulfilled": summ_len <= request_params.get('max_words', 150) and 
                               summ_len >= request_params.get('min_words', 50)
        }
    }
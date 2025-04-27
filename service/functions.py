import os
import uuid
import logging
import torch
import io
from enum import Enum
from pathlib import Path
from typing import Dict
from fastapi import UploadFile
from docx import Document
from transformers import T5ForConditionalGeneration, T5Tokenizer

def generate_file_id() -> str:
    return str(uuid.uuid4())

def ensure_upload_dir(upload_dir: str = "uploads") -> None:
    os.makedirs(upload_dir, exist_ok=True)

def extract_text_from_file(file: UploadFile) -> str:
    file_extension = Path(file.filename).suffix.lower()
    
    try:
        if file_extension in [".txt", ".md", ".csv"]:
            contents = file.file.read()
            file.file.seek(0)
            return contents.decode("utf-8")
        elif file_extension == ".docx":
            content = file.file.read()
            file.file.seek(0)
            doc = Document(io.BytesIO(content))
            return "\n".join([paragraph.text for paragraph in doc.paragraphs])
        else:
            return f"Text extraction not supported for {file_extension} files"
    except Exception as e:
        return f"Error extracting text: {str(e)}"

def save_extracted_text(text: str, file_id: str, upload_dir: str = "uploads") -> str:
    ensure_upload_dir(upload_dir)
    text_filename = f"{file_id}_extracted.txt"
    text_file_path = os.path.join(upload_dir, text_filename)
    
    with open(text_file_path, "w", encoding="utf-8") as file:
        file.write(text)
    
    return text_file_path

def get_text_by_file_id(file_id: str, upload_dir: str = "uploads") -> str:
    text_filename = f"{file_id}_extracted.txt"
    text_file_path = os.path.join(upload_dir, text_filename)
    
    if not os.path.exists(text_file_path):
        raise FileNotFoundError(f"File with ID {file_id} not found")
    
    with open(text_file_path, "r", encoding="utf-8") as file:
        return file.read()

def detect_language(text: str) -> str:
    """Определяет язык текста (ru/en)"""
    cyrillic_count = sum(1 for char in text if 'а' <= char.lower() <= 'я')
    return 'ru' if cyrillic_count > len(text) * 0.3 else 'en'

class TextSummarizer:
    def __init__(self, model_path: str = "../updated_model"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = T5Tokenizer.from_pretrained(
            "cointegrated/rut5-small", 
            legacy=False
        )
        self.model = T5ForConditionalGeneration.from_pretrained(model_path).to(self.device)
        logging.info(f"Model loaded on {self.device}")

    def summarize(self, text: str, max_length: int = 256, min_length: int = 30, variation: float = 0.8) -> str:
        """Суммаризация текста с помощью локальной модели"""
        inputs = self.tokenizer(
            f"summarize: {text}",
            return_tensors="pt",
            max_length=512,
            truncation=True
        ).to(self.device)
        
        outputs = self.model.generate(
            **inputs,
            max_length=max_length,
            min_length=min_length,
            num_beams=5,
            early_stopping=True,
            length_penalty=variation,
            no_repeat_ngram_size=3,
            do_sample=True,
            temperature=0.7,
            top_k=50
        )
        
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def summarize_long_text(self, text: str, max_length: int = 256, min_length: int = 30) -> str:
        """Суммаризация длинного текста с сохранением контекста"""
        # Разделяем текст на чанки с перекрытием
        chunks = self._split_text_with_overlap(text)
        
        # Суммаризируем каждый чанк
        chunk_summaries = []
        for chunk in chunks:
            summary = self.summarize(chunk, max_length=max_length, min_length=min_length)
            chunk_summaries.append(summary)
        
        # Объединяем суммаризации и делаем финальную суммаризацию
        combined_summary = ' '.join(chunk_summaries)
        return self.summarize(combined_summary, max_length=max_length, min_length=min_length)

    def _split_text_with_overlap(self, text: str, chunk_size: int = 512, overlap: int = 128) -> list:
        """Разделяет текст на чанки с перекрытием"""
        words = text.split()
        chunks = []
        i = 0
        
        while i < len(words):
            end = min(i + chunk_size, len(words))
            chunk = ' '.join(words[i:end])
            chunks.append(chunk)
            
            if end < len(words):
                i = end - overlap
            else:
                break
        
        return chunks
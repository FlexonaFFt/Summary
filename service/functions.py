import os
import uuid
import logging
import torch
import io
from enum import Enum
from pathlib import Path
from typing import Dict
from fastapi import UploadFile
from transformers import T5ForConditionalGeneration, T5Tokenizer

import pdfplumber
from pdf2image import convert_from_bytes
import pytesseract
from docx import Document

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
        elif file_extension == ".pdf":
            content = file.file.read()
            file.file.seek(0)
            
            # Попробуем извлечь текст с помощью pdfplumber
            text = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text.append(page_text)
            
            extracted_text = "\n".join(text) if text else ""
            
            # Если текст не извлечен (например, PDF содержит только изображения), используем OCR
            if not extracted_text.strip():
                try:
                    # Конвертируем PDF в изображения
                    images = convert_from_bytes(content)
                    ocr_text = []
                    for image in images:
                        text = pytesseract.image_to_string(image, lang='eng+rus')  # Поддержка русского и английского
                        ocr_text.append(text)
                    extracted_text = "\n".join(ocr_text)
                except Exception as ocr_e:
                    logging.error(f"OCR extraction failed: {str(ocr_e)}")
                    return f"Error extracting text with OCR: {str(ocr_e)}"
            
            return extracted_text
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
        chunks = self._split_text_with_overlap(text, chunk_size=300, overlap=100)
        chunk_summaries = []
        for chunk in chunks:
            summary = self.summarize(chunk, max_length=100, min_length=20)
            chunk_summaries.append(summary)
        
        combined_summary = ' '.join(chunk_summaries)
        final_summary = self._postprocess_summary(
            self.summarize(combined_summary, max_length=max_length, min_length=min_length))
        
        return final_summary

    def _split_text_with_overlap(self, text: str, chunk_size: int = 300, overlap: int = 100) -> list:
        """Разделяет текст на чанки с перекрытием, сохраняя целостность предложений"""
        sentences = text.split('. ')
        chunks = []
        current_chunk = []
        current_length = 0
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_length = len(sentence.split())
            
            if current_length + sentence_length <= chunk_size or not current_chunk:
                current_chunk.append(sentence)
                current_length += sentence_length
            else:
                chunks.append('. '.join(current_chunk) + '.')
                overlap_start = max(0, len(current_chunk) - overlap // 10)  # Примерно 10 предложений перекрытия
                current_chunk = current_chunk[overlap_start:]
                current_length = sum(len(s.split()) for s in current_chunk)
                current_chunk.append(sentence)
                current_length += sentence_length
        
        if current_chunk:
            chunks.append('. '.join(current_chunk) + '.')
        
        return chunks

    def _postprocess_summary(self, summary: str) -> str:
        """Постобработка суммаризации для улучшения читаемости"""
        sentences = summary.split('. ')
        unique_sentences = []
        seen = set()
        
        for sentence in sentences:
            normalized = ' '.join(sentence.lower().split())
            if normalized not in seen:
                seen.add(normalized)
                unique_sentences.append(sentence)
        
        filtered_sentences = [s for s in unique_sentences if len(s.split()) >= 5]
        processed_summary = '. '.join(filtered_sentences)
        processed_summary = processed_summary.replace('..', '.')
        if processed_summary:
            processed_summary = processed_summary[0].upper() + processed_summary[1:]
            if not processed_summary.endswith('.'):
                processed_summary += '.'
        
        return processed_summary
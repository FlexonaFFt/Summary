import re
import torch 
from transformers import T5ForConditionalGeneration, T5Tokenizer
from typing import Optional, Union
import os
from pdfminer.high_level import extract_text as extract_text_from_pdf
from docx import Document as DocxDocument

class RussianTextSummarizer:
    def __init__(self, model_name="IlyaGusev/rut5_base_sum_gazeta"):
        self.model = T5ForConditionalGeneration.from_pretrained(model_name)
        self.tokenizer = T5Tokenizer.from_pretrained(model_name)
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)
        
    def count_words(self, text: str) -> int:
        """Подсчет слов в тексте (приблизительный)"""
        return len(re.findall(r'\w+', text))
    
    def split_text(self, text: str, max_words: int = 500) -> list[str]:
        """Разделение текста на части по количеству слов"""
        paragraphs = re.split(r'\n\s*\n', text)
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        for paragraph in paragraphs:
            words = re.findall(r'\w+', paragraph)
            word_count = len(words)
            
            if current_word_count + word_count > max_words and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_word_count = 0
                
            current_chunk.append(paragraph)
            current_word_count += word_count
            
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
            
        return chunks
    
    def summarize_chunk(self, text: str, num_words: int = 150, temperature: float = 0.9) -> str:
        """Суммаризация части текста с настройкой по количеству слов"""
        # Эмпирическая формула для соотнесения количества слов и длины вывода
        max_length = min(512, int(num_words * 1.5))
        min_length = max(50, int(num_words * 0.7))
        
        input_ids = self.tokenizer(
            text,
            max_length=512,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        ).to(self.device)
        
        output_ids = self.model.generate(
            input_ids=input_ids["input_ids"],
            attention_mask=input_ids["attention_mask"],
            max_length=max_length,
            min_length=min_length,
            do_sample=True,
            temperature=temperature,
            top_p=0.9,
            early_stopping=True,
            num_beams=5,
            no_repeat_ngram_size=3,
        )
        
        summary = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return summary
    
    def summarize_long_text(self, text: str, target_word_count: int = 300) -> str:
        """Суммаризация длинного текста с контролем количества слов в результате"""
        # Разбиваем текст на части
        chunks = self.split_text(text)
        
        # Суммаризируем каждую часть
        chunk_summaries = []
        for chunk in chunks:
            # Распределяем целевое количество слов между частями
            chunk_word_count = self.count_words(chunk)
            chunk_target = max(50, int(target_word_count * (chunk_word_count / self.count_words(text))))
            
            summary = self.summarize_chunk(chunk, num_words=chunk_target)
            chunk_summaries.append(summary)
        
        # Объединяем суммаризации частей
        combined_summary = " ".join(chunk_summaries)
        
        # Если суммарное количество слов превышает целевое, делаем финальную суммаризацию
        if self.count_words(combined_summary) > target_word_count * 1.2:
            combined_summary = self.summarize_chunk(combined_summary, num_words=target_word_count)
        
        return combined_summary
    
    def read_file(self, file_path: str) -> str:
        """Чтение текста из файла (поддержка PDF, TXT, DOCX)"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Файл не найден: {file_path}")
            
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.pdf':
            return extract_text_from_pdf(file_path)
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif ext == '.docx':
            doc = DocxDocument(file_path)
            return "\n".join([para.text for para in doc.paragraphs])
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {ext}")

def main():
    summarizer = RussianTextSummarizer()
    
    print("Выберите источник текста:")
    print("1 - Ввести текст вручную")
    print("2 - Загрузить из файла")
    choice = input("Ваш выбор (1/2): ")
    
    if choice == '1':
        text = input("Введите текст для суммаризации:\n")
    elif choice == '2':
        file_path = "../service/uploads/00a9b160-977e-4a3e-ac9f-ee632bf9a5f5_extracted.txt"
        text = summarizer.read_file(file_path)
    else:
        print("Неверный выбор")
        return
    
    target_words = int(input("Введите желаемое количество слов в summary (по умолчанию 300): ") or "300")
    
    print("\nСуммаризация...")
    summary = summarizer.summarize_long_text(text, target_word_count=target_words)
    
    print("\nРезультат суммаризации:")
    print(summary)
    print(f"\nКоличество слов в summary: {summarizer.count_words(summary)}")

if __name__ == "__main__":
    main()
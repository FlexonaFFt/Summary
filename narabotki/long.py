import re
import torch
import math
import os
from transformers import T5ForConditionalGeneration, T5Tokenizer
from typing import Dict, List
from pdfminer.high_level import extract_text as extract_text_from_pdf
from docx import Document as DocxDocument


class SmartRussianSummarizer:
    def __init__(self, model_name: str = "IlyaGusev/rut5_base_sum_gazeta"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = T5Tokenizer.from_pretrained(model_name)
        self.model = T5ForConditionalGeneration.from_pretrained(model_name).to(self.device)
        self.sentence_split_regex = re.compile(r'(?<=[.!?…])\s+(?=[А-ЯЁA-Z])')
        
    def count_words(self, text: str) -> int:
        """Точный подсчет слов с учетом русской морфологии"""
        return len(re.findall(r'[а-яёА-ЯЁa-zA-Z0-9-]+', text))
    
    def analyze_text_structure(self, text: str) -> Dict:
        """Анализ структуры текста для оптимального разбиения"""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        sentences = []
        for para in paragraphs:
            sentences.extend(re.split(self.sentence_split_regex, para))
        
        word_counts = [self.count_words(s) for s in sentences]
        total_words = sum(word_counts)
        
        return {
            'paragraph_count': len(paragraphs),
            'sentence_count': len(sentences),
            'avg_sentence_length': sum(word_counts)/len(sentences) if sentences else 0,
            'total_words': total_words,
            'sentences': sentences,
            'paragraphs': paragraphs
        }
    
    def smart_chunking(self, text: str, target_summary_length: int) -> List[str]:
        """Интеллектуальное разбиение текста на чанки"""
        analysis = self.analyze_text_structure(text)
        total_words = analysis['total_words']
        
        # Определяем стратегию разбиения
        if total_words < target_summary_length * 3:
            return [text]  # Не разбиваем короткие тексты
        
        # Эвристика для определения оптимального размера чанка
        avg_chunk_words = min(
            max(target_summary_length * 2, 500),
            total_words // math.ceil(total_words / (target_summary_length * 4))
        )
        
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        # Предпочитаем разбивать по параграфам, но если они слишком большие - по предложениям
        for paragraph in analysis['paragraphs']:
            para_word_count = self.count_words(paragraph)
            
            if para_word_count > avg_chunk_words * 1.5:
                # Разбиваем слишком длинные параграфы на предложения
                sentences = re.split(self.sentence_split_regex, paragraph)
                for sent in sentences:
                    sent_word_count = self.count_words(sent)
                    if current_word_count + sent_word_count > avg_chunk_words and current_chunk:
                        chunks.append(" ".join(current_chunk))
                        current_chunk = []
                        current_word_count = 0
                    current_chunk.append(sent)
                    current_word_count += sent_word_count
            else:
                if current_word_count + para_word_count > avg_chunk_words and current_chunk:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_word_count = 0
                current_chunk.append(paragraph)
                current_word_count += para_word_count
        
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
            
        return chunks
    
    def determine_summary_strategy(self, text: str, target_words: int) -> Dict:
        """Определение оптимальной стратегии суммаризации"""
        analysis = self.analyze_text_structure(text)
        ratio = analysis['total_words'] / target_words if target_words > 0 else 10
        
        strategy = {
            'mode': 'default',
            'temperature': 0.9,
            'length_penalty': 1.5,
            'repetition_penalty': 2.0,
            'num_beams': 4,
            'no_repeat_ngram_size': 3,
            'iterative': False
        }
        
        if ratio > 15:
            strategy.update({
                'mode': 'iterative',
                'iterative': True,
                'temperature': 0.7,
                'length_penalty': 2.0
            })
        elif ratio < 5:
            strategy.update({
                'mode': 'extractive',
                'temperature': 1.2,
                'length_penalty': 0.8,
                'num_beams': 2
            })
        
        if target_words < 50:
            strategy.update({
                'mode': 'short',
                'temperature': 0.7,
                'length_penalty': 0.5,
                'num_beams': 1,
                'no_repeat_ngram_size': 2
            })
        elif target_words > 300:
            strategy.update({
                'mode': 'long',
                'temperature': 1.0,
                'length_penalty': 2.5,
                'num_beams': 6,
                'no_repeat_ngram_size': 4
            })
        
        return strategy
    
    def generate_summary(
        self,
        text: str,
        target_words: int,
        temperature: float = 0.9,
        length_penalty: float = 1.5,
        repetition_penalty: float = 2.0,
        num_beams: int = 4,
        no_repeat_ngram_size: int = 3
    ) -> str:
        """Генерация summary с заданными параметрами"""
        if not text.strip():
            return ""
            
        target_tokens = min(512, int(target_words * 1.8))
        min_tokens = max(20, int(target_tokens * 0.4))
        
        input_ids = self.tokenizer(
            text,
            max_length=1024,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        ).to(self.device)
        
        output_ids = self.model.generate(
            input_ids=input_ids["input_ids"],
            attention_mask=input_ids["attention_mask"],
            max_length=target_tokens,
            min_length=min_tokens,
            do_sample=True,
            temperature=temperature,
            top_p=0.95,
            length_penalty=length_penalty,
            repetition_penalty=repetition_penalty,
            num_beams=num_beams,
            no_repeat_ngram_size=no_repeat_ngram_size,
            early_stopping=True
        )
        
        summary = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return summary
    
    def adjust_summary_length(self, summary: str, target_words: int) -> str:
        """Точная подгонка длины summary"""
        current_words = self.count_words(summary)
        
        if current_words <= target_words * 1.1:  # 10% допуск
            return summary
            
        # Если summary слишком длинное - обрезаем наименее важные предложения
        sentences = re.split(self.sentence_split_regex, summary)
        if len(sentences) <= 1:
            return summary
            
        # Сортируем предложения по длине (сначала самые короткие)
        sentences.sort(key=lambda s: self.count_words(s))
        
        adjusted = []
        word_count = 0
        for sent in sentences:
            sent_words = self.count_words(sent)
            if word_count + sent_words <= target_words or not adjusted:
                adjusted.append(sent)
                word_count += sent_words
            else:
                break
                
        return ' '.join(adjusted)
    
    def summarize_long_text(self, text: str, target_word_count: int = 150) -> str:
        """Интеллектуальная суммаризация с контролем длины"""
        if not text.strip():
            return ""
            
        strategy = self.determine_summary_strategy(text, target_word_count)
        
        if strategy['iterative']:
            # Многоуровневая суммаризация для очень длинных текстов
            chunks = self.smart_chunking(text, target_word_count)
            chunk_summaries = []
            
            for chunk in chunks:
                chunk_target = max(50, target_word_count // len(chunks))
                chunk_summary = self.generate_summary(
                    chunk,
                    chunk_target,
                    temperature=strategy['temperature'],
                    length_penalty=strategy['length_penalty'],
                    repetition_penalty=strategy['repetition_penalty'],
                    num_beams=strategy['num_beams'],
                    no_repeat_ngram_size=strategy['no_repeat_ngram_size']
                )
                chunk_summaries.append(chunk_summary)
            
            combined_text = " ".join(chunk_summaries)
            if self.count_words(combined_text) > target_word_count * 1.5:
                final_summary = self.generate_summary(
                    combined_text,
                    target_word_count,
                    temperature=strategy['temperature'] * 0.9,
                    length_penalty=strategy['length_penalty'] * 1.2
                )
            else:
                final_summary = combined_text
        else:
            # Прямая суммаризация для текстов средней длины
            final_summary = self.generate_summary(
                text,
                target_word_count,
                temperature=strategy['temperature'],
                length_penalty=strategy['length_penalty'],
                repetition_penalty=strategy['repetition_penalty'],
                num_beams=strategy['num_beams'],
                no_repeat_ngram_size=strategy['no_repeat_ngram_size']
            )
        
        # Точная подгонка длины
        final_summary = self.adjust_summary_length(final_summary, target_word_count)
        
        return final_summary
    
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
            return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        else:
            raise ValueError(f"Неподдерживаемый формат файла: {ext}")


def main():
    summarizer = SmartRussianSummarizer()
    
    print("Выберите источник текста:")
    print("1 - Ввести текст вручную")
    print("2 - Загрузить из файла")
    choice = input("Ваш выбор (1/2): ").strip()
    
    if choice == '1':
        print("Введите текст для суммаризации (завершите ввод пустой строкой):")
        lines = []
        while True:
            line = input()
            if not line:
                break
            lines.append(line)
        text = "\n".join(lines)
    elif choice == '2':
        file_path = "../service/uploads/00a9b160-977e-4a3e-ac9f-ee632bf9a5f5_extracted.txt"
        try:
            text = summarizer.read_file(file_path)
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            return
    else:
        print("Неверный выбор")
        return
    
    while True:
        target_words_input = input("Введите желаемое количество слов в summary (по умолчанию 300): ").strip()
        try:
            target_words = int(target_words_input) if target_words_input else 300
            if target_words <= 0:
                raise ValueError
            break
        except ValueError:
            print("Пожалуйста, введите положительное целое число")
    
    print("\nСуммаризация...")
    try:
        summary = summarizer.summarize_long_text(text, target_word_count=target_words)
        
        print("\nРезультат суммаризации:")
        print(summary)
        print(f"\nКоличество слов в summary: {summarizer.count_words(summary)}")
        
        # Сохранение результата
        save = input("\nСохранить результат в файл? (y/n): ").strip().lower()
        if save == 'y':
            output_path = input("Введите путь для сохранения (по умолчанию summary.txt): ").strip()
            output_path = output_path if output_path else "summary.txt"
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(summary)
                print(f"Результат сохранен в {output_path}")
            except Exception as e:
                print(f"Ошибка при сохранении файла: {e}")
    except Exception as e:
        print(f"Произошла ошибка при суммаризации: {e}")


if __name__ == "__main__":
    main()
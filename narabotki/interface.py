from transformers import T5ForConditionalGeneration, T5Tokenizer
import torch

class TextSummarizer:
    def __init__(self, model_path="../final_model"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = T5Tokenizer.from_pretrained(
            "cointegrated/rut5-small", 
            legacy=False  # Отключаем устаревшее поведение
        )
        self.model = T5ForConditionalGeneration.from_pretrained(model_path).to(self.device)
        print(f"Модель загружена на {self.device}")

    def summarize(self, text, max_length=256, min_length=30, variation=0.8):
        """
        variation: коэффициент разнообразия (0.0-1.0)
        """
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
            length_penalty=variation,  # Ключевой параметр!
            no_repeat_ngram_size=3,
            do_sample=True,           # Добавляем случайность
            temperature=0.7,          # Контроль случайности
            top_k=50                  # Ограничиваем словарь
        )
        
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

if __name__ == "__main__":
    # Инициализация суммаризатора
    summarizer = TextSummarizer()
    
    # Пример использования
    sample_text = """В широком смысле кадровая политика - система правил и норм в области работы с кадрами, которые должны быть осознаны и определенным образом сформулированы, приводящая человеческий ресурс в соответствие со стратегией фирмы.
    Данным определением подчеркивается интегрированность сферы управления персоналом в общую деятельность организации, а также факт осознания правил и норм кадровой работы всеми субъектами организации.
    В узком смысле кадровая политика - набор конкретных правил, пожеланий и ограничений во взаимоотношениях работников и организации.
    Под кадровой политикой подразумевается формирование стратегии кадровой работы, установление целей и задач, определение принципов подбора, расстановки и развития персонала, совершенствование форм и методов работы с персоналом в конкретных рыночных условиях на том или ином этапе развития организации.
    Цель кадровой политики - обеспечение оптимального баланса процессов обновления и сохранения численного и качественного состава кадров, его развития в соответствии с потребностями организации, требованиями законодательства, состоянием рынка труда.
    Назначение кадровой политики — своевременно формулировать цели в соответствии со стратегией развития организации, ставить проблемы и задачи, находить способы и организовывать достижение целей."""
    
    summary1 = summarizer.summarize(sample_text, max_length=50)
    summary2 = summarizer.summarize(sample_text, max_length=75)
    summary3 = summarizer.summarize(sample_text)
    print("\nРезультат суммаризации:")
    print(summary1)
    print()
    print(summary2)
    print()
    print(summary3)
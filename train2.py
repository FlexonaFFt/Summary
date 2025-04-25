# Импорт библиотек
from transformers import T5ForConditionalGeneration, T5Tokenizer, Seq2SeqTrainer, Seq2SeqTrainingArguments
from datasets import load_dataset, load_metric
import torch
from torch.utils.data import DataLoader
import numpy as np
from accelerate import Accelerator  # Для ускорения обучения

# Инициализация ускорителя (автоматически использует GPU/TPU если доступно)
accelerator = Accelerator()

# 1. Загрузка модели и токенизатора
model_name = "cointegrated/rut5-base-sum"
tokenizer = T5Tokenizer.from_pretrained(model_name)
model = T5ForConditionalGeneration.from_pretrained(model_name)

# 2. Загрузка и подготовка данных
dataset = load_dataset("IlyaGusev/gazeta", split="train[:20%]")  # Берем 20% для примера

def preprocess_function(examples):
    inputs = ["summarize: " + doc for doc in examples["text"]]
    model_inputs = tokenizer(
        inputs,
        max_length=512,
        truncation=True,
        padding="max_length"
    )
    
    with tokenizer.as_target_tokenizer():
        labels = tokenizer(
            examples["summary"],
            max_length=128,
            truncation=True,
            padding="max_length"
        )
    
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

tokenized_dataset = dataset.map(preprocess_function, batched=True)
tokenized_dataset = tokenized_dataset.train_test_split(test_size=0.1)

# 3. Метрики для оценки
rouge = load_metric("rouge")

def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    decoded_preds = tokenizer.batch_decode(predictions, skip_special_tokens=True)
    
    labels = np.where(labels != -100, labels, tokenizer.pad_token_id)
    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
    
    result = rouge.compute(
        predictions=decoded_preds,
        references=decoded_labels,
        use_stemmer=True
    )
    
    return {
        "rouge1": round(result["rouge1"].mid.fmeasure * 100, 4),
        "rouge2": round(result["rouge2"].mid.fmeasure * 100, 4),
        "rougeL": round(result["rougeL"].mid.fmeasure * 100, 4),
    }

# 4. Оптимизированные параметры обучения
training_args = Seq2SeqTrainingArguments(
    output_dir="./results",
    per_device_train_batch_size=8,  # Увеличиваем batch size
    per_device_eval_batch_size=8,
    gradient_accumulation_steps=2,  # Аккумуляция градиентов
    learning_rate=3e-5,
    num_train_epochs=2,  # Уменьшаем эпохи для скорости
    warmup_steps=500,
    weight_decay=0.01,
    logging_dir="./logs",
    logging_steps=100,
    eval_steps=500,
    save_steps=1000,
    evaluation_strategy="steps",
    predict_with_generate=True,
    fp16=True if accelerator.device.type == "cuda" else False,  # Автовыбор
    dataloader_num_workers=4,  # Параллельная загрузка данных
    report_to="tensorboard",
    load_best_model_at_end=True,
)

# 5. Инициализация Trainer
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["test"],
    compute_metrics=compute_metrics,
)

# 6. Ускорение обучения с помощью Accelerate
model, trainer = accelerator.prepare(model, trainer)

# 7. Запуск обучения
print("Начало обучения...")
trainer.train()

# 8. Сохранение модели
accelerator.wait_for_everyone()
if accelerator.is_main_process:
    trainer.save_model("./final_summarization_model")
    tokenizer.save_pretrained("./final_summarization_model")
    print("Модель сохранена в './final_summarization_model'")

# 9. Функция для инференса
def summarize(text, model_path="./final_summarization_model", max_length=100):
    # Загрузка модели (если не передана)
    if isinstance(model_path, str):
        model = T5ForConditionalGeneration.from_pretrained(model_path)
        tokenizer = T5Tokenizer.from_pretrained(model_path)
        model.to(accelerator.device)
    
    inputs = tokenizer(
        f"summarize: {text}",
        return_tensors="pt",
        max_length=512,
        truncation=True,
        padding="max_length"
    ).to(accelerator.device)
    
    outputs = model.generate(
        **inputs,
        max_length=max_length,
        num_beams=5,
        early_stopping=True,
        do_sample=True,
        temperature=0.9,
        top_k=50,
        top_p=0.95,
    )
    
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# Пример использования
if accelerator.is_main_process:
    sample_text = "В Москве состоялось открытие нового IT-парка..."  # Ваш текст
    print("\nРезультат суммаризации:")
    print(summarize(sample_text))
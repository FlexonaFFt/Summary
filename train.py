from transformers import (
    AutoTokenizer,
    AutoModelForSeq2SeqLM,
    DataCollatorForSeq2Seq,
    Seq2SeqTrainingArguments,
    Seq2SeqTrainer,
    TrainerCallback
)

from datasets import load_dataset
from rouge_score import rouge_scorer

import os
os.environ["WANDB_DISABLED"] = "true"

MODEL_NAME = "google/mt5-small"
DATASET_NAME = "IlyaGusev/gazeta"
OUTPUT_DIR = "./saved_model"

dataset = load_dataset(DATASET_NAME)
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

def preprocess_function(examples):
    inputs = ["summarize: " + text for text in examples["text"]]
    model_inputs = tokenizer(
        inputs,
        max_length=512,  
        truncation=True,
        padding="max_length",  
        return_tensors="pt"   
    )
    
    labels = tokenizer(
        examples["summary"],
        max_length=256,  
        truncation=True,
        padding="max_length", 
        return_tensors="pt"
    )
    
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

tokenized_dataset = dataset.map(preprocess_function, batched=True)

model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
training_args = Seq2SeqTrainingArguments(
    output_dir=OUTPUT_DIR,
    per_device_train_batch_size=52,
    per_device_eval_batch_size=52,
    num_train_epochs=3,
    save_strategy="epoch",
    eval_strategy="epoch",
    logging_dir="./logs",
    learning_rate=5e-5, 
    weight_decay=0.01,
    predict_with_generate=True,
    report_to="none",
    warmup_steps=500
)

class LoggingCallback(TrainerCallback):
    def on_log(self, args, state, control, logs=None, **kwargs):
        if state.is_local_process_zero:
            print(f"\nШаг {state.global_step} / {state.max_steps}")
            print(f"Loss: {logs.get('loss', 'N/A'):.4f}")
            print(f"Validation Loss: {logs.get('eval_loss', 'N/A'):.4f}")
            if 'rougeL' in logs:
                print(f"Rouge-L: {logs['rougeL']:.4f}")

def compute_metrics(eval_pred):
    predictions, labels = eval_pred
    decoded_preds = tokenizer.batch_decode(predictions, skip_special_tokens=True)
    decoded_labels = tokenizer.batch_decode(labels, skip_special_tokens=True)
    
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'])
    scores = [scorer.score(ref, pred) for ref, pred in zip(decoded_labels, decoded_preds)]
    
    return {
        'rouge1': sum(s['rouge1'].fmeasure for s in scores) / len(scores),
        'rouge2': sum(s['rouge2'].fmeasure for s in scores) / len(scores),
        'rougeL': sum(s['rougeL'].fmeasure for s in scores) / len(scores),
    }

data_collator = DataCollatorForSeq2Seq(
    tokenizer,
    model=model,
    padding=True,
    max_length=512,  
    pad_to_multiple_of=8  
)

trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset["train"],
    eval_dataset=tokenized_dataset["validation"],
    tokenizer=tokenizer,
    data_collator=data_collator,
    compute_metrics=compute_metrics,
    callbacks=[LoggingCallback()]
)

print("\n=== Конфигурация обучения ===")
print(f"Модель: {MODEL_NAME}")
print(f"Датасет: {DATASET_NAME}")
print(f"Размер батча: {training_args.per_device_train_batch_size}")
print(f"Эпохи: {training_args.num_train_epochs}")
print(f"Learning rate: {training_args.learning_rate}")
print(f"Устройство: {training_args.device}")

print("\n=== Информация о данных ===")
print(f"Обучающие примеры: {len(tokenized_dataset['train'])}")
print(f"Валидационные примеры: {len(tokenized_dataset['validation'])}")

print("\n=== Начало обучения ===")
train_results = trainer.train()

print("\n=== Обучение завершено ===")
print(f"Финальный loss: {train_results.metrics['train_loss']:.4f}")
print(f"Общее время обучения: {train_results.metrics['train_runtime']:.2f} сек")
print(f"Скорость обучения: {train_results.metrics['train_samples_per_second']:.2f} примеров/сек")

trainer.save_model(OUTPUT_DIR)
tokenizer.save_pretrained(OUTPUT_DIR)
print(f"\nМодель сохранена в {OUTPUT_DIR}")
print(f"Размер модели: {sum(p.numel() for p in model.parameters())/1e6:.1f}M параметров")
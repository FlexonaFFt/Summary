from transformers import TrainerCallback 

class MemoryOptimizationCallback(TrainerCallback):  
    def on_step_end(self, args, state, control, **kwargs):
        torch.cuda.empty_cache()
        gc.collect()
    
    def on_evaluate(self, args, state, control, **kwargs):
        torch.cuda.empty_cache()
        gc.collect()

from transformers import T5ForConditionalGeneration, T5Tokenizer, Seq2SeqTrainer, Seq2SeqTrainingArguments, TrainerCallback
from datasets import load_dataset
import evaluate
import torch
import numpy as np
from accelerate import Accelerator
import gc

torch.cuda.empty_cache()
gc.collect()
accelerator = Accelerator()


model_name = "cointegrated/rut5-small"
tokenizer = T5Tokenizer.from_pretrained(model_name)
model = T5ForConditionalGeneration.from_pretrained(model_name)
training_args = Seq2SeqTrainingArguments(
    output_dir="./results",
    per_device_train_batch_size=64,
    per_device_eval_batch_size=16,
    gradient_accumulation_steps=1,
    learning_rate=3e-5,
    num_train_epochs=5,  
    fp16=False,
    gradient_checkpointing=True,
    optim="adamw_torch",
    eval_strategy="no",
    save_strategy="steps",
    save_steps=500,
    logging_steps=50,
    report_to="none",
    dataloader_pin_memory=False,
)

dataset = load_dataset("IlyaGusev/gazeta", split="train[:50%]")  

def preprocess_function(examples):
    inputs = ["summarize: " + doc for doc in examples["text"]]
    return tokenizer(
        text=inputs,
        text_target=examples["summary"],
        max_length=128,  
        truncation=True,
        padding="max_length"
    )

tokenized_dataset = dataset.map(
    preprocess_function,
    batched=True,
    batch_size=4,
    remove_columns=dataset.column_names
)

class MemoryCallback(TrainerCallback):
    def on_step_end(self, args, state, control, **kwargs):
        torch.cuda.empty_cache()
        gc.collect()

trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    callbacks=[MemoryCallback()],  
)

print("Начало обучения...")
try:
    trainer.train()
except Exception as e:
    print(f"Ошибка обучения: {e}")
finally:
    torch.cuda.empty_cache()
    gc.collect()

if accelerator.is_main_process:
    trainer.save_model("../final_model")
    print("Модель сохранена")
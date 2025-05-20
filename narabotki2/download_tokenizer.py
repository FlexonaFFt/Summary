from transformers import T5Tokenizer
model_name = "cointegrated/rut5-small"
output_path = "../final_model"
tokenizer = T5Tokenizer.from_pretrained(model_name)
tokenizer.save_pretrained(output_path)

print(f"Токенизатор успешно сохранен в {output_path}")
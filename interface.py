from transformers import pipeline

MODEL_PATH = "./saved_model"

def summarize(text):
    summarizer = pipeline(
        "summarization",
        model=MODEL_PATH,
        tokenizer="google/mt5-small"
    )
    return summarizer(text, max_length=130, min_length=30)[0]["summary_text"]

if __name__ == "__main__":
    example_text = "Ваш текст для суммаризации здесь..."
    print("Результат:", summarize(example_text))
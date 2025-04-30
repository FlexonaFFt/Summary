from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
import tempfile
from schemas import SummarizationRequest, SummarizationResponse
from functions import summarize_text, process_file, calculate_metrics

app = FastAPI(
    title="Word-Based Text Summarization API",
    description="API для суммаризации текстов с контролем длины в словах",
    version="2.0.0"
)

@app.post("/summarize/text", response_model=SummarizationResponse)
async def summarize_from_text(request: SummarizationRequest):
    """Суммаризирует текст с контролем длины в словах"""
    if not request.text and not request.file_path:
        raise HTTPException(
            status_code=400,
            detail="Необходимо предоставить текст или путь к файлу"
        )
    
    if request.text:
        try:
            summary = summarize_text(
                text=request.text,
                max_words=request.max_words,
                min_words=request.min_words,
                do_sample=request.do_sample
            )
            metrics = calculate_metrics(
                original=request.text,
                summary=summary,
                request_params={
                    "max_words": request.max_words,
                    "min_words": request.min_words
                }
            )
            return SummarizationResponse(
                summary=summary,
                original_length=metrics["original_length"],
                summary_length=metrics["summary_length"],
                compression_ratio=metrics["compression_ratio"],
                requested_length=metrics["requested_length"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.post("/summarize/file", response_model=SummarizationResponse)
async def summarize_from_file(
    file: UploadFile = File(...),
    max_words: int = 150,
    min_words: int = 50,
    do_sample: bool = False
):
    """Суммаризирует текст из файла с контролем длины в словах"""
    if not file.filename.lower().endswith('.txt'):
        raise HTTPException(
            status_code=400,
            detail="Поддерживаются только текстовые файлы (.txt)"
        )
    
    temp_file_path = None
    try:
        # Создаем временный файл
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Обрабатываем файл
        original_text, summary = process_file(
            temp_file_path,
            max_words=max_words,
            min_words=min_words,
            do_sample=do_sample
        )
        
        metrics = calculate_metrics(
            original=original_text,
            summary=summary,
            request_params={
                "max_words": max_words,
                "min_words": min_words
            }
        )
        return SummarizationResponse(
            summary=summary,
            original_length=metrics["original_length"],
            summary_length=metrics["summary_length"],
            compression_ratio=metrics["compression_ratio"],
            requested_length=metrics["requested_length"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)

@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса"""
    return {
        "status": "ok",
        "details": {
            "model_loaded": _model is not None if '_model' in globals() else False,
            "service": "word-based summarization"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi import Form 
from typing import Optional
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
async def api_summarize_file(
    file: UploadFile = File(...),
    max_words: int = Form(150),
    min_words: int = Form(50),
    do_sample: bool = Form(False),
    length_penalty: float = Form(0.8),
    num_beams: int = Form(4),
    no_repeat_ngram_size: int = Form(2),
    temperature: Optional[float] = Form(None)
):
    if not file.filename.lower().endswith('.txt'):
        raise HTTPException(400, "Только .txt файлы поддерживаются")
    
    temp_path = None
    try:
        # Читаем содержимое файла напрямую без временного файла
        content = await file.read()
        text = content.decode('utf-8')
        
        summary = summarize_text(
            text=text,
            max_words=max_words,
            min_words=min_words,
            do_sample=do_sample,
            length_penalty=length_penalty,
            num_beams=num_beams,
            no_repeat_ngram_size=no_repeat_ngram_size,
            temperature=temperature
        )
        
        metrics = calculate_metrics(
            original=text,
            summary=summary,
            params={
                'max_words': max_words,
                'min_words': min_words,
                'length_penalty': length_penalty,
                'num_beams': num_beams,
                'no_repeat_ngram_size': no_repeat_ngram_size,
                'temperature': temperature
            }
        )
        
        return SummarizationResponse(**metrics)
    
    except UnicodeDecodeError:
        raise HTTPException(400, "Ошибка декодирования файла. Убедитесь, что файл в UTF-8")
    except Exception as e:
        raise HTTPException(500, f"Ошибка обработки файла: {str(e)}")

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
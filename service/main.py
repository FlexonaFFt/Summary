import os
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from functions import (
    generate_file_id,
    extract_text_from_file,
    save_extracted_text,
    get_text_by_file_id,
    TextSummarizer
)
from schemas import UploadResponse, SummarizeResponse, SummarizationRequest

app = FastAPI(title="Text Summarization API")
UPLOAD_DIR = "uploads"
summarizer = TextSummarizer()

@app.post("/upload/", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Ограничение размера файла (например, 15 МБ)
    max_file_size = 15 * 1024 * 1024  # 15 MB
    file_size = 0
    for chunk in file.file:
        file_size += len(chunk)
        if file_size > max_file_size:
            raise HTTPException(status_code=400, detail="File size exceeds 10 MB limit")
    file.file.seek(0)  # Сбросить указатель файла после подсчета размера
    
    # Проверка поддерживаемых расширений
    allowed_extensions = [".txt", ".md", ".csv", ".docx", ".pdf"]
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")
    
    try:
        file_id = generate_file_id()
        extracted_text = extract_text_from_file(file)
        if extracted_text.startswith("Error"):
            raise HTTPException(status_code=400, detail=extracted_text)
        text_file_path = save_extracted_text(extracted_text, file_id, UPLOAD_DIR)
        
        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            extracted_text=extracted_text,
            success=True,
            message="File uploaded and processed successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/")
async def root():
    return {"message": "Text Summarization API is running"}

@app.get("/summarize/{file_id}", response_model=SummarizeResponse)
async def summarize_file(file_id: str, max_length: int = 150):
    try:
        text = get_text_by_file_id(file_id, UPLOAD_DIR)
        summary = summarizer.summarize(text, max_length=max_length)
        
        return SummarizeResponse(
            file_id=file_id,
            summary=summary,
            success=True,
            message="Text successfully summarized"
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error summarizing text: {str(e)}")

@app.post("/summarize/long/{file_id}")
async def summarize_long_file(file_id: str):

    try:
        text = get_text_by_file_id(file_id, UPLOAD_DIR)
        summary = summarizer.summarize_long_text(
            text=text,
            max_length=256,
            min_length=30
        )
        
        return {
            "file_id": file_id,
            "summary": summary,
            "success": True
        }
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"File with ID {file_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Summarization error: {str(e)}"
        )

@app.post("/summarize/long")
async def summarize_long_text(request: SummarizationRequest):
    try:
        summary = summarizer.summarize_long_text(
            text=request.text,
            max_length=request.max_length,
            min_length=request.min_length
        )
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    uvicorn.run(app, host="0.0.0.0", port=8000)
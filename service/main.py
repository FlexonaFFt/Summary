import os
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
    
    try:
        file_id = generate_file_id()
        extracted_text = extract_text_from_file(file)
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
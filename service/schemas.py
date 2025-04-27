from pydantic import BaseModel
from enum import Enum

class UploadResponse(BaseModel):
    file_id: str
    filename: str
    extracted_text: str
    success: bool
    message: str = None

class SummarizeResponse(BaseModel):
    file_id: str
    summary: str
    success: bool
    message: str = None

class SummarizationRequest(BaseModel):
    text: str
    max_length: int = 256
    min_length: int = 30
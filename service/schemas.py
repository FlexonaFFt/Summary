from pydantic import BaseModel, Field
from typing import Optional

class SummarizationRequest(BaseModel):
    text: Optional[str] = None
    file_path: Optional[str] = None
    max_words: int = Field(150, gt=10, le=300, description="Максимальное количество слов в суммаризации")
    min_words: int = Field(50, gt=5, le=150, description="Минимальное количество слов в суммаризации")
    do_sample: bool = False

class SummarizationResponse(BaseModel):
    summary: str
    original_length: int = Field(..., description="Количество слов в оригинальном тексте")
    summary_length: int = Field(..., description="Количество слов в суммаризации")
    compression_ratio: float = Field(..., description="Коэффициент сжатия (original_length/summary_length)")
    requested_length: dict = Field(..., description="Запрошенные параметры длины")
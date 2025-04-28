import pytest
import io
import os 
import sys 

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app
from schemas import UploadResponse
from pathlib import Path
from fastapi import UploadFile

# Создаем тестовый клиент для FastAPI
client = TestClient(app)

# Фикстура для временной директории uploads
@pytest.fixture
def upload_dir(tmp_path):
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return upload_dir

# Тест для корневого маршрута
def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Text Summarization API is running"}

# Тест для успешной загрузки текстового файла
def test_upload_text_file(upload_dir):
    with patch("main.UPLOAD_DIR", str(upload_dir)):
        file_content = b"This is a test file content."
        with patch("main.generate_file_id", return_value="test-id"):
            with patch("main.extract_text_from_file", return_value="This is a test file content."):
                with patch("main.save_extracted_text", return_value=str(upload_dir / "test-id_extracted.txt")):
                    response = client.post(
                        "/upload/",
                        files={"file": ("test.txt", file_content, "text/plain")}
                    )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["file_id"] == "test-id"
        assert response_data["filename"] == "test.txt"
        assert response_data["extracted_text"] == "This is a test file content."
        assert response_data["success"] is True
        assert response_data["message"] == "File uploaded and processed successfully"

# Тест для загрузки PDF-файла
def test_upload_pdf_file(upload_dir):
    with patch("main.UPLOAD_DIR", str(upload_dir)):
        file_content = b"%PDF-1.4 fake PDF content"
        with patch("main.generate_file_id", return_value="pdf-id"):
            with patch("main.extract_text_from_file", return_value="Extracted PDF text"):
                with patch("main.save_extracted_text", return_value=str(upload_dir / "pdf-id_extracted.txt")):
                    response = client.post(
                        "/upload/",
                        files={"file": ("test.pdf", file_content, "application/pdf")}
                    )
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["file_id"] == "pdf-id"
        assert response_data["filename"] == "test.pdf"
        assert response_data["extracted_text"] == "Extracted PDF text"
        assert response_data["success"] is True

# Тест для ошибки при загрузке неподдерживаемого файла
def test_upload_unsupported_file():
    file_content = b"Some content"
    response = client.post(
        "/upload/",
        files={"file": ("test.xyz", file_content, "application/octet-stream")}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported file type: .xyz"

# Тест для ошибки при отсутствии файла
def test_upload_no_file():
    response = client.post("/upload/")
    assert response.status_code == 400
    assert response.json()["detail"] == "No file provided"

# Тест для успешной суммаризации
def test_summarize_file(upload_dir):
    with patch("main.UPLOAD_DIR", str(upload_dir)):
        file_path = upload_dir / "test-id_extracted.txt"
        file_path.write_text("This is a test file content for summarization.")
        
        with patch("main.get_text_by_file_id", return_value="This is a test file content for summarization."):
            with patch("main.summarizer.summarize", return_value="Test summary"):
                response = client.get("/summarize/test-id?max_length=100")
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["file_id"] == "test-id"
        assert response_data["summary"] == "Test summary"
        assert response_data["success"] is True
        assert response_data["message"] == "Text successfully summarized"

# Тест для ошибки при суммаризации несуществующего файла
def test_summarize_nonexistent_file(upload_dir):
    with patch("main.UPLOAD_DIR", str(upload_dir)):
        response = client.get("/summarize/nonexistent-id")
        assert response.status_code == 404
        assert response.json()["detail"] == "File with ID nonexistent-id not found"

# Тест для превышения размера файла
def test_upload_file_too_large():
    file_content = b"A" * (11 * 1024 * 1024)  # 11 MB
    response = client.post(
        "/upload/",
        files={"file": ("large.txt", file_content, "text/plain")}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "File size exceeds 15 MB limit"
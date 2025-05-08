from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form
from pydantic import BaseModel
import uuid
from aiokafka import AIOKafkaProducer
import io, docx  
import PyPDF2 
import pytesseract
import aioredis
import asyncio, os
from loguru import logger
from contextlib import asynccontextmanager
from pdf2image import convert_from_bytes
from fastapi.middleware.cors import CORSMiddleware

redis = None
producer = None

class TextRequest(BaseModel):
    text: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis, producer
    
    connected = False
    while not connected:
        try:
            bootstrap_servers = os.getenv("BOOTSTRAP_SERVERS", "localhost:9092")  # Изменено с kafka:9092 на localhost:9092
            redis = aioredis.from_url("redis://localhost")  # Изменено с redis://redis на redis://localhost
            producer = AIOKafkaProducer(bootstrap_servers=bootstrap_servers)
            await producer.start()
            log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
            os.makedirs(log_dir, exist_ok=True)
            logger.add(os.path.join(log_dir, "app.log"), rotation="1 day")
            logger.info("FastAPI запущен")
            connected = True
        except Exception as e:
            print(f"❌ Redis or Kafka is not available yet. Retrying in 5s... Error: {e}")
            await asyncio.sleep(5)
    
    yield  
    
    if producer:
        await producer.stop()
    logger.info("FastAPI остановлен")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/summarize")
async def summarize(data: TextRequest):
    request_id = str(uuid.uuid4())
    await redis.set(request_id, "processing")
    await producer.send_and_wait("summarize", f"{request_id}|{data.text}".encode())
    return {"request_id": request_id}

@app.get("/status/{request_id}")
async def check_status(request_id: str):
    result = await redis.get(request_id)
    if result:
        result = result.decode()
        if result != "processing":
            return {"status": "done", "summary": result}
        else:
            return {"status": "processing"}
    return {"status": "not_found"}

@app.post("/summarize-file")
async def summarize_file(file: UploadFile = File(...)):
    try:
        text = await extract_text(file)
        
        if not text:
            return {"error": "Не удалось извлечь текст из файла"}
        
        request_id = str(uuid.uuid4())
        await redis.set(request_id, "processing")
        await producer.send_and_wait("summarize", f"{request_id}|{text}".encode())
        
        logger.info(f"Файл {file.filename} отправлен на суммаризацию, ID={request_id}")
        return {"request_id": request_id, "filename": file.filename}
    
    except Exception as e:
        logger.error(f"Ошибка при обработке файла: {e}")
        return {"error": f"Ошибка при обработке файла: {str(e)}"}

@app.post("/ask-question")
async def ask_question(file: UploadFile = File(...), question: str = Form(...)):
    try:
        text = await extract_text(file)
        
        if not text:
            return {"error": "Не удалось извлечь текст из файла"}
        
        request_id = str(uuid.uuid4())
        await redis.set(request_id, "processing")
        await producer.send_and_wait("question", f"{request_id}|{text}|{question}".encode())
        
        logger.info(f"Вопрос к файлу {file.filename} отправлен, ID={request_id}")
        return {"request_id": request_id, "filename": file.filename}
    
    except Exception as e:
        logger.error(f"Ошибка при обработке вопроса к файлу: {e}")
        return {"error": f"Ошибка при обработке вопроса к файлу: {str(e)}"}


# Функции для извлечения текста из файлов 
async def extract_text_from_pdf(file_content):
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            text += pdf_reader.pages[page_num].extract_text()
        
        if not text.strip():
            logger.info("Применение OCR для PDF файла")
            images = convert_from_bytes(file_content)
            text = ""
            for image in images:
                text += pytesseract.image_to_string(image, lang='rus+eng')
        
        return text
    except Exception as e:
        logger.error(f"Ошибка при извлечении текста из PDF: {e}")
        return ""

async def extract_text_from_docx(file_content):
    try:
        doc = docx.Document(io.BytesIO(file_content))
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text
    except Exception as e:
        logger.error(f"Ошибка при извлечении текста из DOCX: {e}")
        return ""

async def extract_text_from_txt(file_content):
    try:
        return file_content.decode('utf-8')
    except UnicodeDecodeError:
        try:
            return file_content.decode('cp1251')  
        except Exception as e:
            logger.error(f"Ошибка при декодировании TXT файла: {e}")
            return ""
    except Exception as e:
        logger.error(f"Ошибка при извлечении текста из TXT: {e}")
        return ""

async def extract_text(file: UploadFile):
    content = await file.read()
    file_extension = os.path.splitext(file.filename)[1].lower()
    
    if file_extension == '.pdf':
        return await extract_text_from_pdf(content)
    elif file_extension == '.docx':
        return await extract_text_from_docx(content)
    elif file_extension == '.txt':
        return await extract_text_from_txt(content)
    else:
        logger.error(f"Неподдерживаемый формат файла: {file_extension}")
        return ""
import asyncio
import aiohttp
import hashlib
import os
import aiofiles
import aioredis
import uuid
from loguru import logger
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery


API_TOKEN = os.getenv("BOT_TOKEN")
FASTAPI_URL = os.getenv("FASTAPI_URL", "http://fastapi:8000")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis")
MAX_REQUESTS_PER_MIN = 5

qa_mode_users = {}
user_last_summary_file = {}

logger.add("/var/log/fastapi/bot.log", rotation="1 day")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

redis = None

menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Суммаризация текста")],
        [KeyboardButton(text="📄 Суммаризация файла")],
    ],
    resize_keyboard=True
)

def get_ask_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❓ Задать вопрос по тексту", callback_data="enter_qa_mode")]
    ])

def get_exit_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚪 Выйти из режима вопросов", callback_data="exit_qa_mode")]
    ])


@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer(
        "Привет! Я бот, который умеет:\n"
        "📌 Суммаризировать текст или файл (PDF, DOCX, TXT)\n"
        "📌 Отвечать на вопросы по файлу\n\n"
        "Выбери команду ниже 👇",
        reply_markup=menu_kb
    )

@dp.message(lambda m: m.text == "📝 Суммаризация текста")
async def summarize_text_handler(message: Message):
    await message.answer("Отправь мне текст для суммаризации.")

@dp.message(lambda m: m.text == "📄 Суммаризация файла")
async def summarize_file_prompt(message: Message):
    await message.answer("Пришли мне PDF/DOCX/TXT файл для суммаризации.")

@dp.message(lambda m: m.text == "❓ Задать вопрос по файлу")
async def ask_question_prompt(message: Message):
    await message.answer("Сначала пришли файл, затем в следующем сообщении — вопрос.")

async def is_limited(user_id: int) -> bool:
    key = f"user:{user_id}:requests"
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, 60)
    return current > MAX_REQUESTS_PER_MIN

@dp.message(lambda m: m.text and not m.document)
async def handle_text(message: Message):
    user_id = message.from_user.id

    if await is_limited(user_id):
        await message.answer("⏳ Вы превысили лимит: 5 запросов в минуту. Пожалуйста, подождите.")
        return

    if qa_mode_users.get(user_id):
        file = user_last_summary_file.get(user_id)
        if not file:
            await message.answer("❌ Нет загруженного файла для вопросов.")
            return

        doc = await bot.download(file)
        tmp_path = f"/tmp/{uuid.uuid4()}_{file.file_name}"
        async with aiofiles.open(tmp_path, "wb") as f:
            await f.write(doc.read())

        async with aiohttp.ClientSession() as session:
            with open(tmp_path, "rb") as f:
                data = aiohttp.FormData()
                data.add_field("file", f, filename=file.file_name, content_type=file.mime_type)
                data.add_field("question", message.text)
                async with session.post(f"{FASTAPI_URL}/ask-question", data=data) as resp:
                    result = await resp.json()

        os.remove(tmp_path)

        if "error" in result:
            await message.answer(f"❌ Ошибка: {result['error']}")
            return

        request_id = result.get("request_id")
        await message.answer("⌛ Выполняется поиск ответа на вопрос...")
        await wait_for_answer(message, request_id)
        return

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{FASTAPI_URL}/summarize", json={"text": message.text}) as resp:
            data = await resp.json()
            request_id = data.get("request_id")

    await message.answer("⌛ Выполняется суммаризация...")
    await wait_for_result(message, request_id)


async def get_file_hash(file: types.Document) -> str:
    file_obj = await bot.download(file)
    hasher = hashlib.sha256()
    while chunk := file_obj.read(8192):
        hasher.update(chunk)
    return hasher.hexdigest()

@dp.message(lambda m: m.document)
async def handle_file(message: Message):
    if await is_limited(message.from_user.id):
        await message.answer("⏳ Вы превысили лимит: 5 запросов в минуту. Пожалуйста, подождите.")
        return

    file = message.document
    hash_key = f"filecache:{await get_file_hash(file)}"

    cached_summary = await redis.get(hash_key)
    if cached_summary:
        await message.answer("✅ Результат найден в кэше:\n\n" + cached_summary.decode())
        return

    doc = await bot.download(file)
    tmp_path = f"/tmp/{uuid.uuid4()}_{file.file_name}"
    async with aiofiles.open(tmp_path, "wb") as f:
        await f.write(doc.read())

    async with aiohttp.ClientSession() as session:
        with open(tmp_path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field("file", f, filename=file.file_name, content_type=file.mime_type)
            async with session.post(f"{FASTAPI_URL}/summarize-file", data=data) as resp:
                result = await resp.json()

    qa_mode_users.pop(message.from_user.id, None)
    os.remove(tmp_path)

    if "error" in result:
        await message.answer(f"❌ Ошибка: {result['error']}")
        return

    request_id = result.get("request_id")
    await message.answer("⌛ Файл отправлен, ждём результат...")
    await wait_for_result(message, request_id, cache_key=hash_key)

async def wait_for_result(message: Message, request_id: str, cache_key: str = None):
    for _ in range(120):
        await asyncio.sleep(2)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{FASTAPI_URL}/status/{request_id}") as resp:
                result = await resp.json()
        if result.get("status") == "done":
            summary = result.get("summary")
            if cache_key:
                await redis.set(cache_key, summary)
            # Сохраняем последний файл
            if message.document:
                user_last_summary_file[message.from_user.id] = message.document
            await message.answer(f"✅ Готово:\n\n{summary}", reply_markup=get_ask_button())
            return

    await message.answer("⚠️ Время ожидания истекло. Повторите запрос позже.")

async def wait_for_answer(message: Message, request_id: str):
    for _ in range(60):
        await asyncio.sleep(2)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{FASTAPI_URL}/status/{request_id}") as resp:
                result = await resp.json()
        if result.get("status") == "done":
            answer = result.get("summary")  
            await message.answer(f"📌 Ответ:\n\n{answer}", reply_markup=get_exit_button())
            return
    await message.answer("⚠️ Время ожидания истекло. Попробуй позже.")

@dp.callback_query(lambda c: c.data == "enter_qa_mode")
async def enter_qa_mode(callback: CallbackQuery):
    qa_mode_users[callback.from_user.id] = True
    await callback.message.answer("Ты в режиме вопросов. Задай вопрос по документу.", reply_markup=get_exit_button())
    await callback.answer()

@dp.callback_query(lambda c: c.data == "exit_qa_mode")
async def exit_qa_mode(callback: CallbackQuery):
    qa_mode_users.pop(callback.from_user.id, None)
    user_last_summary_file.pop(callback.from_user.id, None)
    await callback.message.answer("Вы вышли из режима вопросов.", reply_markup=menu_kb)
    await callback.answer()



async def main():
    global redis
    redis = await aioredis.from_url(REDIS_URL)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
import aiohttp
from loguru import logger
import os

API_TOKEN = os.getenv("BOT_TOKEN")
logger.add("/var/log/fastapi/bot.log", rotation="1 day")

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Привет!")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())


# @dp.message_handler()
# async def summarize_text(message: types.Message):
#     async with aiohttp.ClientSession() as session:
#         async with session.post("http://fastapi:8000/summarize", json={"text": message.text}) as resp:
#             data = await resp.json()
#             request_id = data["request_id"]

#         for _ in range(10):
#             await asyncio.sleep(2)
#             async with session.get(f"http://fastapi:8000/status/{request_id}") as status:
#                 result = await status.json()
#                 if result["status"] == "done":
#                     await message.answer(result["summary"])
#                     return

#         await message.answer("Обработка занимает слишком много времени")

# if __name__ == "__main__":
#     executor.start_polling(dp, skip_updates=True)
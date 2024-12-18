import asyncio

from aiogram import Bot, Dispatcher

from app.handlers import router
from database.models import async_main

from config import TOKEN


bot = Bot(TOKEN)
dp = Dispatcher()


async def main():
    await async_main()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Работа завершена")




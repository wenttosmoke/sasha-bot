import asyncio
import random
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# === Настройки ===
API_TOKEN = os.getenv("API_TOKEN")
USER_ID = int(os.getenv("USER_ID")) # ID пользователя, которому бот будет отправлять сообщения
GROUP_ID = int(os.getenv("GROUP_ID"))

WEBHOOK_HOST = "https://sasha-bot-lwjs.onrender.com"  # 🌐 Укажи свой домен (https обязательно!)
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# === Объекты с данными ===
sendToSasha = {

    "loveMessages":{
        "texts":[
            "привет, солнце, очень скучаю по тебе. надеюсь тёма тебя не терроризирует😼",
            "если ты ещё не кушала, то быстро, вперёд. хорошее начало или завершение дня. не бери на себя много. ты большая умничка❤️",
            "ДА ПОЧЕМУ ТЫ ТАКОЙ КОТИК, АОАЦГАЦГАОЦАОЦГШ"
        ],
        "withPhoto":[0, 1],
        "photos": [
            "img/love/1.jpg",
            "img/love/2.jpg",
            "img/love/3.jpg"
        ],
        "withSticker":[0, 1],
        "stickers": [
            "CAACAgIAAxkBAAMqaP4yLe6eCpv3MMdcWnz9yL6V-PUAAoMQAAIxr_BJtXsp4sjpYTw2BA",
            "CAACAgIAAxkBAAMsaP4yPGqu7-UsBzNyf0tfnz0Kd5cAAugSAAJSe-hIcGEwWdFvpbY2BA",
            "CAACAgIAAxkBAAMwaP4ypZlMlliVzM9UwGRjW83k4CkAAi4TAAJjJvlLmSS4X7Q-mfs2BA",
            "CAACAgIAAxkBAAMyaP4ysQABpDMGVXi7m88M4bvdDUDaAALGFwAClLUYS5sPFDYCsujLNgQ",
            "CAACAgIAAxkBAAM0aP4ywPcUwscM6JdOLpY2cIZHP38AAvYqAAJgAThKTsUPg_bmNkM2BA",
            "CAACAgIAAxkBAAM2aP4y0gy21yYZAcuvbdFzqhlgqW4AAvQTAALB2_BIIe42z51nJmE2BA",
            "CAACAgIAAxkBAAM4aP4y6J95jLWjlrth-mxoVix4CNkAAhERAAKwg-lI0VH510R4Wxo2BA",
            "CAACAgIAAxkBAAM6aP4y-amg-1tcPKQL2UNEeRs0XgQAAq4QAAKPuvBIiqcvsvPoPtQ2BA"    
        ]
    },
    "jokeMessages":{
        "texts":[
            "я в армии буквально: \"за что мут, суки...\"",
            "в армии радует только, что моя попа в безопасности😈",
            "спишь?\nдаже через бота могу такое делать😈😈😈"
        ],
        "withPhoto":[0, 1],
        "photos":[
            "img/jokes/1.jpg",
            "img/jokes/2.jpg",
            "img/jokes/3.jpg"
        ],
        "withSticker":[0, 1],
        "stickers":[
            "CAACAgIAAxkBAAMuaP4yVzaGD0M0bBA4grmJLegtFvYAAsoEAAIcktIDPxEeanJ4Hu42BA",
            "CAACAgIAAxkBAAMoaP4yHnj4Z1VWO4KbOSm6TT6WIv0AAuEAA6mfVTnktVMswv4GDDYE",
            "CAACAgIAAxkBAAMmaP4yEsNeBwUebBHk29pnYk8UKGMAAjcrAALTvHhKjzprQyeafmI2BA",
            "CAACAgIAAxkBAAMkaP4x_Wri6oZTZfX1dB8_upOJ860AAiUQAAIrU_FI1qLfNubU_782BA",
            "CAACAgIAAxkBAAM8aP4zZKhgl3p7Ci8FJ4MyjVgEJbYAAiVYAAIwyThKYhGJOvp8LtE2BA",
            "CAACAgIAAxkBAAM-aP4zdCppMZ1ho3v16hlD5grINg4AAg8hAAJnWjBKu5OAVu9uDmM2BA",
            "CAACAgIAAxkBAANAaP4zgRkF_GnvGuUOdy_VR8baMZ4AAr4VAAJEvkFLMGSJ6b6FjjE2BA",
            "CAACAgIAAxkBAANCaP4zlTOTudUycIg1uKT81Uv97WEAAlUSAAIrb0FLAe_GwgVMtWw2BA"    
        ]
    },
    "regularMessages":{
        "texts":[
            "приветик, как диплом?",
            "погода сегодня говорит о том, что такое солнышко как ты должно гулять и дарить другим людям улыбки"
        ],
        "withPhoto":[0, 1],
        "photos":[
            "img/regular/1.jpg",
            "img/regular/2.jpg",
            "img/regular/3.jpg"
        ],
        "withSticker":[0, 1],
        "stickers":[
            "CAACAgIAAxkBAANEaP4z1eB7zHNsT2lNFoflgGs-LiQAAt0WAAJSq2FLRsEUugi7UBI2BA",
            "CAACAgIAAxkBAANGaP4z4mQnL4L45XJwwo_o8FBJRkAAAnkUAAJlUxhIRJoGxi3KttA2BA",
            "CAACAgIAAxkBAANIaP4z7D4SnQrjdzolEQZdnDOMjrAAAu4QAAI0RaBL0kA3lxJ96pg2BA"
        ]
    }
}
currentMessageToSend = {}

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# === Функция случайной рассылки ===
async def send_random_message():
    try:
        if "photo" in currentMessageToSend:
            await bot.send_photo(USER_ID, FSInputFile(currentMessageToSend["photo"]), caption=currentMessageToSend["text"])
            await bot.send_photo(GROUP_ID, FSInputFile(currentMessageToSend["photo"]), caption=currentMessageToSend["text"])
            del currentMessageToSend["photo"]
        else:
            await bot.send_message(USER_ID, text=currentMessageToSend["text"])
            await bot.send_message(GROUP_ID, text=currentMessageToSend["text"])
        if "sticker" in currentMessageToSend:
            await bot.send_sticker(USER_ID, sticker=currentMessageToSend["sticker"])
            await bot.send_sticker(GROUP_ID, sticker=currentMessageToSend["sticker"])
            del currentMessageToSend["sticker"]
        del currentMessageToSend["text"]
        print(f"[{datetime.now()}] Сообщение отправлено.")
    except Exception as e:
        print(f"Ошибка при отправке: {e}")

    # Планируем следующее случайное время отправки
    schedule_random_message()


def schedule_random_message():
    """Планирует отправку в случайную дату/время"""
    scheduler.remove_all_jobs()  # очищаем прошлое задание
 
    # Случайное время — от 1 часа до 2 дней вперёд
    delta = timedelta(
        days=0,
        hours=1,
        minutes=0
        # days=random.randint(0, 7),
        # hours=random.randint(0, 23),
        # minutes=random.randint(0, 59)
    )
    
    run_time = datetime.now() + delta
    message = random.choice(list(sendToSasha.keys()))
    text = random.choice(sendToSasha[message]["texts"])
    del sendToSasha[message]["texts"][text]
    if random.choice(sendToSasha[message]["withPhoto"]) == 1:
        print(f"Сообщение будет отправлено с фото.")   
        currentMessageToSend["photo"] = random.choice(sendToSasha[message]["photos"])
        del sendToSasha[message]["photos"][currentMessageToSend["photo"]]
    if random.choice(sendToSasha[message]["withSticker"]) == 1:
        print(f"Сообщение будет отправлено со стикером.")
        currentMessageToSend["sticker"] = random.choice(sendToSasha[message]["stickers"])
    currentMessageToSend["text"] = text
    scheduler.add_job(send_random_message, "date", run_date=run_time)
    print(f"Следующее сообщение запланировано на {run_time}")


# === Обработчики команд и сообщений ===
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("ну что ж, если ты это читаешь, саш, то я влип в долги.\nебаный белбет, теперь должен родине...\nно часть моего разума осталась здесь и она с тобой!\nпериодически будет тебе напоминать об одной твари, которая дрочит письки в армии.\nнаслаждайся😈")
    schedule_random_message()


@dp.message()
async def echo_msg(message: types.Message):
    await message.reply("хых, я бы ответил, но я дрочу письки(\nпрости, солнце, я обязательно вернусь!\nнадеюсь у тебя всё хорошо")
    await bot.send_message(GROUP_ID, text="❗❗❗ Она ответила " + str(message.date)[:-6] + " ❗❗❗")
    await bot.forward_message(
        chat_id=GROUP_ID,          
        from_chat_id=message.chat.id,  
        message_id=message.message_id
    )


# === Основной запуск ===
async def on_startup(app):
    scheduler.start()
    await bot.set_webhook(WEBHOOK_URL)
    print(f"✅ Webhook установлен: {WEBHOOK_URL}")

async def on_shutdown(app):
    await bot.delete_webhook()
    await bot.session.close()
    print("🛑 Бот выключен.")

async def handle_root(request):
    return web.Response(text="✅ Бот и вебхуки работают!")

# === Настройка aiohttp ===
app = web.Application()
app.router.add_get("/", handle_root)

# Здесь — современный способ подключения webhook handler
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
setup_application(app, dp, bot=bot)

app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8000)
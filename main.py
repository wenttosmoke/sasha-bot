import asyncio
import os
import random
import pytz
import json

from datetime import datetime, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# === Настройки ===
API_TOKEN = os.getenv("API_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID"))
LOGS_ID = int(os.getenv("LOGS_ID"))
STATE_FILE = "json/state.json"

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
            "погода сегодня говорит о том, что такое солнышко как ты должно гулять и дарить другим людям улыбки",
            "как себя чувствуешь?"
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
    },
    "withSong": {
        "texts": [
            "сегодня эта песня напоминает о тебе",
            "тёмный принц СКОКА СКОКА СКОКА",
            "перед тобой я подбираю слова, но поверь они не передадут",
            "ты разочаровалась в моём вокале?"
        ],
        "songs": [
            "songs/1.mp3",
            "songs/2.mp3",
            "songs/3.mp3",
            "songs/4.mp3"
        ]
    }
}
currentMessageToSend = {}

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()


# === Функции сохранения и загрузки рассылки из памяти ===
async def save_state(data: dict):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        await bot.send_message(LOGS_ID, text="❕Запланированное сообщение успешно сохранено в память❕")
        
    except Exception as e:
        print(f"⚠️ Ошибка при сохранении состояния: {e}", flush=True)
        await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при сохранении запланированного сообщения в память: {e}")

async def load_state() -> dict:
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        await bot.send_message(LOGS_ID, text="❕Запланированное сообщение успешно загружено из памяти❕")
    except Exception as e:
        print(f"⚠️ Ошибка при загрузке запланированного сообщения из памяти: {e}", flush=True)
        await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при загрузке запланированного сообщения из памяти: {e}")
    return {}

# === Функция случайной рассылки ===
async def send_random_message():
    is_sent = 0
    try:
        if "song" in currentMessageToSend:
            await bot.send_audio(currentMessageToSend["ID"], FSInputFile(currentMessageToSend["song"]), caption=currentMessageToSend["text"])
            await bot.send_audio(GROUP_ID, FSInputFile(currentMessageToSend["song"]), caption=currentMessageToSend["text"])
            del currentMessageToSend["text"]
            del currentMessageToSend["song"]
            is_sent += 1
    except Exception as e:
        await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при отправке песни с текстом: {e} ⚠️")

    try:
        if "photo" in currentMessageToSend:
                await bot.send_photo(currentMessageToSend["ID"], FSInputFile(currentMessageToSend["photo"]), caption=currentMessageToSend["text"])
                await bot.send_photo(GROUP_ID, FSInputFile(currentMessageToSend["photo"]), caption=currentMessageToSend["text"])
                del currentMessageToSend["text"]
                del currentMessageToSend["photo"]
                is_sent += 1
    except Exception as e:
        await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при отправке фото с текстом: {e} ⚠️")

    try:    
        if "text" in currentMessageToSend:
                await bot.send_message(currentMessageToSend["ID"], text=currentMessageToSend["text"])
                await bot.send_message(GROUP_ID, text=currentMessageToSend["text"])
                del currentMessageToSend["text"]
                is_sent += 1
    except Exception as e:
        await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при отправке текста: {e} ⚠️")

    try:        
        if "sticker" in currentMessageToSend:
                await bot.send_sticker(currentMessageToSend["ID"], sticker=currentMessageToSend["sticker"])
                await bot.send_sticker(GROUP_ID, sticker=currentMessageToSend["sticker"])
                del currentMessageToSend["sticker"]
                is_sent += 1
    except Exception as e:
        await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при отправке стикера: {e} ⚠️")
            
    if is_sent == len(currentMessageToSend.keys()):
        print(f"✅ [{datetime.now(pytz.timezone("Europe/Moscow"))}] Сообщение успешно отправлено ✅", flush=True)
        await bot.send_message(LOGS_ID, text=f"✅ [{datetime.now(pytz.timezone("Europe/Moscow"))}] Сообщение успешно отправлено ✅")
        os.remove(STATE_FILE)
    else:
        if is_sent == 0:
            print(f"❌❌❌ [{datetime.now(pytz.timezone("Europe/Moscow"))}] Сообщение не было отправлено ❌❌❌", flush=True)
            await bot.send_message(LOGS_ID, text=f"❌❌❌ [{datetime.now()}] Сообщение не было отправлено ❌❌❌")
        else:
            print(f"✅⚠️ [{datetime.now(pytz.timezone("Europe/Moscow"))}] Сообщение было отправлено с ошибкой ✅⚠️", flush=True)
            await bot.send_message(LOGS_ID, text=f"✅⚠️ [{datetime.now(pytz.timezone("Europe/Moscow"))}] Сообщение было отправлено с ошибкой ✅⚠️")
            os.remove(STATE_FILE)

    if "song" in currentMessageToSend:
        del currentMessageToSend["song"]        
    if "sticker" in currentMessageToSend:
        del currentMessageToSend["sticker"]
    if "text" in currentMessageToSend:
        del currentMessageToSend["text"]
    if "photo" in currentMessageToSend:
        del currentMessageToSend["photo"]
       
    # Планируем следующее случайное время отправки
    await schedule_random_message(currentMessageToSend["ID"])


async def schedule_random_message(ID):
    """Планирует отправку в случайную дату/время"""
    scheduler.remove_all_jobs()  # очищаем прошлое задание
 
    # Случайное время — от 1 часа до 2 дней вперёд
    delta = timedelta(
        days=0,
        hours=random.randint(0, 1),
        minutes=random.randint(0, 59)
        # days=random.randint(0, 7),
        # hours=random.randint(0, 23),
        # minutes=random.randint(0, 59)
    )
    
    run_time = datetime.now(pytz.timezone("Europe/Moscow")) + delta
    message = random.choice(list(sendToSasha.keys()))
    text = random.choice(sendToSasha[message]["texts"])
    sendToSasha[message]["texts"].remove(text)
    if message == "withSong":
        try:
            print(f"Сообщение будет отправлено с песней.", flush=True)
            currentMessageToSend["song"] = random.choice(sendToSasha[message]["songs"])
            sendToSasha[message]["songs"].remove(currentMessageToSend["song"])
        except Exception as e:
            print(f"⚠️ Ошибка при выборе песни: {e}", flush=True)
            await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при выборе песни: {e}")
    else:
        if random.choice(sendToSasha[message]["withPhoto"]) == 1:
            try:
                print(f"Сообщение будет отправлено с фото.", flush=True)   
                currentMessageToSend["photo"] = random.choice(sendToSasha[message]["photos"])
                sendToSasha[message]["photos"].remove(currentMessageToSend["photo"])
            except Exception as e:
                print(f"⚠️ Ошибка при выборе фото: {e}", flush=True)
                await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при выборе фото: {e}")
        if random.choice(sendToSasha[message]["withSticker"]) == 1:
            try:
                print(f"Сообщение будет отправлено со стикером.", flush=True)
                currentMessageToSend["sticker"] = random.choice(sendToSasha[message]["stickers"])
            except Exception as e:
                print(f"⚠️ Ошибка при выборе стикера: {e}", flush=True)
                await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при выборе стикера: {e}")
    currentMessageToSend["text"] = text
    currentMessageToSend["ID"] = ID
    await bot.send_message(LOGS_ID, text=f"❕\tСледующее сообщение:\t❕\nТекст: {currentMessageToSend["text"]}\nФото: {currentMessageToSend["photo"] if "photo" in currentMessageToSend else ""}\nСтикер: {currentMessageToSend["sticker"] if "" in currentMessageToSend else ""}\nПесня: {currentMessageToSend["song"] if "song" in currentMessageToSend else ""}")
    scheduler.add_job(send_random_message, "date", run_date=run_time)
    save_state({
        "next_message_time": run_time.isoformat(),
        "currentMessageToSend": currentMessageToSend
    })
    print(f"❕ Следующее сообщение успешно запланировано на {run_time} ❕", flush=True)
    await bot.send_message(LOGS_ID, text=f"❕ Следующее сообщение успешно запланировано на {run_time} ❕")


# === Обработчики команд и сообщений ===
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    scheduler.start()
    await message.answer("ну что ж, если ты это читаешь, саш, то я влип в долги.\nебаный белбет, теперь должен родине...\nно часть моего разума осталась здесь и она с тобой!\nпериодически будет тебе напоминать об одной твари, которая дрочит письки в армии.\nнаслаждайся😈")
    await bot.send_message(LOGS_ID, text=f"Пользователь с ID {message.from_user.id} запустил бота")
    await schedule_random_message(int(message.from_user.id))

    


@dp.message()
async def echo_msg(message: types.Message):
    if message.chat.id == message.from_user.id:
        await message.reply("хых, я бы ответил, но я дрочу письки(\nпрости, солнце, я обязательно вернусь!\nнадеюсь у тебя всё хорошо")
        await bot.send_message(GROUP_ID, text="❗❗❗ Она ответила " + str(message.date)[:-6] + " ❗❗❗")
        await bot.forward_message(
            chat_id=GROUP_ID,          
            from_chat_id=message.chat.id,  
            message_id=message.message_id
        )


# === Основной запуск ===
async def run_http_server(port: int):
    async def handle_root(request):
        return web.Response(text="✅ OK")

    app = web.Application()
    app.add_routes([web.get("/", handle_root)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"❕ HTTP server started on 0.0.0.0:{port} ❕", flush=True)
    await bot.send_message(LOGS_ID, text=f"❕ HTTP server started on 0.0.0.0:{port} ❕")


# === Основной запуск ===
async def main():

    # 1) запускаем локальный HTTP-сервер на PORT (чтобы Render увидел открытый порт)
    port = int(os.getenv("PORT", "8080"))
    await run_http_server(port)

    # 2) проверяем наличие сообщений в очереди
    state = await load_state()
    if state and "next_message_time" in state:
        try:
            run_time = datetime.fromisoformat(state["next_message_time"])
            now = datetime.now(pytz.timezone("Europe/Moscow"))
            if run_time > now:
                # Если время еще не наступило — планируем заново
                scheduler.add_job(send_random_message, "date", run_date=run_time)
                currentMessageToSend.update(state["currentMessageToSend"])
            else:
                # Если время прошло — сразу отправляем
                currentMessageToSend.update(state["currentMessageToSend"])
                await send_random_message()
            print(f"♻️ Восстановлено запланированное сообщение на {run_time}", flush=True)
            await bot.send_message(LOGS_ID, text=f"♻️ Восстановлено запланированное сообщение на {run_time}")
        except Exception as e:
            print(f"⚠️ Ошибка при восстановлении очереди сообщений: {e}", flush=True)
            await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при восстановлении очереди сообщений: {e}")

    # 3) запускаем polling (aiogram)
    # Удаляем webhook на всякий случай, чтобы не конфликтовал
    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 Start polling...", flush=True)
    await bot.send_message(LOGS_ID, text="🚀 Start polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
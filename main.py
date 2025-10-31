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
STATE_DIR ="json"
STATE_FILE = os.path.join(STATE_DIR, "state.json")
TEXT_FILE = os.path.join(STATE_DIR, "texts.json")
STATE_FOR_MORNING_FILE = os.path.join(STATE_DIR, "state_for_morning.json")

WEBHOOK_HOST = "https://sasha-bot-lwjs.onrender.com"  # 🌐 Укажи свой домен (https обязательно!)
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# === Функция выгрузки сообщений из JSON ===
def json_load():
    
      with open(TEXT_FILE, 'r') as file:
            
            try:
                data = json.load(file)
                bot.send_message(LOGS_ID, text="✅ Сообщения успешно распакованы из JSON ✅")
                print("✅ Сообщения успешно распакованы из JSON ✅", flush=True)
                return data
            except Exception as e:
                bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при распаковке сообщений из JSON: {e} ⚠️")
                print(f"⚠️ Ошибка при распаковке сообщений из JSON: {e} ⚠️", flush=True)
                
# === Объекты с данными ===
data = json_load()
sendToSasha = data["sendToSasha"]
morningTexts = data["morningTexts"]
stickerForMorning = data["stickersForMorning"]
currentMessageToSend = {}
currentMorningToSend = {}


# === Загружаем сообщения из JSON ===


bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# === Функции сохранения и загрузки рассылки из памяти ===

async def save_state(data: dict, file):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        await bot.send_message(LOGS_ID, text="❕Запланированное сообщение успешно сохранено в память❕")
        
    except Exception as e:
        print(f"⚠️ Ошибка при сохранении состояния: {e}", flush=True)
        await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при сохранении запланированного сообщения в память: {e}")

async def load_state(file) -> dict:
    try:
        if os.path.exists(file):
            with open(file, "r", encoding="utf-8") as f:
                return json.load(f)
            await bot.send_message(LOGS_ID, text="❕Запланированное сообщение успешно загружено из памяти❕")
    except Exception as e:
        print(f"⚠️ Ошибка при загрузке запланированного сообщения из памяти: {e}", flush=True)
        await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при загрузке запланированного сообщения из памяти: {e}")
    return {}

# === Функции вычисления времени до следующего утра ===

def get_time_delta():
    now = datetime.now(pytz.timezone("Europe/Moscow")) 
    print(now)
    # Следующий день 08:00
    tomorrow_8am = (now + timedelta(days=1)).replace(hour=8, minute=0, second=0, microsecond=0)
    
    # Случайное время между 08:00 и 12:00 следующего дня
    random_minutes = random.randint(0, 4 * 60)  # 4 часа = 240 минут
    target_time = tomorrow_8am + timedelta(minutes=random_minutes)
    
    # Вычисляем разницу
    delta = target_time - now
    
    return (delta.days, delta.seconds // 3600, (delta.seconds % 3600) // 60), target_time

# === Функция случайной рассылки ===

async def send_random_message():
    is_sent = 0
    total_to_sent = len(currentMessageToSend.keys()) - 1

    try:
        if "song" in currentMessageToSend:
            await bot.send_audio(currentMessageToSend["ID"], FSInputFile(currentMessageToSend["song"]), caption=currentMessageToSend["text"])
            await bot.send_audio(GROUP_ID, FSInputFile(currentMessageToSend["song"]), caption=currentMessageToSend["text"])
            del currentMessageToSend["text"]
            del currentMessageToSend["song"]
            is_sent += 2
    except Exception as e:
        await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при отправке песни с текстом: {e} ⚠️")

    try:
        if "photo" in currentMessageToSend:
                await bot.send_photo(currentMessageToSend["ID"], FSInputFile(currentMessageToSend["photo"]), caption=currentMessageToSend["text"])
                await bot.send_photo(GROUP_ID, FSInputFile(currentMessageToSend["photo"]), caption=currentMessageToSend["text"])
                del currentMessageToSend["text"]
                del currentMessageToSend["photo"]
                is_sent += 2
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
  
    if is_sent == total_to_sent:
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

# === Функция утренней рассылки ===

async def send_morning_message():
    is_sent = 0
    total_to_sent = len(currentMorningToSend.keys()) - 1

    try:    
        if "text" in currentMorningToSend:
                await bot.send_message(currentMorningToSend["ID"], text=currentMorningToSend["text"])
                await bot.send_message(GROUP_ID, text=currentMorningToSend["text"])
                del currentMorningToSend["text"]
                is_sent += 1
    except Exception as e:
        await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при отправке утреннего сообщения: {e} ⚠️")

    try:        
        if "sticker" in currentMorningToSend:
                await bot.send_sticker(currentMorningToSend["ID"], sticker=currentMorningToSend["sticker"])
                await bot.send_sticker(GROUP_ID, sticker=currentMorningToSend["sticker"])
                del currentMorningToSend["sticker"]
                is_sent += 1
    except Exception as e:
        await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при отправке стикера в утреннем сообщении: {e} ⚠️")
  
    if is_sent == total_to_sent:
        print(f"✅ [{datetime.now(pytz.timezone("Europe/Moscow"))}] Утреннее сообщение успешно отправлено ✅", flush=True)
        await bot.send_message(LOGS_ID, text=f"✅ [{datetime.now(pytz.timezone("Europe/Moscow"))}] Утреннее сообщение успешно отправлено ✅")
        os.remove(STATE_FOR_MORNING_FILE)
    else:
        if is_sent == 0:
            print(f"❌❌❌ [{datetime.now(pytz.timezone("Europe/Moscow"))}] Утреннее сообщение не было отправлено ❌❌❌", flush=True)
            await bot.send_message(LOGS_ID, text=f"❌❌❌ [{datetime.now()}] Утреннее сообщение не было отправлено ❌❌❌")
        else:
            print(f"✅⚠️ [{datetime.now(pytz.timezone("Europe/Moscow"))}] Утреннее сообщение было отправлено с ошибкой ✅⚠️", flush=True)
            await bot.send_message(LOGS_ID, text=f"✅⚠️ [{datetime.now(pytz.timezone("Europe/Moscow"))}] Утреннее сообщение было отправлено с ошибкой ✅⚠️")
            os.remove(STATE_FOR_MORNING_FILE)

    if "sticker" in currentMorningToSend:
        del currentMorningToSend["sticker"]
    if "text" in currentMorningToSend:
        del currentMorningToSend["text"]

       
    # Планируем следующее случайное время отправки
    await schedule_random_morning_message(currentMorningToSend["ID"])

# === Функция случайного времени сообщения ===

async def schedule_random_message(ID):
    """Планирует отправку в случайную дату/время"""
    if scheduler.get_jobs("random"):
        scheduler.remove_job("random")  # очищаем прошлое задание
 
    # Случайное время — от 1 часа до 2 дней вперёд
    deltaforMessages = timedelta(
        days=0,
        hours=5,
        minutes=2
        # days=random.randint(0, 7),
        # hours=random.randint(0, 23),
        # minutes=random.randint(0, 59)
    )

    run_time = datetime.now(pytz.timezone("Europe/Moscow")) + deltaforMessages
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
    scheduler.add_job(send_random_message, "date", run_date=run_time, id="random")
    await save_state({
        "next_message_time": run_time.isoformat(),
        "currentMessageToSend": currentMessageToSend
    }, STATE_FILE)
    print(f"❕ Следующее сообщение успешно запланировано на {run_time} ❕", flush=True)
    await bot.send_message(LOGS_ID, text=f"❕ Следующее сообщение успешно запланировано на {run_time} ❕")

# === Функция случайного времени утреннего сообщения ===

async def schedule_random_morning_message(ID):
    """Планирует отправку в случайную дату/время"""
    if scheduler.get_jobs("morning"):
        scheduler.remove_job("morning")  # очищаем прошлое задание
 
    # Случайное время — от 8 утра до 12 следующего дня
    deltaforMorningTexts = get_time_delta()
    run_time_for_morning_texts = datetime.now(pytz.timezone("Europe/Moscow")) + deltaforMorningTexts
    print("MORNING", flush=True)
    
    text = random.choice(morningTexts)
    morningTexts.remove(text)
    choosedsticker = random.choice(stickerForMorning)
    print(f"MORNING", flush=True)
    currentMorningToSend["text"] = text
    currentMorningToSend["ID"] = ID
    currentMorningToSend["sticker"] = choosedsticker

    await bot.send_message(LOGS_ID, text=f"❕\tСледующее утреннее сообщение:\t❕\nТекст: {currentMorningToSend["text"]}\nСтикер: {currentMessageToSend["sticker"] if "" in currentMessageToSend else ""}")
    scheduler.add_job(send_morning_message, "date", run_date=run_time_for_morning_texts, id="morning")
    await save_state({
        "next_message_time": run_time_for_morning_texts.isoformat(),
        "currentMessageToSend": currentMorningToSend
    }, STATE_FOR_MORNING_FILE)
    print(f"❕ Следующее утреннее сообщение успешно запланировано на {run_time_for_morning_texts} ❕", flush=True)
    await bot.send_message(LOGS_ID, text=f"❕ Следующее утреннее сообщение успешно запланировано на {run_time_for_morning_texts} ❕")

# === Обработчики команд и сообщений ===
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    scheduler.start()
    
    await message.answer("ну что ж, если ты это читаешь, саш, то я влип в долги.\nебаный белбет, теперь должен родине...\nно часть моего разума осталась здесь и она с тобой!\nпериодически будет тебе напоминать об одной твари, которая дрочит письки в армии.\nнаслаждайся😈")
    await bot.send_message(LOGS_ID, text=f"Пользователь с ID {message.from_user.id} запустил бота")
    await schedule_random_message(int(message.from_user.id))
    await schedule_random_morning_message(int(message.from_user.id))

    


@dp.message()
async def echo_msg(message: types.Message):
    if message.chat.id == message.from_user.id:
        await message.reply("хых, я бы ответил, но я дрочу письки(\nпрости, солнце, я обязательно вернусь!\nнадеюсь у тебя всё хорошо")
        await bot.send_message(GROUP_ID, text="❗❗❗ Она ответила ❗❗❗")
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
    state = await load_state(STATE_FILE)
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

    state_of_morning_message = await load_state(STATE_FOR_MORNING_FILE)
    if state_of_morning_message and "next_message_time" in state:
        try:
            run_time = datetime.fromisoformat(state_of_morning_message["next_message_time"])
            now = datetime.now(pytz.timezone("Europe/Moscow"))
            if run_time > now:
                # Если время еще не наступило — планируем заново
                scheduler.add_job(send_morning_message, "date", run_date=run_time, id="morning")
                currentMorningToSend.update(state_of_morning_message["currentMorningToSend"])
            else:
                # Если время прошло — сразу отправляем
                currentMorningToSend.update(state["currentMorningToSend"])
                await send_morning_message()
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

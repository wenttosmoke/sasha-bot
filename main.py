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
MY_ID = int(os.getenv("MY_ID"))
SASHA_ID = int(os.getenv("SASHA_ID"))
STATE_DIR ="json"
STATE_FILE = os.path.join(STATE_DIR, "state.json")
TEXT_FILE = os.path.join(STATE_DIR, "texts.json")
STATE_FOR_MORNING_FILE = os.path.join(STATE_DIR, "state_for_morning.json")

WEBHOOK_HOST = "https://sasha-bot-lwjs.onrender.com"  # 🌐 Укажи свой домен (https обязательно!)
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# === Функция выгрузки сообщений из JSON ===
def json_load():
    
      with open(TEXT_FILE, 'r') as file:
            
            try:
                data = json.load(file)
                # await bot.send_message(LOGS_ID, text="✅ Сообщения успешно распакованы из JSON ✅")
                print("✅ Сообщения успешно распакованы из JSON ✅", flush=True)
                return data
            except Exception as e:
                # bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при распаковке сообщений из JSON: {e} ⚠️")
                print(f"⚠️ Ошибка при распаковке сообщений из JSON: {e} ⚠️", flush=True)
                
# === Объекты с данными ===
data = json_load()
sendToSasha = data["sendToSasha"]
morningTexts = data["morningTexts"]
stickerForMorning = data["stickersForMorning"]
currentMessageToSend = {}
currentMorningToSend = {}

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

# === Функции проверки на случай праздников ===

async def check_and_send_special_day():
    now = datetime.now(pytz.timezone("Europe/Moscow"))
    day = now.day
    month = now.month

    special_days = {
        (1, 1): "с новым годом, солнце! так скучаю по тебе, наверное мою лысую голову укрыло слоем снега, смешная картина. пусть этот год начнётся у тебя также хорошо, как заканчивался мой 2025, когда я познакомился с тобой. я раньше и не думал, что котики могут так хорошо выдавать себя за людей...будь счастлива, уже не так много осталось, и если ты ещё ждёшь меня, я обязательно к тебе вернусь. с новым годом, люблю тебя❤️",
        (3, 8): "с 8 марта, моя принцесса! надеюсь мы с тобой уже хоть раз увиделись, либо видимся уже сейчас, когда ты это читаешь. сегодня твой день, сегодня я готов сорвать все цветы на полянах, скупить всё в магазнах...ладно, денег нет, на самом деле нарву с могил...шутка! очень надеюсь, что у нас получилось(-ся) встретиться, ведь я так хочу ещё хоть раз тебе подарить букетик и увидеть твою улыбку... 💐",
        (5, 26): "с днём рождения, сашенька!❤️ твой день, тебе уже 22, ты уже совсем взрослы котик блин...так надеюсь, что я смогу подарить тебе хоть что-то, но больше всего я хочу тебя увидеть. эгоистично, что подарки в твой день рождения хочу я? ахахах. солнце, ты самая красивое пушистое из семейства кошачьих, на твоём лице хочется видеть только улыбку, которая озоряет своим светом простор. надеюсь, что сейчас, читая этот текст ты улыбаешься. если да, то моя миссия выполнена. ты со всем справишься, ты моя самая большая умничка. люблю тебя❤️",
        (7, 25): "солнце, мне осталось всего 100 дней пережить и мы будем лапка к лапке!!! очень жду этого, заебала эта армия блин. надеюсь у тебя всё хорошо❤️",
        (11, 2): "я дома, котик! очень надеюсь что ты меня ждала, очень надеюсь что я в ближайшее время полечу к тебе, мяу."
    }

    if (month, day) in special_days:
        text = special_days[(month, day)]
        await bot.send_message(SASHA_ID, text=text)
        await bot.send_message(GROUP_ID, text=text)
        await bot.send_message(LOGS_ID, text=f"🎉 Отправлено праздничное сообщение за {now.strftime('%d.%m.%Y')}:\n{text}")
    else:
        print(f"📅 Сегодня {now.strftime('%d.%m.%Y')} — обычный день", flush=True)

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
    if scheduler.get_jobs(f"random{ID}"):
        scheduler.remove_job(f"random{ID}")  # очищаем прошлое задание
 
    # Случайное время — от 1 часа до 2 дней вперёд
    deltaforMessages = timedelta(
        days=0,
        hours=random.randint(0, 15),
        minutes=random.randint(0, 59)
    )

    run_time = datetime.now(pytz.timezone("Europe/Moscow")) + deltaforMessages
    message = random.choice(list(sendToSasha.keys()))
    while (message != "withSong" and len(sendToSasha[message]["texts"]) == 0) or (message == "withSong" and len(sendToSasha[message]["songs"]) == 0):
            print(f"⚠️ Закончились строки {sendToSasha[message]}", flush=True)
            await bot.send_message(LOGS_ID, text=f"⚠️ Закончились строки {message}")
            del sendToSasha[message]
            message = random.choice(list(sendToSasha.keys()))

    if message == "withSong":
        try:
            print(f"Сообщение будет отправлено с песней.", flush=True)
            currentMessageToSend["song"] = random.choice(list(sendToSasha[message]["songs"].keys()))
            currentMessageToSend["text"] = sendToSasha[message]["songs"][currentMessageToSend["song"]]
            del sendToSasha[message]["songs"][currentMessageToSend["song"]]
        except Exception as e:
            print(f"⚠️ Ошибка при выборе песни: {e}", flush=True)
            await bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при выборе песни: {e}")
    else:
        text = random.choice(sendToSasha[message]["texts"])
        sendToSasha[message]["texts"].remove(text)
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
    scheduler.add_job(send_random_message, "date", run_date=run_time, id=f"random{ID}")
    await save_state({
        "next_message_time": run_time.isoformat(),
        "currentMessageToSend": currentMessageToSend,
        "ID" : ID
    }, STATE_FILE)
    print(f"❕ Следующее сообщение успешно запланировано на {run_time} ❕", flush=True)
    await bot.send_message(LOGS_ID, text=f"❕ Следующее сообщение успешно запланировано на {run_time} ❕")

# === Функция случайного времени утреннего сообщения ===

async def schedule_random_morning_message(ID):
    """Планирует отправку в случайную дату/время"""
    if scheduler.get_jobs(f"morning{ID}"):
        scheduler.remove_job(f"morning{ID}")  # очищаем прошлое задание
 
    # Случайное время — от 8 утра до 12 следующего дня
    deltaTuple = get_time_delta()[0]
    print(f"deltaTuple={deltaTuple}", flush=True)
    deltaforMorningTexts = timedelta(
        days=int(deltaTuple[0]),
        hours=int(deltaTuple[1]),
        minutes=int(deltaTuple[2])
    )
    run_time_for_morning_texts = datetime.now(pytz.timezone("Europe/Moscow")) + deltaforMorningTexts
    print("MORNING", flush=True)
    
    text = random.choice(morningTexts)
    morningTexts.remove(text)
    choosedsticker = random.choice(stickerForMorning)
    print(f"MORNING", flush=True)
    currentMorningToSend["text"] = text
    currentMorningToSend["ID"] = ID
    currentMorningToSend["sticker"] = choosedsticker

    await bot.send_message(LOGS_ID, text=f"❕\tСледующее утреннее сообщение:\t❕\nТекст: {currentMorningToSend["text"]}\nСтикер: {currentMorningToSend["sticker"]}")
    scheduler.add_job(send_morning_message, "date", run_date=run_time_for_morning_texts, id=f"morning{ID}")
    await save_state({
        "next_message_time": run_time_for_morning_texts.isoformat(),
        "currentMessageToSend": currentMorningToSend,
        "ID" : ID
    }, STATE_FOR_MORNING_FILE)
    print(f"❕ Следующее утреннее сообщение успешно запланировано на {run_time_for_morning_texts} ❕", flush=True)
    await bot.send_message(LOGS_ID, text=f"❕ Следующее утреннее сообщение успешно запланировано на {run_time_for_morning_texts} ❕")

# === Обработчики команд и сообщений ===
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    if int(message.from_user.id) == MY_ID or int(message.from_user.id) == SASHA_ID:
        scheduler.start()

        await message.answer("мяу мяу, ты вернулась! солнце, пару месяцев, и я буду с тобой и уже не уйду. бот сделан с любовью и костылями. наслаждайся. люблю тебя!")
        await bot.send_message(LOGS_ID, text=f"✅ Пользователь с ID {message.from_user.id} запустил бота ✅")
        await schedule_random_message(int(message.from_user.id))
        await schedule_random_morning_message(int(message.from_user.id))
        scheduler.add_job(check_and_send_special_day, "cron", hour=12, minute=40, timezone=pytz.timezone("Europe/Moscow"), id=f"daily_special_check{message.from_user.id}")
    else:
        await bot.send_message(LOGS_ID, text=f"❌ Пользователь с ID {message.from_user.id} попытался запустить бота ❌")
        await message.answer("ты кто, съебался нахуй, бот не для тебя😡")


    


@dp.message()
async def echo_msg(message: types.Message):
    if int(message.from_user.id) == MY_ID or int(message.from_user.id) == SASHA_ID:
        if message.chat.id == message.from_user.id:
            await message.reply("я в армии, смотрю на небо в поисках твои глаз\nя их найду даже самой тёмной ночью\nосталось немного, котик, дождись...")
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
                scheduler.add_job(send_random_message, "date", run_date=run_time, id=f"random{state["ID"]}")
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
                scheduler.add_job(send_morning_message, "date", run_date=run_time, id=f"morning{state["ID"]}")
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

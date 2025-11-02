import asyncio
import os
import random
import pytz
import json
import signal
import atexit

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
SCHEDULER_STATE_FILE = os.path.join(STATE_DIR, "scheduler_state.json")
STATE_OF_OBJECTS = os.path.join(STATE_DIR, "state_of_objects.json")
WEBHOOK_HOST = "https://sasha-bot-lwjs.onrender.com"  # 🌐 Укажи свой домен (https обязательно!)
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# === Функция выгрузки сообщений из JSON ===
def json_load():
    try:
      with open(TEXT_FILE, 'r') as file:    
        data = json.load(file)
        # await bot.send_message(LOGS_ID, text="✅ Сообщения успешно распакованы из JSON ✅")
        print("✅ Сообщения успешно распакованы из JSON ✅", flush=True)
        return data
    except Exception as e:
        # bot.send_message(LOGS_ID, text=f"⚠️ Ошибка при распаковке сообщений из JSON: {e} ⚠️")
        print(f"⚠️ Ошибка при распаковке сообщений из JSON: {e} ⚠️", flush=True)
                
# === Объекты с данными ===
# data = json_load()
# sendToSasha = data.get("sendToSasha", {})
# morningTexts = data.get("morningTexts", [])
# stickerForMorning = data.get("stickersForMorning", [])
currentMessageToSend = {}
currentMorningToSend = {}

# === Функции сохранения и загрузки рассылки из памяти ===

# === Синхронные функции для сохранения состояния ===
def sync_save_state(data: dict, file: str):
    """Синхронное сохранение состояния в файл"""
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Состояние синхронно сохранено в {file}", flush=True)
    except Exception as e:
        print(f"⚠️ Ошибка при синхронном сохранении состояния: {e}", flush=True)

def sync_save_message_queue():
    """Синхронное сохранение всей очереди сообщений"""
    message_state = {
        'currentMessageToSend': currentMessageToSend,
        'currentMorningToSend': currentMorningToSend,
        'sendToSasha': sendToSasha,
        'morningTexts': morningTexts,
        'stickerForMorning': stickerForMorning,
        'last_update': datetime.now(pytz.timezone("Europe/Moscow")).isoformat()
    }
    sync_save_state(message_state, STATE_FILE)

def sync_save_scheduler_state():
    """Синхронное сохранение состояния планировщика"""
    jobs_data = []
    for job in scheduler.get_jobs():
        job_info = {
            'id': job.id,
            'name': job.name if hasattr(job, 'name') else job.id,
            'func': job.func.__name__ if hasattr(job.func, '__name__') else str(job.func)
        }
        
        # Безопасная проверка next_run_time
        try:
            if hasattr(job, 'next_run_time') and job.next_run_time is not None:
                job_info['next_run_time'] = job.next_run_time.isoformat()
            else:
                job_info['next_run_time'] = None
        except (AttributeError, Exception):
            job_info['next_run_time'] = None
            
        jobs_data.append(job_info)
    
    sync_save_state({'jobs': jobs_data}, SCHEDULER_STATE_FILE)

async def save_state(data: dict, file: str):
    """Асинхронное сохранение состояния в файл"""
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✅ Состояние сохранено в {file}", flush=True)
    except Exception as e:
        print(f"⚠️ Ошибка при сохранении состояния: {e}", flush=True)
        # Не пытаемся отправлять сообщения в бота при ошибках сохранения

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

# === Функция сохранения состояния планировщика ===

async def save_scheduler_state():
    """Сохраняет состояние планировщика"""
    jobs_data = []
    for job in scheduler.get_jobs():
        job_info = {
            'id': job.id,
            'name': job.name if hasattr(job, 'name') else job.id,
            'func': job.func.__name__ if hasattr(job.func, '__name__') else str(job.func)
        }
        
        # Безопасная проверка next_run_time
        try:
            if hasattr(job, 'next_run_time') and job.next_run_time is not None:
                job_info['next_run_time'] = job.next_run_time.isoformat()
            else:
                job_info['next_run_time'] = None
        except (AttributeError, Exception):
            job_info['next_run_time'] = None
            
        jobs_data.append(job_info)
    
    await save_state({'jobs': jobs_data}, SCHEDULER_STATE_FILE)

# === Функция восстановления состояния планировщика ===

async def restore_scheduler_state():
    """Восстанавливает состояние планировщика"""
    state = await load_state(SCHEDULER_STATE_FILE)
    if not state or 'jobs' not in state:
        print("ℹ️ Нет сохраненного состояния планировщика", flush=True)
        return
    
    now = datetime.now(pytz.timezone("Europe/Moscow"))
    restored_count = 0
    
    for job_data in state['jobs']:
        try:
            # Пропускаем задачи без времени выполнения
            if not job_data.get('next_run_time'):
                continue
                
            run_time = datetime.fromisoformat(job_data['next_run_time'])
            
            # Если время уже прошло, пропускаем
            if run_time <= now:
                print(f"⏰ Время задачи {job_data.get('id')} уже прошло, пропускаем", flush=True)
                continue
                
            # Восстанавливаем задачи по их ID
            job_id = job_data.get('id')
            if job_id == "random":
                if not scheduler.get_job("random"):
                    scheduler.add_job(
                        send_random_message, 
                        "date", 
                        run_date=run_time, 
                        id="random"
                    )
                    restored_count += 1
                    print(f"♻️ Восстановлена задача random на {run_time}", flush=True)
                    
            elif job_id == "morning":
                if not scheduler.get_job("morning"):
                    scheduler.add_job(
                        send_morning_message, 
                        "date", 
                        run_date=run_time, 
                        id="morning"
                    )
                    restored_count += 1
                    print(f"♻️ Восстановлена задача morning на {run_time}", flush=True)
                    
            elif job_id == "daily_special_check":
                if not scheduler.get_job("daily_special_check"):
                    scheduler.add_job(
                        check_and_send_special_day, 
                        "cron", 
                        hour=0, minute=0, 
                        timezone=pytz.timezone("Europe/Moscow"), 
                        id="daily_special_check"
                    )
                    restored_count += 1
                    print(f"♻️ Восстановлена задача daily_special_check", flush=True)
                
        except Exception as e:
            print(f"⚠️ Ошибка при восстановлении задачи {job_data.get('id')}: {e}", flush=True)
    
    print(f"✅ Восстановлено {restored_count} задач планировщика", flush=True)

# === Функция сохранения очереди сообщений ===

async def save_message_queue():
    """Асинхронное сохранение всей очереди сообщений"""
    message_state = {
        'currentMessageToSend': currentMessageToSend,
        'currentMorningToSend': currentMorningToSend,
        'sendToSasha': sendToSasha,
        'morningTexts': morningTexts,
        'stickerForMorning': stickerForMorning,
        'last_update': datetime.now(pytz.timezone("Europe/Moscow")).isoformat()
    }
    await save_state(message_state, STATE_FILE)

# === Функция загрузки очереди сообщений ===

async def load_message_queue():
    """Загружает всю очередь сообщений"""
    state = await load_state(STATE_FILE)
    if state:
        global currentMessageToSend, currentMorningToSend, sendToSasha, morningTexts, stickerForMorning
        
        currentMessageToSend.update(state.get('currentMessageToSend', {}))
        currentMorningToSend.update(state.get('currentMorningToSend', {}))
        
        # Восстанавливаем исходные данные, если они не загрузились
        if not sendToSasha:
            sendToSasha.update(state.get('sendToSasha', data["sendToSasha"]))
        if not morningTexts:
            morningTexts.extend(state.get('morningTexts', data["morningTexts"]))
        if not stickerForMorning:
            stickerForMorning.extend(state.get('stickerForMorning', data["stickersForMorning"]))

# === Функции проверки на случай праздников ===

async def check_and_send_special_day():
    now = datetime.now(pytz.timezone("Europe/Moscow"))
    day = now.day
    month = now.month

    special_days = {
        (1, 1): "с новым годом, солнце! так скучаю по тебе, наверное мою лысую голову укрыло слоем снега, смешная картина. пусть этот год начнётся у тебя также хорошо, как заканчивался мой 2025, когда я познакомился с тобой. я раньше и не думал, что котики могут так хорошо выдавать себя за людей...будь счастлива, уже не так много осталось, и если ты ещё ждёшь меня, я обязательно к тебе вернусь. с новым годом, люблю тебя❤️",
        (11, 2): "с днём рождения, сашенька!❤️ твой день, тебе уже 22, ты уже совсем взрослы котик блин...так надеюсь, что я смогу подарить тебе хоть что-то, но больше всего я хочу тебя увидеть. эгоистично, что подарки в твой день рождения хочу я? ахахах. солнце, ты самая красивое пушистое из семейства кошачьих, на твоём лице хочется видеть только улыбку, которая озоряет своим светом простор. надеюсь, что сейчас, читая этот текст ты улыбаешься. если да, то моя миссия выполнена. ты со всем справишься, ты моя самая большая умничка. люблю тебя❤️",
        (3, 8): "с 8 марта, моя принцесса! надеюсь мы с тобой уже хоть раз увиделись, либо видимся уже сейчас, когда ты это читаешь. сегодня твой день, сегодня я готов сорвать все цветы на полянах, скупить всё в магазнах...ладно, денег нет, на самом деле нарву с могил...шутка! очень надеюсь, что у нас получилось(-ся) встретиться, ведь я так хочу ещё хоть раз тебе подарить букетик и увидеть твою улыбку... 💐",
        (5, 26): "с днём рождения, сашенька!❤️ твой день, тебе уже 22, ты уже совсем взрослы котик блин...так надеюсь, что я смогу подарить тебе хоть что-то, но больше всего я хочу тебя увидеть. эгоистично, что подарки в твой день рождения хочу я? ахахах. солнце, ты самая красивое пушистое из семейства кошачьих, на твоём лице хочется видеть только улыбку, которая озоряет своим светом простор. надеюсь, что сейчас, читая этот текст ты улыбаешься. если да, то моя миссия выполнена. ты со всем справишься, ты моя самая большая умничка. люблю тебя❤️"
    }

    if (month, day) in special_days:
        text = special_days[(month, day)]
        await bot.send_message(MY_ID, text=text)
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
    try:
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
                await bot.send_message(LOGS_ID, text=f"❌❌❌ [{datetime.now(pytz.timezone("Europe/Moscow"))}] Сообщение не было отправлено ❌❌❌")
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
        # Сохраняем очередь и планировщика  
        await save_message_queue()
        await save_scheduler_state()
    except Exception as e:
        print(f"❌ Ошибка при отправке сообщения: {e}", flush=True)
        await bot.send_message(LOGS_ID, text=f"❌ Ошибка при отправке сообщения: {e}")   
    # Планируем следующее случайное время отправки
    await schedule_random_message(currentMessageToSend["ID"])

# === Функция утренней рассылки ===

async def send_morning_message():
    try:
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
                await bot.send_message(LOGS_ID, text=f"❌❌❌ [{datetime.now(pytz.timezone("Europe/Moscow"))}] Утреннее сообщение не было отправлено ❌❌❌")
            else:
                print(f"✅⚠️ [{datetime.now(pytz.timezone("Europe/Moscow"))}] Утреннее сообщение было отправлено с ошибкой ✅⚠️", flush=True)
                await bot.send_message(LOGS_ID, text=f"✅⚠️ [{datetime.now(pytz.timezone("Europe/Moscow"))}] Утреннее сообщение было отправлено с ошибкой ✅⚠️")
                os.remove(STATE_FOR_MORNING_FILE)

        if "sticker" in currentMorningToSend:
            del currentMorningToSend["sticker"]
        if "text" in currentMorningToSend:
            del currentMorningToSend["text"]
     # Сохраняем очередь и планировщика  
        await save_message_queue()
        await save_scheduler_state()
    except Exception as e:
        print(f"❌ Ошибка при отправке утреннего сообщения: {e}", flush=True)
        await bot.send_message(LOGS_ID, text=f"❌ Ошибка при отправке утреннего сообщения: {e}")   
       
    # Планируем следующее случайное время отправки
    await schedule_random_morning_message(currentMorningToSend["ID"])

# === Функция случайного времени сообщения ===

async def schedule_random_message(ID):
    """Планирует отправку с сохранением состояния"""
    try:
        # Удаляем старую задачу если есть
        old_job = scheduler.get_job("random")
        if old_job:
            old_job.remove()
 
        # Случайное время — от 1 часа до 2 дней вперёд
        deltaforMessages = timedelta(
            days=0,
            hours=0,
            minutes=5
        )

        run_time = datetime.now(pytz.timezone("Europe/Moscow")) + deltaforMessages
        
        # Выбираем сообщение (ваш существующий код)
        message = random.choice(list(sendToSasha.keys()))
        while (message != "withSong" and len(sendToSasha[message]["texts"]) == 0) or (message == "withSong" and len(sendToSasha[message]["songs"]) == 0):
            print(f"⚠️ Закончились строки {sendToSasha[message]}", flush=True)
            await bot.send_message(LOGS_ID, text=f"⚠️ Закончились строки {message}")
            del sendToSasha[message]
            message = random.choice(list(sendToSasha.keys()))

        # Подготавливаем сообщение (ваш существующий код)
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
        
        # Добавляем задачу в планировщик
        scheduler.add_job(send_random_message, "date", run_date=run_time, id="random")
        
        # Сохраняем состояние
        await save_message_queue()
        await save_scheduler_state()
        
        print(f"❕ Следующее сообщение успешно запланировано на {run_time} ❕", flush=True)
        await bot.send_message(LOGS_ID, text=f"❕ Следующее сообщение успешно запланировано на {run_time} ❕")
        
    except Exception as e:
        print(f"❌ Ошибка при планировании сообщения: {e}", flush=True)
        await bot.send_message(LOGS_ID, text=f"❌ Ошибка при планировании сообщения: {e}")

# === Функция случайного времени утреннего сообщения ===

async def schedule_random_morning_message(ID):
    """Планирует утреннюю отправку с сохранением состояния"""
    try:
        # Удаляем старую задачу если есть
        old_job = scheduler.get_job("morning")
        if old_job:
            old_job.remove()
 
        # Случайное время — от 8 утра до 12 следующего дня
        deltaTuple = get_time_delta()[0]
        print(f"deltaTuple={deltaTuple}", flush=True)
        deltaforMorningTexts = timedelta(
            days=int(deltaTuple[0]),
            hours=int(deltaTuple[1]),
            minutes=int(deltaTuple[2])
        )
        run_time_for_morning_texts = datetime.now(pytz.timezone("Europe/Moscow")) + deltaforMorningTexts
        
        # Подготавливаем утреннее сообщение
        text = random.choice(morningTexts)
        morningTexts.remove(text)
        choosedsticker = random.choice(stickerForMorning)
        
        currentMorningToSend["text"] = text
        currentMorningToSend["ID"] = ID
        currentMorningToSend["sticker"] = choosedsticker

        # Добавляем задачу в планировщик
        scheduler.add_job(send_morning_message, "date", run_date=run_time_for_morning_texts, id="morning")
        
        # Сохраняем состояние
        await save_message_queue()
        await save_scheduler_state()
        
        print(f"❕ Следующее утреннее сообщение успешно запланировано на {run_time_for_morning_texts} ❕", flush=True)
        await bot.send_message(LOGS_ID, text=f"❕ Следующее утреннее сообщение успешно запланировано на {run_time_for_morning_texts} ❕")
        
    except Exception as e:
        print(f"❌ Ошибка при планировании утреннего сообщения: {e}", flush=True)
        await bot.send_message(LOGS_ID, text=f"❌ Ошибка при планировании утреннего сообщения: {e}")

# === Обработчики команд и сообщений ===
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    if int(message.from_user.id) == MY_ID or int(message.from_user.id) == SASHA_ID:
        currentMessageToSend["ID"] = message.from_user.id
        currentMorningToSend["ID"] = message.from_user.id
        await message.answer("ну что ж, если ты это читаешь, саш, то я влип в долги.\nебаный белбет, теперь должен родине...\nно часть моего разума осталась здесь и она с тобой!\nпериодически будет тебе напоминать об одной твари, которая дрочит письки в армии.\nнаслаждайся😈")
        await bot.send_message(LOGS_ID, text=f"✅ Пользователь с ID {message.from_user.id} запустил бота ✅")
        await schedule_random_message(int(message.from_user.id))
        await schedule_random_morning_message(int(message.from_user.id))
        scheduler.add_job(check_and_send_special_day, "cron", hour=12, minute=40, timezone=pytz.timezone("Europe/Moscow"), id="daily_special_check")
    else:
        await bot.send_message(LOGS_ID, text=f"❌ Пользователь с ID {message.from_user.id} попытался запустить бота ❌")
        await message.answer("ты кто, съебался нахуй, бот не для тебя😡")


    


@dp.message()
async def echo_msg(message: types.Message):
    if int(message.from_user.id) == MY_ID or int(message.from_user.id) == SASHA_ID:
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
    async def handle_health(request):
        return web.json_response({"status": "ok", "timestamp": datetime.now().isoformat()})
    app = web.Application()
    app.add_routes([web.get("/", handle_root), web.get("/health", handle_health)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"❕ HTTP server started on 0.0.0.0:{port} ❕", flush=True)
    await bot.send_message(LOGS_ID, text=f"❕ HTTP server started on 0.0.0.0:{port} ❕")

def sync_cleanup():
    """Синхронная очистка и сохранение состояния"""
    try:
        print("💾 Синхронное сохранение состояния перед завершением...", flush=True)
        
        # Сохраняем состояние синхронно
        sync_save_message_queue()
        sync_save_scheduler_state()
        
        # Останавливаем планировщик
        if scheduler.running:
            scheduler.shutdown()
            
        print("✅ Состояние сохранено, планировщик остановлен", flush=True)
    except Exception as e:
        print(f"⚠️ Ошибка при синхронном сохранении состояния: {e}", flush=True)

async def async_cleanup():
    """Асинхронная очистка и сохранение состояния"""
    try:
        print("💾 Асинхронное сохранение состояния перед завершением...", flush=True)
        
        # Сохраняем состояние асинхронно
        await save_message_queue()
        await save_scheduler_state()
        
        # Останавливаем планировщик
        if scheduler.running:
            scheduler.shutdown()
            
        print("✅ Состояние сохранено, планировщик остановлен", flush=True)
    except Exception as e:
        print(f"⚠️ Ошибка при асинхронном сохранении состояния: {e}", flush=True)

def setup_cleanup():
    """Настройка обработчиков для корректного завершения"""
    def signal_handler(signum, frame):
        print(f"📞 Получен сигнал {signum}, сохраняем состояние...", flush=True)
        # Используем синхронную очистку для сигналов
        sync_cleanup()
    
    # Регистрируем обработчики сигналов
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    except (AttributeError, ValueError):
        print("⚠️ Сигналы не поддерживаются на этой платформе", flush=True)
    
    # Регистрируем обработчик при выходе (тоже синхронный)
    atexit.register(sync_cleanup)

async def validate_and_repair_data():
    """Проверяет и восстанавливает целостность данных"""
    global sendToSasha, morningTexts, stickerForMorning, data
    
    # Загружаем исходные данные если они пустые
    if not data:
        data = json_load()
    
    # Проверяем основные данные
    if not sendToSasha:
        sendToSasha = data.get("sendToSasha", {})
        print("⚠️ Восстановлены sendToSasha из исходных данных", flush=True)
    
    if not morningTexts:
        morningTexts = data.get("morningTexts", [])
        print("⚠️ Восстановлены morningTexts из исходных данных", flush=True)
    
    if not stickerForMorning:
        stickerForMorning = data.get("stickersForMorning", [])
        print("⚠️ Восстановлены stickerForMorning из исходных данных", flush=True)
    
    # Проверяем текущие сообщения
    if currentMessageToSend and not currentMessageToSend.get("ID"):
        currentMessageToSend.clear()
        print("⚠️ Очищен некорректный currentMessageToSend", flush=True)
    
    if currentMorningToSend and not currentMorningToSend.get("ID"):
        currentMorningToSend.clear()
        print("⚠️ Очищен некорректный currentMorningToSend", flush=True)
    
    # Сохраняем исправленные данные
    await save_message_queue()

# === Основной запуск ===
async def main():
    # 1) Настройка обработчиков для корректного завершения
    setup_cleanup()
    
    # 2) Инициализация данных
    global data, sendToSasha, morningTexts, stickerForMorning
    data = json_load()
    sendToSasha = data.get("sendToSasha", {})
    morningTexts = data.get("morningTexts", [])
    stickerForMorning = data.get("stickersForMorning", [])
    
    print("🔄 Загрузка сохраненного состояния...", flush=True)
    
    # 3) Загружаем сохраненное состояние сообщений
    await load_message_queue()
    
    # 4) Проверяем и восстанавливаем целостность данных
    await validate_and_repair_data()
    
    # 5) Запускаем HTTP сервер (для Render)
    port = int(os.getenv("PORT", "8080"))
    await run_http_server(port)
    
    # 6) Запускаем планировщик
    if not scheduler.running:
        scheduler.start()
        print("✅ Планировщик запущен", flush=True)
    
     # 7) Восстанавливаем задачи планировщика
    await restore_scheduler_state()
    
    # 8) Проверяем и создаем задачи если нужно
    now = datetime.now(pytz.timezone("Europe/Moscow"))
    
    # Проверяем задачу random
    random_job = scheduler.get_job("random")
    # if not random_job:
    #     print("🔄 Создание новой задачи random...", flush=True)
    #     target_id = currentMessageToSend.get("ID", SASHA_ID)
    #     await schedule_random_message(target_id)
    # else:
    #     print(f"✅ Задача random активна, следующее выполнение: {random_job.next_run_time}", flush=True)
    if random_job:
        print(f"✅ Задача random активна, следующее выполнение: {random_job.next_run_time}", flush=True)
    
        
    # Проверяем задачу morning  
    morning_job = scheduler.get_job("morning")
    # if not morning_job:
    #     print("🔄 Создание новой задачи morning...", flush=True)
    #     target_id = currentMorningToSend.get("ID", SASHA_ID)
    #     await schedule_random_morning_message(target_id)
    # else:
    #     print(f"✅ Задача morning активна, следующее выполнение: {morning_job.next_run_time}", flush=True)
    if morning_job:
        print(f"✅ Задача morning активна, следующее выполнение: {morning_job.next_run_time}", flush=True)

    # 9) Сохраняем начальное состояние
    await save_message_queue()
    await save_scheduler_state()
    
    # 10) Отправляем сообщение о запуске
    try:
        await bot.send_message(LOGS_ID, text="🚀 Бот запущен с восстановлением состояния")
    except Exception as e:
        print(f"⚠️ Не удалось отправить сообщение о запуске: {e}", flush=True)
    
    # 11) Запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 Start polling...", flush=True)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка в основном цикле: {e}", flush=True)
        # Сохраняем состояние при ошибке
        await async_cleanup()
        raise


if __name__ == "__main__":
    asyncio.run(main())
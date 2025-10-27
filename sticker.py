from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = "8401693264:AAEz21vSR2t5fq7UJZifgfL7s4ZE1ZZrZ7g"

async def get_sticker_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sticker = update.message.sticker
    if sticker:
        await update.message.reply_text(f"🆔 ID стикера:\n`{sticker.file_id}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Это не стикер!")

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(MessageHandler(filters.Sticker.ALL, get_sticker_id))
app.run_polling()
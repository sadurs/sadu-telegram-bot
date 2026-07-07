import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "6856205408"))

PACKAGES = {
    "basic": ("Basic Package", "100 QAR"),
    "pro": ("Professional Package", "200 QAR"),
    "complete": ("Complete Package", "450 QAR"),
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [[
        InlineKeyboardButton("العربية", callback_data="lang_ar"),
        InlineKeyboardButton("English", callback_data="lang_en")
    ]]
    await update.message.reply_text("Choose language / اختر اللغة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data.startswith("lang_"):
        context.user_data["lang"] = data.split("_")[1]
        keyboard = [
            [InlineKeyboardButton("Basic - 100 QAR", callback_data="pkg_basic")],
            [InlineKeyboardButton("Professional - 200 QAR", callback_data="pkg_pro")],
            [InlineKeyboardButton("Complete - 450 QAR", callback_data="pkg_complete")]
        ]
        await q.edit_message_text("اختر الباقة:" if context.user_data["lang"] == "ar" else "Choose package:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("pkg_"):
        key = data.split("_")[1]
        context.user_data["package"] = PACKAGES[key]
        keyboard = [[
            InlineKeyboardButton("Yes / نعم", callback_data="music_yes"),
            InlineKeyboardButton("No / لا", callback_data="music_no")
        ]]
        await q.edit_message_text("إضافة موسيقى AI بـ 100 QAR؟\nAdd AI Music for 100 QAR?", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("music_"):
        context.user_data["music"] = "Yes" if data == "music_yes" else "No"
        context.user_data["step"] = "name"
        await q.edit_message_text("اكتب اسمك:" if context.user_data.get("lang") == "ar" else "Enter your name:")

    elif data.startswith("admin_accept_") or data.startswith("admin_reject_"):
        action, user_id = data.split("_")[1], int(data.split("_")[2])
        msg = "تم قبول طلبك ✅" if action == "accept" else "تم رفض طلبك ❌"
        msg_en = "Your request has been accepted ✅" if action == "accept" else "Your request has been rejected ❌"
        await context.bot.send_message(user_id, f"{msg}\n{msg_en}")
        await q.edit_message_text("تم تحديث حالة الطلب.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")
    text = update.message.text

    if step == "name":
        context.user_data["name"] = text
        context.user_data["step"] = "email"
        await update.message.reply_text("اكتب الإيميل:")

    elif step == "email":
        context.user_data["email"] = text
        context.user_data["step"] = "car"
        await update.message.reply_text("اكتب موديل السيارة:")

    elif step == "car":
        context.user_data["car"] = text
        context.user_data["step"] = "date"
        await update.message.reply_text("اكتب تاريخ التصوير المناسب:")

    elif step == "date":
        context.user_data["date"] = text
        pkg, price = context.user_data["package"]
        music_price = 100 if context.user_data["music"] == "Yes" else 0
        total = int(price.split()[0]) + music_price

        summary = f"""
طلب جديد من SADU

الاسم: {context.user_data['name']}
الإيميل: {context.user_data['email']}
السيارة: {context.user_data['car']}
التاريخ: {context.user_data['date']}
الباقة: {pkg}
السعر: {price}
AI Music: {context.user_data['music']}
الإجمالي: {total} QAR
User ID: {update.effective_user.id}
"""

        keyboard = [[
            InlineKeyboardButton("قبول ✅", callback_data=f"admin_accept_{update.effective_user.id}"),
            InlineKeyboardButton("رفض ❌", callback_data=f"admin_reject_{update.effective_user.id}")
        ]]

        await context.bot.send_message(ADMIN_CHAT_ID, summary, reply_markup=InlineKeyboardMarkup(keyboard))
        await update.message.reply_text("تم إرسال طلبك بنجاح ✅\nYour request has been sent successfully.")
        context.user_data.clear()

    else:
        await update.message.reply_text("اكتب /start للبدء")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()

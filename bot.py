import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "6856205408"))

PACKAGES = {
    "basic": ("الباقة الأساسية / Basic Package", 100),
    "pro": ("الباقة الاحترافية / Professional Package", 200),
    "complete": ("الباقة المتكاملة / Complete Package", 450),
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("العربية 🇶🇦", callback_data="lang_ar")],
        [InlineKeyboardButton("English 🇬🇧", callback_data="lang_en")]
    ]
    await update.message.reply_text(
        "اختر اللغة / Choose language:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_packages(q, context):
    lang = context.user_data.get("lang", "ar")
    keyboard = [
        [InlineKeyboardButton("الباقة الأساسية / Basic - 100 QAR", callback_data="pkg_basic")],
        [InlineKeyboardButton("الباقة الاحترافية / Professional - 200 QAR", callback_data="pkg_pro")],
        [InlineKeyboardButton("الباقة المتكاملة / Complete - 450 QAR", callback_data="pkg_complete")]
    ]
    text = "اختر الباقة:" if lang == "ar" else "Choose your package:"
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "lang_ar":
        context.user_data["lang"] = "ar"
        await show_packages(q, context)

    elif data == "lang_en":
        context.user_data["lang"] = "en"
        await show_packages(q, context)

    elif data.startswith("pkg_"):
        package_key = data.replace("pkg_", "")
        context.user_data["package_key"] = package_key
        context.user_data["package_name"], context.user_data["package_price"] = PACKAGES[package_key]

        keyboard = [
            [
                InlineKeyboardButton("نعم / Yes", callback_data="music_yes"),
                InlineKeyboardButton("لا / No", callback_data="music_no")
            ]
        ]
        await q.edit_message_text(
            "هل تريد إضافة موسيقى AI؟ السعر 100 QAR\nDo you want AI Music add-on? 100 QAR",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data.startswith("music_"):
        context.user_data["ai_music"] = "Yes" if data == "music_yes" else "No"
        context.user_data["step"] = "name"
        await q.edit_message_text("اكتب اسمك:")

    elif data.startswith("accept_") or data.startswith("reject_"):
        action, user_id = data.split("_")
        user_id = int(user_id)

        if action == "accept":
            msg = "تم قبول طلبك ✅\nYour request has been accepted ✅"
            admin_msg = "تم قبول الطلب ✅"
        else:
            msg = "تم رفض طلبك ❌\nYour request has been rejected ❌"
            admin_msg = "تم رفض الطلب ❌"

        await context.bot.send_message(chat_id=user_id, text=msg)
        await q.edit_message_text(admin_msg)

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")
    text = update.message.text.strip()

    if not step:
        await update.message.reply_text("اكتب /start للبدء")
        return

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

        package_name = context.user_data["package_name"]
        package_price = context.user_data["package_price"]
        ai_music = context.user_data["ai_music"]
        ai_price = 100 if ai_music == "Yes" else 0
        total = package_price + ai_price
        user_id = update.effective_user.id

        summary = f"""
طلب جديد من SADU

الاسم: {context.user_data['name']}
الإيميل: {context.user_data['email']}
السيارة: {context.user_data['car']}
التاريخ: {context.user_data['date']}

الباقة: {package_name}
سعر الباقة: {package_price} QAR
AI Music: {ai_music}
الإجمالي: {total} QAR

User ID: {user_id}
"""

        keyboard = [
            [
                InlineKeyboardButton("قبول ✅", callback_data=f"accept_{user_id}"),
                InlineKeyboardButton("رفض ❌", callback_data=f"reject_{user_id}")
            ]
        ]

        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=summary,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        await update.message.reply_text(
            "تم إرسال طلبك بنجاح ✅\nYour request has been sent successfully."
        )

        context.user_data.clear()

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()

if __name__ == "__main__":
    main()

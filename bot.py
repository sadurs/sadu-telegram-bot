import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "6856205408"))

PACKAGES = {
    "basic": ("الباقة الأساسية / Basic", 100),
    "pro": ("الباقة الاحترافية / Professional", 200),
    "complete": ("الباقة المتكاملة / Complete", 450),
}

ADDONS = {
    "fast": ("التسليم السريع خلال 45 دقيقة", 150),
    "extra10": ("زيادة مدة المقطع 10 ثواني", 100),
    "music": ("إنشاء موسيقى AI", 100),
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("العربية", callback_data="lang_ar")],
        [InlineKeyboardButton("English", callback_data="lang_en")]
    ]
    await update.message.reply_text(
        "اختر اللغة / Choose language:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data.startswith("lang_"):
        context.user_data["lang"] = data.replace("lang_", "")
        context.user_data["step"] = "name"
        await q.edit_message_text("اكتب اسمك الكامل:" if context.user_data["lang"] == "ar" else "Enter your full name:")

    elif data.startswith("pkg_"):
        key = data.replace("pkg_", "")
        context.user_data["package_name"], context.user_data["package_price"] = PACKAGES[key]
        context.user_data["addons"] = []
        await show_addons(q, context)

    elif data.startswith("addon_"):
        key = data.replace("addon_", "")
        if key in context.user_data["addons"]:
            context.user_data["addons"].remove(key)
        else:
            context.user_data["addons"].append(key)
        await show_addons(q, context)

    elif data == "done_addons":
        await show_payment(q, context)

    elif data.startswith("pay_"):
        context.user_data["payment"] = "كاش / Cash" if data == "pay_cash" else "فورا / Fawra"
        await send_summary(q, context)

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

async def show_packages(update, context):
    keyboard = [
        [InlineKeyboardButton("الباقة الأساسية - 100 QAR", callback_data="pkg_basic")],
        [InlineKeyboardButton("الباقة الاحترافية - 200 QAR", callback_data="pkg_pro")],
        [InlineKeyboardButton("الباقة المتكاملة - 450 QAR", callback_data="pkg_complete")],
    ]
    await update.message.reply_text("اختر الباقة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_addons(q, context):
    selected = context.user_data.get("addons", [])
    keyboard = []
    for key, (name, price) in ADDONS.items():
        mark = "✅" if key in selected else "⬜"
        keyboard.append([InlineKeyboardButton(f"{mark} {name} +{price} QAR", callback_data=f"addon_{key}")])
    keyboard.append([InlineKeyboardButton("تم اختيار الإضافات ✅", callback_data="done_addons")])
    await q.edit_message_text("اختر الإضافات المطلوبة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_payment(q, context):
    keyboard = [
        [InlineKeyboardButton("كاش / Cash", callback_data="pay_cash")],
        [InlineKeyboardButton("فورا / Fawra", callback_data="pay_fawra")]
    ]
    await q.edit_message_text("اختر طريقة الدفع:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")
    text = update.message.text.strip()

    if step == "name":
        context.user_data["name"] = text
        context.user_data["step"] = "phone"
        await update.message.reply_text("اكتب رقم الهاتف:")

    elif step == "phone":
        context.user_data["phone"] = text
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
        context.user_data["step"] = "time"
        await update.message.reply_text("اكتب الوقت المناسب للتصوير:")

    elif step == "time":
        context.user_data["time"] = text
        context.user_data["step"] = "notes"
        await update.message.reply_text("اكتب أي ملاحظات إضافية، أو اكتب: لا يوجد")

    elif step == "notes":
        context.user_data["notes"] = text
        context.user_data["step"] = "package"
        await show_packages(update, context)

    else:
        await update.message.reply_text("اكتب /start للبدء")

async def send_summary(q, context):
    data = context.user_data

    package_price = data["package_price"]
    addons_total = 0
    addon_lines = []

    for key in data.get("addons", []):
        name, price = ADDONS[key]
        addon_lines.append(f"✅ {name}: +{price} QAR")
        addons_total += price

    addons_text = "\n".join(addon_lines) if addon_lines else "لا توجد إضافات"
    total = package_price + addons_total
    user_id = q.from_user.id

    payment_note = ""
    if data["payment"] == "فورا / Fawra":
        payment_note = "\n🔁 اسم التحويل فورا: ALIMRI"

    summary = f"""
🚘 طلب جديد من SADU

👤 الاسم: {data['name']}
📱 الهاتف: {data['phone']}
📧 الإيميل: {data['email']}

🚗 السيارة: {data['car']}
📅 التاريخ: {data['date']}
🕒 الوقت: {data['time']}

📦 الباقة:
{data['package_name']}
السعر: {package_price} QAR

➕ الإضافات:
{addons_text}

💳 طريقة الدفع:
{data['payment']}
{payment_note}

📝 الملاحظات:
{data['notes']}

💰 الإجمالي: {total} QAR

Telegram ID: {user_id}
"""

    keyboard = [[
        InlineKeyboardButton("قبول ✅", callback_data=f"accept_{user_id}"),
        InlineKeyboardButton("رفض ❌", callback_data=f"reject_{user_id}")
    ]]

    client_msg = "تم إرسال طلبك بنجاح ✅\nYour request has been sent successfully."
    if data["payment"] == "فورا / Fawra":
        client_msg += "\n\nللدفع عبر فورا:\nاسم التحويل: ALIMRI"

    await q.message.reply_text(client_msg)
    await context.bot.send_message(ADMIN_CHAT_ID, summary, reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data.clear()

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.run_polling()

if __name__ == "__main__":
    main()

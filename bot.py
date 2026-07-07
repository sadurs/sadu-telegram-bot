import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "6856205408"))

PACKAGES = {
    "basic": ("🎬 الباقة الأساسية / Basic", 100),
    "pro": ("🎥 الباقة الاحترافية / Professional", 200),
    "complete": ("🚘 الباقة المتكاملة / Complete", 450),
}

ADDONS = {
    "fast": ("⚡ التسليم السريع خلال 45 دقيقة", 150),
    "extra10": ("⏱️ زيادة مدة المقطع 10 ثواني", 100),
    "music": ("🎵 إنشاء موسيقى AI", 100),
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("🇶🇦 العربية", callback_data="lang_ar")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
    ]
    await update.message.reply_text(
        "🚘 أهلاً بك في بوت SADU الرسمي\n\nاختر اللغة / Choose language:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_packages(q, context):
    keyboard = [
        [InlineKeyboardButton("🎬 الأساسية - 100 QAR", callback_data="pkg_basic")],
        [InlineKeyboardButton("🎥 الاحترافية - 200 QAR", callback_data="pkg_pro")],
        [InlineKeyboardButton("🚘 المتكاملة - 450 QAR", callback_data="pkg_complete")],
    ]
    await q.edit_message_text("📦 اختر الباقة المناسبة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def show_addons(q, context):
    selected = context.user_data.get("addons", [])
    keyboard = []

    for key, (name, price) in ADDONS.items():
        mark = "✅" if key in selected else "⬜"
        keyboard.append([InlineKeyboardButton(f"{mark} {name} +{price} QAR", callback_data=f"addon_{key}")])

    keyboard.append([InlineKeyboardButton("✅ متابعة", callback_data="done_addons")])

    await q.edit_message_text(
        "➕ اختر الإضافات المطلوبة:\n\nيمكنك اختيار أكثر من إضافة.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_payment(q):
    keyboard = [
        [InlineKeyboardButton("💵 كاش / Cash", callback_data="pay_cash")],
        [InlineKeyboardButton("🔁 فورا / Fawra", callback_data="pay_fawra")]
    ]
    await q.edit_message_text("💳 اختر طريقة الدفع:", reply_markup=InlineKeyboardMarkup(keyboard))

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data.startswith("lang_"):
        context.user_data["lang"] = data.replace("lang_", "")
        await show_packages(q, context)

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
        await show_payment(q)

    elif data.startswith("pay_"):
        context.user_data["payment"] = "💵 كاش / Cash" if data == "pay_cash" else "🔁 فورا / Fawra"
        context.user_data["step"] = "name"
        await q.edit_message_text("👤 اكتب اسمك الكامل:")

    elif data.startswith("accept_"):
        user_id = int(data.replace("accept_", ""))

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 تم قبول طلبك بنجاح!\n\n"
                "شكراً لاختيارك SADU 🚘\n\n"
                "📱 سيتم التواصل معك عبر واتساب لتحديد موعد ومكان التصوير.\n\n"
                "💳 طريقة الدفع:\n"
                "إذا اخترت الكاش: يتم الدفع يوم التصوير.\n"
                "إذا اخترت فورا: التحويل إلى الاسم التالي:\n"
                "👤 ALIMRI\n\n"
                "📤 بعد التحويل يمكنك إرسال صورة الإيصال داخل هذا البوت."
            )
        )
        await q.edit_message_text("✅ تم قبول الطلب وإرسال رسالة القبول للعميل.")

    elif data.startswith("reject_"):
        user_id = int(data.replace("reject_", ""))
        context.user_data["step"] = "reject_reason"
        context.user_data["rejecting_user_id"] = user_id
        await q.edit_message_text("❌ اكتب سبب رفض الطلب، وسيتم إرساله للعميل:")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")
    text = update.message.text.strip()

    if step == "reject_reason":
        user_id = context.user_data.get("rejecting_user_id")
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "❌ نعتذر، لم يتم قبول طلبك.\n\n"
                f"📝 سبب الرفض:\n{text}\n\n"
                "إذا رغبت في تعديل الطلب يمكنك إرسال طلب جديد في أي وقت.\n\n"
                "شكراً لاختيارك SADU 🚘"
            )
        )
        await update.message.reply_text("✅ تم إرسال سبب الرفض للعميل.")
        context.user_data.clear()
        return

    if step == "name":
        context.user_data["name"] = text
        context.user_data["step"] = "phone"
        await update.message.reply_text("📱 اكتب رقم الهاتف:")

    elif step == "phone":
        context.user_data["phone"] = text
        context.user_data["step"] = "email"
        await update.message.reply_text("📧 اكتب البريد الإلكتروني:")

    elif step == "email":
        context.user_data["email"] = text
        context.user_data["step"] = "car"
        await update.message.reply_text("🚗 اكتب موديل السيارة:")

    elif step == "car":
        context.user_data["car"] = text
        context.user_data["step"] = "date"
        await update.message.reply_text("📅 اكتب تاريخ التصوير المناسب:")

    elif step == "date":
        context.user_data["date"] = text
        context.user_data["step"] = "time"
        await update.message.reply_text("🕒 اكتب الوقت المناسب للتصوير:")

    elif step == "time":
        context.user_data["time"] = text
        context.user_data["step"] = "notes"
        await update.message.reply_text("📝 اكتب أي ملاحظات إضافية، أو اكتب: لا يوجد")

    elif step == "notes":
        context.user_data["notes"] = text
        await send_summary_from_text(update, context)

    else:
        await update.message.reply_text("اكتب /start للبدء من جديد.")

async def send_summary_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data

    package_price = data["package_price"]
    addons_total = 0
    addon_lines = []

    for key in data.get("addons", []):
        name, price = ADDONS[key]
        addon_lines.append(f"{name}: +{price} QAR")
        addons_total += price

    addons_text = "\n".join(addon_lines) if addon_lines else "لا توجد إضافات"
    total = package_price + addons_total
    user_id = update.effective_user.id

    payment_note = ""
    if data["payment"] == "🔁 فورا / Fawra":
        payment_note = "\n🔁 اسم التحويل فورا: ALIMRI"

    summary = f"""
🚘 طلب جديد من SADU

📦 الباقة:
{data['package_name']}
💰 سعر الباقة: {package_price} QAR

➕ الإضافات:
{addons_text}

💳 طريقة الدفع:
{data['payment']}
{payment_note}

👤 الاسم: {data['name']}
📱 الهاتف: {data['phone']}
📧 الإيميل: {data['email']}

🚗 السيارة: {data['car']}
📅 التاريخ: {data['date']}
🕒 الوقت: {data['time']}

📝 الملاحظات:
{data['notes']}

💵 الإجمالي النهائي: {total} QAR

🆔 Telegram ID: {user_id}
"""

    keyboard = [[
        InlineKeyboardButton("✅ قبول الطلب", callback_data=f"accept_{user_id}"),
        InlineKeyboardButton("❌ رفض الطلب", callback_data=f"reject_{user_id}")
    ]]

    await update.message.reply_text(
        "✅ تم إرسال طلبك بنجاح\n\nسيتم مراجعة الطلب والرد عليك قريبًا."
    )

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=summary,
        reply_markup=InlineKeyboardMarkup(keyboard)
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

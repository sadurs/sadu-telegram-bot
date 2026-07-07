import os
import html
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

TIKTOK_URL = "https://www.tiktok.com/@ar.q6r"
FAWRA_NAME = "ALIMRI"

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


def esc(value):
    return html.escape(str(value))


def user_lang(context):
    return context.user_data.get("lang", "ar")


def txt(context, ar, en):
    return ar if user_lang(context) == "ar" else en


def calc_total(data):
    package_price = data.get("package_price", 0)
    addons_total = 0
    addon_lines = []

    for key in data.get("addons", []):
        name, price = ADDONS[key]
        addon_lines.append(f"{name}: +{price} QAR")
        addons_total += price

    addons_text = "\n".join(addon_lines) if addon_lines else "لا توجد إضافات"
    total = package_price + addons_total
    return addons_text, total


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    keyboard = [
        [InlineKeyboardButton("🇶🇦 العربية", callback_data="lang_ar")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
    ]

    await update.message.reply_text(
        "🚘 أهلاً بك في بوت SADU الرسمي\n\n"
        "Welcome to the official SADU booking bot\n\n"
        "اختر اللغة / Choose language:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_terms(q, context):
    terms = """
📜 <b>الشروط والأحكام</b>

✅ جميع الأسعار بالريال القطري QAR.

✅ يتم تأكيد الحجز بعد مراجعة الطلب وقبوله من فريق SADU.

✅ في حال اختيار الدفع عبر خدمة فورا، يجب تحويل المبلغ إلى:
<b>ALIMRI</b>
ثم إرسال صورة إيصال الدفع داخل البوت.

✅ في حال اختيار الدفع كاش، يتم الدفع يوم التصوير.

✅ يحق لفريق SADU قبول أو رفض أي طلب مع توضيح السبب عند الرفض.

✅ يلتزم العميل بتقديم بيانات صحيحة، وخاصة رقم الهاتف للتواصل عبر واتساب.

✅ سيتم التواصل مع العميل عبر واتساب لتحديد موعد ومكان التصوير بعد قبول الطلب.

✅ يوافق العميل على منح SADU الحق في استخدام ونشر الصور ومقاطع الفيديو الناتجة عن جلسة التصوير لأغراض التسويق والعرض على حساباتنا في منصات التواصل، بما في ذلك TikTok:
https://www.tiktok.com/@ar.q6r

✅ إذا كان العميل لا يرغب في نشر المحتوى، يجب توضيح ذلك في خانة الملاحظات قبل إرسال الطلب.

☑️ بالضغط على "أوافق"، فإنك تقر بأنك قرأت الشروط والأحكام ووافقت عليها.
"""

    keyboard = [
        [InlineKeyboardButton("✅ أوافق / I Agree", callback_data="terms_accept")],
        [InlineKeyboardButton("❌ لا أوافق / I Don’t Agree", callback_data="terms_decline")],
    ]

    await q.edit_message_text(
        terms,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True,
    )


async def show_packages(q, context):
    keyboard = [
        [InlineKeyboardButton("🎬 الأساسية - 100 QAR", callback_data="pkg_basic")],
        [InlineKeyboardButton("🎥 الاحترافية - 200 QAR", callback_data="pkg_pro")],
        [InlineKeyboardButton("🚘 المتكاملة - 450 QAR", callback_data="pkg_complete")],
    ]

    await q.edit_message_text(
        txt(context, "📦 اختر الباقة المناسبة:", "📦 Choose your package:"),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_addons(q, context):
    selected = context.user_data.get("addons", [])
    keyboard = []

    for key, (name, price) in ADDONS.items():
        mark = "✅" if key in selected else "⬜"
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{mark} {name} +{price} QAR",
                    callback_data=f"addon_{key}",
                )
            ]
        )

    keyboard.append([InlineKeyboardButton("✅ متابعة / Continue", callback_data="done_addons")])

    await q.edit_message_text(
        txt(
            context,
            "➕ اختر الإضافات المطلوبة:\n\nيمكنك اختيار أكثر من إضافة.",
            "➕ Choose add-ons:\n\nYou can select more than one add-on.",
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def show_payment(q, context):
    keyboard = [
        [InlineKeyboardButton("💵 كاش / Cash", callback_data="pay_cash")],
        [InlineKeyboardButton("🔁 فورا / Fawra", callback_data="pay_fawra")],
    ]

    await q.edit_message_text(
        txt(context, "💳 اختر طريقة الدفع:", "💳 Choose payment method:"),
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def ask_next_after_payment(q, context):
    context.user_data["step"] = "name"
    await q.edit_message_text(
        txt(context, "👤 اكتب اسمك الكامل:", "👤 Enter your full name:")
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data.startswith("lang_"):
        context.user_data["lang"] = data.replace("lang_", "")
        await show_terms(q, context)

    elif data == "terms_accept":
        await show_packages(q, context)

    elif data == "terms_decline":
        context.user_data.clear()
        await q.edit_message_text(
            "تم إلغاء الطلب لأنك لم توافق على الشروط والأحكام.\n\n"
            "Booking cancelled because terms and conditions were not accepted."
        )

    elif data.startswith("pkg_"):
        key = data.replace("pkg_", "")
        context.user_data["package_key"] = key
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
        context.user_data["payment"] = "💵 كاش / Cash" if data == "pay_cash" else "🔁 فورا / Fawra"
        await ask_next_after_payment(q, context)

    elif data.startswith("accept_"):
        user_id = int(data.replace("accept_", ""))

        msg = (
            "🎉 تم قبول طلبك بنجاح!\n\n"
            "شكراً لاختيارك SADU 🚘\n\n"
            "📱 سيتم التواصل معك عبر واتساب لتحديد موعد ومكان التصوير.\n\n"
            "💳 تفاصيل الدفع:\n"
            "💵 إذا اخترت الكاش: يتم الدفع يوم التصوير.\n"
            f"🔁 إذا اخترت فورا: يرجى التحويل إلى الاسم التالي:\n{FAWRA_NAME}\n\n"
            "📤 بعد التحويل يمكنك إرسال صورة الإيصال داخل هذا البوت."
        )

        await context.bot.send_message(chat_id=user_id, text=msg)
        await q.edit_message_text("✅ تم قبول الطلب وإرسال رسالة القبول والدفع للعميل.")

    elif data.startswith("reject_"):
        user_id = int(data.replace("reject_", ""))
        context.user_data["step"] = "reject_reason"
        context.user_data["rejecting_user_id"] = user_id
        await q.edit_message_text("❌ اكتب سبب رفض الطلب، وسيتم إرساله للعميل:")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")
    text_value = update.message.text.strip()

    if step == "reject_reason":
        user_id = context.user_data.get("rejecting_user_id")
        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "❌ نعتذر، لم يتم قبول طلبك.\n\n"
                f"📝 سبب الرفض:\n{text_value}\n\n"
                "يمكنك تعديل الطلب وإرسال طلب جديد في أي وقت.\n\n"
                "شكراً لاختيارك SADU 🚘"
            ),
        )
        await update.message.reply_text("✅ تم إرسال سبب الرفض للعميل.")
        context.user_data.clear()
        return

    if step == "name":
        context.user_data["name"] = text_value
        context.user_data["step"] = "phone"
        await update.message.reply_text(
            txt(context, "📱 اكتب رقم الهاتف:", "📱 Enter your phone number:")
        )

    elif step == "phone":
        context.user_data["phone"] = text_value
        context.user_data["step"] = "email"
        await update.message.reply_text(
            txt(context, "📧 اكتب البريد الإلكتروني:", "📧 Enter your email:")
        )

    elif step == "email":
        context.user_data["email"] = text_value
        context.user_data["step"] = "car"
        await update.message.reply_text(
            txt(context, "🚗 اكتب موديل السيارة:", "🚗 Enter car model:")
        )

    elif step == "car":
        context.user_data["car"] = text_value
        context.user_data["step"] = "date"
        await update.message.reply_text(
            txt(context, "📅 اكتب تاريخ التصوير المناسب:", "📅 Enter preferred shooting date:")
        )

    elif step == "date":
        context.user_data["date"] = text_value
        context.user_data["step"] = "time"
        await update.message.reply_text(
            txt(context, "🕒 اكتب الوقت المناسب للتصوير:", "🕒 Enter preferred shooting time:")
        )

    elif step == "time":
        context.user_data["time"] = text_value
        context.user_data["step"] = "notes"
        await update.message.reply_text(
            txt(
                context,
                "📝 اكتب أي ملاحظات إضافية، أو اكتب: لا يوجد",
                "📝 Enter any additional notes, or write: None",
            )
        )

    elif step == "notes":
        context.user_data["notes"] = text_value
        await send_summary(update, context)

    else:
        await update.message.reply_text("اكتب /start للبدء من جديد.")


async def send_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data

    addons_text, total = calc_total(data)
    user_id = update.effective_user.id

    payment_note = ""
    if data["payment"] == "🔁 فورا / Fawra":
        payment_note = f"\n🔁 اسم التحويل فورا: {FAWRA_NAME}"

    publish_note = (
        "✅ وافق العميل على الشروط والأحكام، بما في ذلك حق SADU في نشر المحتوى "
        f"لأغراض التسويق على TikTok: {TIKTOK_URL}"
    )

    summary = f"""
🚘 <b>طلب جديد من SADU</b>

📦 <b>الباقة:</b>
{esc(data['package_name'])}
💰 <b>سعر الباقة:</b> {data['package_price']} QAR

➕ <b>الإضافات:</b>
{esc(addons_text)}

💳 <b>طريقة الدفع:</b>
{esc(data['payment'])}
{esc(payment_note)}

👤 <b>الاسم:</b> {esc(data['name'])}
📱 <b>الهاتف:</b> {esc(data['phone'])}
📧 <b>الإيميل:</b> {esc(data['email'])}

🚗 <b>السيارة:</b> {esc(data['car'])}
📅 <b>التاريخ:</b> {esc(data['date'])}
🕒 <b>الوقت:</b> {esc(data['time'])}

📝 <b>الملاحظات:</b>
{esc(data['notes'])}

💵 <b>الإجمالي النهائي:</b> {total} QAR

📜 <b>الشروط:</b>
{esc(publish_note)}

🆔 <b>Telegram ID:</b> {user_id}
"""

    keyboard = [
        [
            InlineKeyboardButton("✅ قبول الطلب", callback_data=f"accept_{user_id}"),
            InlineKeyboardButton("❌ رفض الطلب", callback_data=f"reject_{user_id}"),
        ]
    ]

    await update.message.reply_text(
        txt(
            context,
            "✅ تم إرسال طلبك بنجاح\n\n⏳ سيتم مراجعة الطلب والرد عليك قريبًا.",
            "✅ Your request has been submitted successfully.\n\n⏳ We will review it and reply soon.",
        )
    )

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=summary,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True,
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

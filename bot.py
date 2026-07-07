import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "6856205408"))

DB_FILE = "sadu_orders.db"
TIKTOK_URL = "https://www.tiktok.com/@ar.q6r"
FAWRA_NAME = "ALIMRI"
MOVMAX_IMAGE = "movmax.jpg"

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

DISCOUNT_CODES = {"SR26": 10}


def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT UNIQUE,
            user_id INTEGER,
            name TEXT,
            phone TEXT,
            email TEXT,
            car TEXT,
            date TEXT,
            time TEXT,
            package TEXT,
            addons TEXT,
            payment TEXT,
            discount_code TEXT,
            discount_percent INTEGER,
            discount_amount INTEGER,
            subtotal INTEGER,
            total INTEGER,
            notes TEXT,
            status TEXT DEFAULT 'new',
            full_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def next_order_no(order_id):
    return f"SR-{order_id:04d}"


def calc_total(data):
    addons_total = 0
    addon_lines = []

    for key in data.get("addons", []):
        name, price = ADDONS[key]
        addon_lines.append(f"{name}: +{price} QAR")
        addons_total += price

    subtotal = data.get("package_price", 0) + addons_total
    discount_percent = data.get("discount_percent", 0)
    discount_amount = round(subtotal * discount_percent / 100)
    total = subtotal - discount_amount
    addons_text = "\n".join(addon_lines) if addon_lines else "لا توجد إضافات"
    return addons_text, subtotal, discount_amount, total


def save_order(data, user_id, full_message, addons_text, subtotal, discount_amount, total):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO orders (
            user_id, name, phone, email, car, date, time,
            package, addons, payment, discount_code, discount_percent,
            discount_amount, subtotal, total, notes, status, full_message
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        data.get("name"),
        data.get("phone"),
        data.get("email"),
        data.get("car"),
        data.get("date"),
        data.get("time"),
        data.get("package_name"),
        addons_text,
        data.get("payment"),
        data.get("discount_code", "لا يوجد"),
        data.get("discount_percent", 0),
        discount_amount,
        subtotal,
        total,
        data.get("notes"),
        "new",
        full_message
    ))

    order_id = cur.lastrowid
    order_no = next_order_no(order_id)
    cur.execute("UPDATE orders SET order_no=? WHERE id=?", (order_no, order_id))

    conn.commit()
    conn.close()
    return order_no


def update_order_status(order_no, status):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status=? WHERE order_no=?", (status, order_no))
    conn.commit()
    conn.close()


def get_order(order_no):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
        SELECT order_no, user_id, name, phone, car, total, status, created_at
        FROM orders
        WHERE order_no=?
    """, (order_no,))
    row = cur.fetchone()
    conn.close()
    return row


def fetch_orders(status=None, limit=10):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    if status:
        cur.execute("""
            SELECT order_no, name, phone, total, status, created_at
            FROM orders
            WHERE status=?
            ORDER BY id DESC
            LIMIT ?
        """, (status, limit))
    else:
        cur.execute("""
            SELECT order_no, name, phone, total, status, created_at
            FROM orders
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))

    rows = cur.fetchall()
    conn.close()
    return rows


def format_status(status):
    return {
        "new": "🟡 قيد المراجعة",
        "accepted": "✅ مقبول",
        "rejected": "❌ مرفوض",
        "completed": "🎬 مكتمل وتم إرسال المقطع",
    }.get(status, status)


def format_orders(rows, title):
    if not rows:
        return f"{title}\n\nلا توجد طلبات."

    msg = f"{title}\n\n"
    for order_no, name, phone, total, status, created_at in rows:
        msg += (
            f"🆔 {order_no}\n"
            f"👤 {name}\n"
            f"📱 {phone}\n"
            f"💰 {total} QAR\n"
            f"📌 {format_status(status)}\n"
            f"🕒 {created_at}\n\n"
        )
    return msg


def main_menu_keyboard(user_id):
    keyboard = [
        [InlineKeyboardButton("🚘 حجز جديد", callback_data="start_booking")],
        [InlineKeyboardButton("🛒 متجر SADU", callback_data="store")],
        [InlineKeyboardButton("🔎 الاستعلام عن حالة الطلب", callback_data="check_order")],
    ]

    if user_id == ADMIN_CHAT_ID:
        keyboard.append([InlineKeyboardButton("🛠 لوحة التحكم", callback_data="admin_panel")])

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "🚘 أهلاً بك في بوت SADU الرسمي\n\nاختر الخدمة المطلوبة:",
        reply_markup=main_menu_keyboard(update.effective_user.id)
    )


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    await send_admin_panel(update.message)


async def send_admin_panel(message):
    keyboard = [
        [
            InlineKeyboardButton("📋 آخر الطلبات", callback_data="admin_orders"),
            InlineKeyboardButton("🆕 الجديدة", callback_data="admin_new"),
        ],
        [
            InlineKeyboardButton("✅ المقبولة", callback_data="admin_accepted"),
            InlineKeyboardButton("❌ المرفوضة", callback_data="admin_rejected"),
        ],
        [
            InlineKeyboardButton("🎬 إرسال مقطع للعميل", callback_data="admin_send_video"),
        ],
        [
            InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats"),
            InlineKeyboardButton("🎁 أكواد الخصم", callback_data="admin_discounts"),
        ],
    ]

    await message.reply_text(
        "🛠 لوحة تحكم SADU\n\nاختر من القائمة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_store(q):
    caption = """
🛒 متجر SADU

🚗 MOVMAX Electronic Suction Cup + Blade Arm

ستاند احترافي لتصوير السيارات والرولنق شوت، مزود بشفاط إلكتروني وذراع تثبيت يساعد على تقليل الاهتزاز أثناء التصوير.

✅ المميزات:
• شفاط إلكتروني لتثبيت أقوى
• ذراع MOVMAX Blade Arm
• مناسب لتصوير Rolling Shots
• مناسب لصناع المحتوى ومصوري السيارات
• يعطي لقطات أكثر ثباتًا وسلاسة

📷 يدعم:
• DJI Pocket 3
• DJI Pocket 4
• GoPro
• Insta360
• كاميرات الأكشن الخفيفة

📌 الحالة:
⏳ سيتوفر قريبًا

للاستفسار:
@sadu_services_bot
"""

    keyboard = [[InlineKeyboardButton("⬅️ رجوع", callback_data="back_start")]]

    if os.path.exists(MOVMAX_IMAGE):
        with open(MOVMAX_IMAGE, "rb") as photo:
            await q.message.reply_photo(
                photo=photo,
                caption=caption,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        await q.delete_message()
    else:
        await q.edit_message_text(
            caption + "\n\n⚠️ لم يتم العثور على صورة المنتج. تأكد أن اسم الصورة movmax.jpg",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


async def show_terms(q):
    keyboard = [
        [InlineKeyboardButton("✅ أوافق / I Agree", callback_data="terms_accept")],
        [InlineKeyboardButton("❌ لا أوافق", callback_data="terms_decline")]
    ]

    await q.edit_message_text(
        f"""
📜 الشروط والأحكام

✅ جميع الأسعار بالريال القطري QAR.

✅ يتم تأكيد الحجز بعد مراجعة الطلب وقبوله من فريق SADU.

✅ عند اختيار فورا، يتم التحويل إلى:
{FAWRA_NAME}

✅ يحق لـ SADU قبول أو رفض أي طلب مع توضيح السبب.

✅ سيتم التواصل مع العميل عبر واتساب لتحديد موعد ومكان التصوير.

✅ يوافق العميل على حق SADU في نشر الصور والمقاطع لأغراض التسويق على حسابنا:
{TIKTOK_URL}

✅ إذا لا ترغب بنشر المحتوى، اكتب ذلك في الملاحظات.

☑️ بالضغط على أوافق، فإنك تقر بقراءة الشروط والموافقة عليها.
""",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )


async def show_packages(q):
    keyboard = [
        [InlineKeyboardButton("🎬 الأساسية - 100 QAR", callback_data="pkg_basic")],
        [InlineKeyboardButton("🎥 الاحترافية - 200 QAR", callback_data="pkg_pro")],
        [InlineKeyboardButton("🚘 المتكاملة - 450 QAR", callback_data="pkg_complete")]
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


async def ask_discount(q):
    keyboard = [
        [InlineKeyboardButton("✅ نعم، لدي كود خصم", callback_data="discount_yes")],
        [InlineKeyboardButton("❌ لا يوجد", callback_data="discount_no")]
    ]
    await q.edit_message_text("🎁 هل لديك كود خصم؟", reply_markup=InlineKeyboardMarkup(keyboard))


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "start_booking":
        keyboard = [
            [InlineKeyboardButton("🇶🇦 العربية", callback_data="lang_ar")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")]
        ]
        await q.edit_message_text(
            "🌐 اختر اللغة / Choose language:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "store":
        await show_store(q)

    elif data == "back_start":
        await q.edit_message_text(
            "🚘 أهلاً بك في بوت SADU الرسمي\n\nاختر الخدمة المطلوبة:",
            reply_markup=main_menu_keyboard(q.from_user.id)
        )

    elif data == "check_order":
        context.user_data["step"] = "check_order"
        await q.edit_message_text("🔎 اكتب رقم الطلب مثل:\nSR-0001")

    elif data == "admin_panel":
        if q.from_user.id != ADMIN_CHAT_ID:
            return
        keyboard = [
            [InlineKeyboardButton("📋 آخر الطلبات", callback_data="admin_orders")],
            [InlineKeyboardButton("🆕 الطلبات الجديدة", callback_data="admin_new")],
            [InlineKeyboardButton("✅ المقبولة", callback_data="admin_accepted")],
            [InlineKeyboardButton("❌ المرفوضة", callback_data="admin_rejected")],
            [InlineKeyboardButton("🎬 إرسال مقطع للعميل", callback_data="admin_send_video")],
            [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
            [InlineKeyboardButton("🎁 أكواد الخصم", callback_data="admin_discounts")],
        ]
        await q.edit_message_text("🛠 لوحة تحكم SADU", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_orders":
        await q.edit_message_text(format_orders(fetch_orders(None, 10), "📋 آخر الطلبات"))

    elif data == "admin_new":
        await q.edit_message_text(format_orders(fetch_orders("new", 10), "🆕 الطلبات الجديدة"))

    elif data == "admin_accepted":
        await q.edit_message_text(format_orders(fetch_orders("accepted", 10), "✅ الطلبات المقبولة"))

    elif data == "admin_rejected":
        await q.edit_message_text(format_orders(fetch_orders("rejected", 10), "❌ الطلبات المرفوضة"))

    elif data == "admin_send_video":
        if q.from_user.id != ADMIN_CHAT_ID:
            return
        context.user_data["step"] = "delivery_order_no"
        await q.edit_message_text("🎬 اكتب رقم الطلب الذي تريد إرسال المقطع له:\nمثال: SR-0001")

    elif data == "admin_discounts":
        msg = "🎁 أكواد الخصم الحالية:\n\n"
        for code, percent in DISCOUNT_CODES.items():
            msg += f"🏷️ {code} — {percent}%\n"
        await q.edit_message_text(msg)

    elif data == "admin_stats":
        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM orders")
        total_orders = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM orders WHERE status='new'")
        new_orders = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM orders WHERE status='accepted'")
        accepted = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM orders WHERE status='rejected'")
        rejected = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM orders WHERE status='completed'")
        completed = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(total), 0) FROM orders WHERE status IN ('accepted','completed')")
        revenue = cur.fetchone()[0]
        conn.close()

        await q.edit_message_text(
            f"""
📊 إحصائيات SADU

📦 إجمالي الطلبات: {total_orders}
🆕 الجديدة: {new_orders}
✅ المقبولة: {accepted}
❌ المرفوضة: {rejected}
🎬 المكتملة: {completed}

💰 إجمالي المقبول والمكتمل:
{revenue} QAR
"""
        )

    elif data.startswith("lang_"):
        context.user_data["lang"] = data.replace("lang_", "")
        await show_terms(q)

    elif data == "terms_accept":
        await show_packages(q)

    elif data == "terms_decline":
        context.user_data.clear()
        await q.edit_message_text("تم إلغاء الطلب لأنك لم توافق على الشروط والأحكام.")

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
        await show_payment(q)

    elif data.startswith("pay_"):
        context.user_data["payment"] = "💵 كاش / Cash" if data == "pay_cash" else "🔁 فورا / Fawra"
        await ask_discount(q)

    elif data == "discount_yes":
        context.user_data["step"] = "discount_code"
        await q.edit_message_text("📝 أدخل كود الخصم:")

    elif data == "discount_no":
        context.user_data["discount_code"] = "لا يوجد"
        context.user_data["discount_percent"] = 0
        context.user_data["step"] = "name"
        await q.edit_message_text("👤 اكتب اسمك الكامل:")

    elif data.startswith("accept|"):
        _, user_id, order_no = data.split("|")
        update_order_status(order_no, "accepted")

        await context.bot.send_message(
            chat_id=int(user_id),
            text=(
                f"🎉 تم قبول طلبك بنجاح!\n\n"
                f"🆔 رقم الطلب: {order_no}\n\n"
                "📱 سيتم التواصل معك عبر واتساب لتحديد موعد ومكان التصوير.\n\n"
                "💳 تفاصيل الدفع:\n"
                "💵 الكاش: يتم الدفع يوم التصوير.\n"
                f"🔁 فورا: التحويل إلى الاسم التالي:\n{FAWRA_NAME}\n\n"
                "📤 بعد التحويل يمكنك إرسال صورة الإيصال داخل هذا البوت."
            )
        )
        await q.edit_message_text(f"✅ تم قبول الطلب\n🆔 {order_no}")

    elif data.startswith("reject|"):
        _, user_id, order_no = data.split("|")
        context.user_data["step"] = "reject_reason"
        context.user_data["rejecting_user_id"] = int(user_id)
        context.user_data["rejecting_order_no"] = order_no
        await q.edit_message_text(f"❌ اكتب سبب رفض الطلب:\n🆔 {order_no}")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("step")
    text = update.message.text.strip()

    if step == "check_order":
        order_no = text.upper().strip()
        row = get_order(order_no)

        if not row:
            await update.message.reply_text("❌ لم يتم العثور على الطلب.\nتأكد من رقم الطلب وحاول مرة أخرى.")
            return

        order_no, user_id, name, phone, car, total, status, created_at = row

        if update.effective_user.id != user_id and update.effective_user.id != ADMIN_CHAT_ID:
            await update.message.reply_text("❌ لا يمكنك الاستعلام عن هذا الطلب.")
            return

        await update.message.reply_text(
            f"""
📋 حالة الطلب

🆔 رقم الطلب: {order_no}
👤 الاسم: {name}
🚗 السيارة: {car}
💰 الإجمالي: {total} QAR
📌 الحالة: {format_status(status)}
🕒 تاريخ الطلب: {created_at}
"""
        )
        context.user_data.clear()
        return

    if step == "delivery_order_no":
        if update.effective_user.id != ADMIN_CHAT_ID:
            return

        order_no = text.upper().strip()
        row = get_order(order_no)

        if not row:
            await update.message.reply_text("❌ رقم الطلب غير موجود.")
            return

        context.user_data["delivery_order_no"] = order_no
        context.user_data["delivery_user_id"] = row[1]
        context.user_data["step"] = "delivery_file"

        await update.message.reply_text(
            "🎬 الآن أرسل المقطع كملف وليس فيديو:\n\n"
            "اضغط 📎 > File / ملف > اختر المقطع.\n\n"
            "بهذه الطريقة يصل للعميل بأعلى جودة."
        )
        return

    if step == "discount_code":
        code = text.upper().strip()

        if code in ["تخطي", "SKIP", "NO"]:
            context.user_data["discount_code"] = "لا يوجد"
            context.user_data["discount_percent"] = 0
            context.user_data["step"] = "name"
            await update.message.reply_text("👤 اكتب اسمك الكامل:")
            return

        if code in DISCOUNT_CODES:
            context.user_data["discount_code"] = code
            context.user_data["discount_percent"] = DISCOUNT_CODES[code]
            context.user_data["step"] = "name"
            await update.message.reply_text(
                f"🎉 تم تطبيق كود الخصم بنجاح!\n\n"
                f"🏷️ كود الخصم: {code}\n"
                f"🎁 نسبة الخصم: {DISCOUNT_CODES[code]}%\n\n"
                "👤 اكتب اسمك الكامل:"
            )
        else:
            await update.message.reply_text("❌ كود الخصم غير صحيح.\n\nأعد كتابة الكود أو اكتب: تخطي")
        return

    if step == "reject_reason":
        user_id = context.user_data["rejecting_user_id"]
        order_no = context.user_data["rejecting_order_no"]

        update_order_status(order_no, "rejected")

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "❌ نعتذر، لم يتم قبول طلبك.\n\n"
                f"🆔 رقم الطلب: {order_no}\n\n"
                f"📝 سبب الرفض:\n{text}\n\n"
                "يمكنك تعديل الطلب وإرسال طلب جديد في أي وقت.\n\n"
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
        await send_summary(update, context)

    else:
        await update.message.reply_text("اكتب /start للبدء من جديد.")


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return

    if context.user_data.get("step") != "delivery_file":
        return

    order_no = context.user_data["delivery_order_no"]
    user_id = context.user_data["delivery_user_id"]
    document = update.message.document

    await context.bot.send_document(
        chat_id=user_id,
        document=document.file_id,
        caption=(
            f"🎬 تم الانتهاء من مقطعك بنجاح!\n\n"
            f"🆔 رقم الطلب: {order_no}\n\n"
            "تم إرسال المقطع لك كملف للحفاظ على أعلى جودة.\n\n"
            "شكراً لاختيارك SADU 🚘"
        )
    )

    update_order_status(order_no, "completed")

    await update.message.reply_text(
        f"✅ تم إرسال المقطع للعميل بأعلى جودة.\n\n🆔 {order_no}\n📌 الحالة: مكتمل"
    )

    context.user_data.clear()


async def handle_video_wrong(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID:
        return

    if context.user_data.get("step") == "delivery_file":
        await update.message.reply_text(
            "⚠️ أرسلته كفيديو، وهذا قد يقلل الجودة.\n\n"
            "لأعلى جودة:\n"
            "اضغط 📎 > File / ملف > اختر المقطع."
        )


async def send_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    addons_text, subtotal, discount_amount, total = calc_total(data)
    user_id = update.effective_user.id

    payment_note = ""
    if data["payment"] == "🔁 فورا / Fawra":
        payment_note = f"\n🔁 اسم التحويل فورا: {FAWRA_NAME}"

    summary = f"""
🚘 طلب جديد من SADU

📦 الباقة:
{data['package_name']}
💰 سعر الباقة: {data['package_price']} QAR

➕ الإضافات:
{addons_text}

💳 طريقة الدفع:
{data['payment']}
{payment_note}

🎁 كود الخصم:
{data.get('discount_code', 'لا يوجد')}

🏷️ نسبة الخصم:
{data.get('discount_percent', 0)}%

💰 الإجمالي قبل الخصم:
{subtotal} QAR

🎁 قيمة الخصم:
{discount_amount} QAR

✅ الإجمالي بعد الخصم:
{total} QAR

👤 الاسم: {data['name']}
📱 الهاتف: {data['phone']}
📧 الإيميل: {data['email']}

🚗 السيارة: {data['car']}
📅 التاريخ: {data['date']}
🕒 الوقت: {data['time']}

📝 الملاحظات:
{data['notes']}

📜 وافق العميل على الشروط والأحكام وحق SADU في نشر المحتوى على TikTok:
{TIKTOK_URL}

🆔 Telegram ID: {user_id}
"""

    order_no = save_order(data, user_id, summary, addons_text, subtotal, discount_amount, total)

    final_summary = f"""
🚘 طلب جديد من SADU

🆔 رقم الطلب: {order_no}

{summary}
"""

    keyboard = [[
        InlineKeyboardButton("✅ قبول الطلب", callback_data=f"accept|{user_id}|{order_no}"),
        InlineKeyboardButton("❌ رفض الطلب", callback_data=f"reject|{user_id}|{order_no}")
    ]]

    await update.message.reply_text(
        f"✅ تم إرسال طلبك بنجاح\n\n🆔 رقم طلبك: {order_no}\n\n⏳ سيتم مراجعة الطلب والرد عليك قريبًا."
    )

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=final_summary,
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

    context.user_data.clear()


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video_wrong))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling()


if __name__ == "__main__":
    main()

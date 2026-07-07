    elif data.startswith("accept_"):
        user_id = int(data.replace("accept_", ""))

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "تم قبول طلبك ✅\n\n"
                "يرجى إتمام الدفع حسب الطريقة التي اخترتها.\n\n"
                "الدفع كاش: يتم الدفع عند التصوير.\n"
                "الدفع عبر فورا: التحويل إلى الاسم التالي:\n"
                "ALIMRI\n\n"
                "بعد الدفع، أرسل صورة التحويل هنا."
            )
        )

        await q.edit_message_text("تم قبول الطلب وإرسال تعليمات الدفع للعميل ✅")

    elif data.startswith("reject_"):
        user_id = int(data.replace("reject_", ""))

        context.user_data["rejecting_user_id"] = user_id
        context.user_data["step"] = "reject_reason"

        await q.edit_message_text(
            "اكتب سبب رفض الطلب، وسيتم إرساله للعميل."
        )

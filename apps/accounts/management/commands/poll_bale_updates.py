import time

from django.core.management.base import BaseCommand

from apps.accounts.bale_client import answer_pre_checkout_query, get_updates
from apps.accounts.bale_services import try_link_from_update


class Command(BaseCommand):
    help = "پایش مداوم پیام‌های ورودی بله (اتصال حساب + پرداخت حق عضویت) — باید همیشه در پس‌زمینه اجرا شود."

    def handle(self, *args, **options):
        offset = None
        self.stdout.write(self.style.SUCCESS("شروع پایش پیام‌های بله..."))
        while True:
            try:
                result = get_updates(offset=offset, timeout=30)
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"خطا در دریافت آپدیت: {exc}"))
                time.sleep(5)
                continue

            for update in result.get("result", []):
                # ⚠️ نکته‌ی حیاتی: offset باید همیشه جلو برود، حتی اگر
                # پردازش این Update با خطا مواجه شود — وگرنه همان
                # Update خراب تا ابد دوباره دریافت می‌شود (حلقه‌ی بی‌نهایت).
                offset = update["update_id"] + 1
                try:
                    self._process_update(update)
                except Exception as exc:
                    self.stderr.write(self.style.ERROR(f"خطا در پردازش Update {update['update_id']}: {exc}"))

    def _process_update(self, update):
        if "pre_checkout_query" in update:
            self._handle_pre_checkout(update["pre_checkout_query"])
            return

        message = update.get("message")
        if not message:
            return

        if "successful_payment" in message:
            self._handle_successful_payment(message)
            return

        try_link_from_update(update)

    def _handle_pre_checkout(self, query):
        from apps.members.bale_payments import resolve_fee_payload

        self.stdout.write(f"دریافت PreCheckoutQuery: {query['id']} — مبلغ: {query['total_amount']}")
        fee = resolve_fee_payload(query["invoice_payload"])
        if fee is None:
            self.stdout.write(self.style.WARNING(f"payload نامعتبر یا منقضی‌شده: {query['invoice_payload']}"))
            answer_pre_checkout_query(query["id"], ok=False, error_message="این درخواست پرداخت معتبر نیست یا منقضی شده است.")
            return
        if fee.payment_status != "unpaid":
            self.stdout.write(self.style.WARNING(f"حق عضویت {fee.pk} قبلاً پرداخت شده — رد شد."))
            answer_pre_checkout_query(query["id"], ok=False, error_message="این حق عضویت قبلاً پرداخت شده است.")
            return
        answer_pre_checkout_query(query["id"], ok=True)
        self.stdout.write(self.style.SUCCESS(f"PreCheckoutQuery تأیید شد برای حق عضویت {fee.pk}."))

    def _handle_successful_payment(self, message):
        from apps.accounts.bale_client import send_message
        from apps.members.bale_payments import handle_successful_payment

        payment = message["successful_payment"]
        self.stdout.write(f"دریافت SuccessfulPayment — مبلغ: {payment['total_amount']}")
        fee = handle_successful_payment(
            payload=payment["invoice_payload"],
            provider_payment_charge_id=payment.get("provider_payment_charge_id", ""),
        )
        if fee:
            self.stdout.write(self.style.SUCCESS(f"پرداخت حق عضویت {fee.pk} با موفقیت ثبت شد."))
            send_message(message["chat"]["id"], "✅ پرداخت حق عضویت شما با موفقیت ثبت شد. سپاسگزاریم.")
        else:
            self.stdout.write(self.style.ERROR("payload نامعتبر بود — پرداخت موفق ولی هیچ Fee ای پیدا نشد!"))
"""
پرداخت حق عضویت از طریق کیف‌پول بله — payload همیشه امضاشده است تا
هیچ کاربری نتواند با ساختن یک payload جعلی، حق‌عضویت فرد دیگری را
به‌عنوان «پرداخت‌شده توسط خودش» ثبت کند.
"""

from django.core import signing

from .choices import FeePaymentMethod
from .models import MembershipFee

SALT = "behvarzan-bale-fee-payment"


def make_fee_payload(fee):
    return signing.dumps(fee.pk, salt=SALT)


def resolve_fee_payload(payload):
    try:
        fee_id = signing.loads(payload, salt=SALT, max_age=60 * 60 * 24)  # حداکثر ۲۴ ساعت اعتبار
    except signing.BadSignature:
        return None
    return MembershipFee.objects.filter(pk=fee_id).first()


def initiate_fee_payment(fee, user):
    from apps.accounts.bale_client import send_invoice
    from apps.website.utils import full_jalali_date, number_to_persian_words

    if not user.bale_chat_id:
        raise ValueError("این کاربر حساب بله متصل‌شده ندارد.")
    if fee.payment_status != "unpaid":
        raise ValueError("این حق عضویت قبلاً پرداخت شده است.")

    toman_amount = int(fee.amount) // 10
    toman_words = number_to_persian_words(toman_amount)
    jalali_due_date = full_jalali_date(fee.due_date)
    full_name = user.get_full_name() or user.username

    payload = make_fee_payload(fee)
    send_invoice(
        chat_id=user.bale_chat_id,
        title="پرداخت حق عضویت",
        description=(
            f"پرداخت‌کننده: {full_name}\n"
            f"سررسید: {jalali_due_date}\n"
            f"مبلغ: {int(fee.amount):,} ریال (معادل {toman_words} تومان)"
        ),
        payload=payload,
        prices=[{"label": "حق عضویت", "amount": int(fee.amount)}],
    )


def handle_successful_payment(payload, provider_payment_charge_id):
    from django.utils import timezone

    from .services import record_fee_payment

    fee = resolve_fee_payload(payload)
    if fee is None:
        return None
    if fee.payment_status == "unpaid":
        record_fee_payment(
            fee=fee, paid_by=None,
            payment_date=timezone.localdate(),
            payment_method=FeePaymentMethod.BALE,
            reference_number=provider_payment_charge_id,
            is_automated_payment=True,
        )
    return fee
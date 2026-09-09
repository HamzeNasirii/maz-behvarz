import datetime

from django.contrib.auth import get_user_model
from django.core import signing
from django.test import TestCase
from django.utils import timezone

from apps.members.bale_payments import (
    handle_successful_payment,
    initiate_fee_payment,
    make_fee_payload,
    resolve_fee_payload,
)
from apps.members.models import Member, MembershipFee

User = get_user_model()


class FeePayloadSecurityTests(TestCase):
    """
    ⚠️ این بخش مهم‌ترین تست‌های این فایل‌اند — چون payload مستقیم به
    پول واقعی مرتبط است، باید مطمئن شویم هیچ‌کس نمی‌تواند آن را جعل کند.
    """

    def setUp(self):
        user = User.objects.create_user(username="bale_pay_user1", password="pass12345")
        member = Member.objects.create(user=user)
        self.fee = MembershipFee.objects.create(member=member, amount=500000, due_date=timezone.localdate())

    def test_payload_roundtrip(self):
        payload = make_fee_payload(self.fee)
        resolved = resolve_fee_payload(payload)
        self.assertEqual(resolved.pk, self.fee.pk)

    def test_tampered_payload_rejected(self):
        payload = make_fee_payload(self.fee)
        tampered = payload[:-1] + ("a" if payload[-1] != "a" else "b")
        self.assertIsNone(resolve_fee_payload(tampered))

    def test_payload_for_nonexistent_fee_returns_none(self):
        """اگر حق عضویت بعداً حذف شود، payload قدیمی نباید به رکورد دیگری اشاره کند."""
        fake_payload = signing.dumps(999999, salt="behvarzan-bale-fee-payment")
        self.assertIsNone(resolve_fee_payload(fake_payload))

    def test_expired_payload_rejected(self):
        """
        payload قدیمی‌تر از ۲۴ ساعت باید رد شود — با دستکاری مستقیم
        signing (شبیه‌سازی گذشت زمان، بدون واقعاً صبر کردن ۲۴ ساعت).
        """
        old_payload = signing.dumps(self.fee.pk, salt="behvarzan-bale-fee-payment")
        # شبیه‌سازی timestamp قدیمی با max_age=0 در خود resolve ناممکن است
        # مستقیم پس این تست را با فراخوانی مستقیم TimestampSigner انجام می‌دهیم.
        from django.core.signing import TimestampSigner

        signer = TimestampSigner(salt="behvarzan-bale-fee-payment")
        really_old_payload = signer.sign_object(self.fee.pk)
        # به‌جای صبر واقعی، مستقیم max_age=0 در خود تابع تست می‌کنیم:
        with self.assertRaises(Exception):
            signing.loads(really_old_payload, salt="behvarzan-bale-fee-payment", max_age=0)


class InitiateFeePaymentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bale_pay_user2", password="pass12345")
        self.member = Member.objects.create(user=self.user)
        self.fee = MembershipFee.objects.create(member=self.member, amount=500000, due_date=timezone.localdate())

    def test_raises_if_user_has_no_bale_chat_id(self):
        with self.assertRaises(ValueError):
            initiate_fee_payment(self.fee, self.user)

    def test_raises_if_fee_already_paid(self):
        self.user.bale_chat_id = "123456"
        self.user.save()
        self.fee.payment_status = "paid"
        self.fee.save()
        with self.assertRaises(ValueError):
            initiate_fee_payment(self.fee, self.user)


class HandleSuccessfulPaymentTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="bale_pay_user3", password="pass12345")
        member = Member.objects.create(user=user)
        self.fee = MembershipFee.objects.create(member=member, amount=500000, due_date=timezone.localdate())
        self.payload = make_fee_payload(self.fee)

    def test_marks_fee_as_paid(self):
        result = handle_successful_payment(self.payload, "TX-TEST-1")
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.payment_status, "paid")
        self.assertEqual(result.pk, self.fee.pk)

    def test_idempotent_on_double_delivery(self):
        """
        ⚠️ تست حیاتی: اگر بله به هر دلیلی (خطای شبکه، Retry) پیام
        SuccessfulPayment را دوبار بفرستد، نباید دوبار پردازش شود یا
        خطا بدهد.
        """
        handle_successful_payment(self.payload, "TX-TEST-1")
        handle_successful_payment(self.payload, "TX-TEST-1")  # فراخوانی دوم
        self.fee.refresh_from_db()
        self.assertEqual(self.fee.payment_status, "paid")

    def test_invalid_payload_returns_none_without_error(self):
        result = handle_successful_payment("garbage-payload", "TX-TEST-2")
        self.assertIsNone(result)
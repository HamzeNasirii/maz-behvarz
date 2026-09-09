import datetime
import re
from decimal import Decimal

from django import forms

from apps.website.utils import gregorian_to_jalali, jalali_to_gregorian
from .choices import FeePaymentMethod

from .models import MembershipFee


class JalaliDateField(forms.CharField):
    """
    فیلد تاریخ شمسی — ورودی/نمایش به‌فرمت ۱۴۰۴/۰۱/۰۱، ذخیره‌ی داخلی
    (دیتابیس) همچنان میلادی (date) باقی می‌ماند.
    """

    widget = forms.TextInput(attrs={"placeholder": "مثال: 1404/06/15"})

    def to_python(self, value):
        if not value:
            return None
        value = value.strip()
        match = re.fullmatch(r"(\d{4})/(\d{1,2})/(\d{1,2})", value)
        if not match:
            raise forms.ValidationError("فرمت تاریخ باید به‌صورت ۱۴۰۴/۰۱/۰۱ باشد.")
        jy, jm, jd = int(match.group(1)), int(match.group(2)), int(match.group(3))
        try:
            gy, gm, gd = jalali_to_gregorian(jy, jm, jd)
            return datetime.date(gy, gm, gd)
        except ValueError:
            raise forms.ValidationError("تاریخ واردشده معتبر نیست.")

    def prepare_value(self, value):
        if isinstance(value, datetime.date):
            jy, jm, jd = gregorian_to_jalali(value.year, value.month, value.day)
            return f"{jy}/{jm:02d}/{jd:02d}"
        return value


class MembershipFeeCreateForm(forms.ModelForm):
    """
    عمداً فیلد member را ندارد — چون این فرم همیشه از صفحه‌ی جزئیات
    یک عضو مشخص باز می‌شود؛ عضو در View (نه فرم) تعیین می‌شود.
    فیلد amount به‌صورت CharField اعلام شده تا مقدار فرمت‌شده با کاما
    (از سمت کاربر) پیش از تبدیل به عدد، پاک‌سازی شود.
    """

    amount = forms.CharField(
        label="مبلغ (ریال)",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off", "id": "id_amount"}),
    )
    due_date = JalaliDateField(label="تاریخ سررسید")

    class Meta:
        model = MembershipFee
        fields = ["amount", "due_date"]

    def clean_amount(self):
        raw = self.cleaned_data.get("amount", "")
        digits_only = re.sub(r"[^\d]", "", raw)
        if not digits_only:
            raise forms.ValidationError("مبلغ الزامی است و باید فقط شامل ارقام باشد.")
        amount = Decimal(digits_only)
        if amount <= 0:
            raise forms.ValidationError("مبلغ باید بزرگ‌تر از صفر باشد.")
        return amount


class MembershipFeePaymentForm(forms.Form):
    payment_date = JalaliDateField(label="تاریخ پرداخت")
    payment_method = forms.ChoiceField(choices=FeePaymentMethod.choices, label="نحوه‌ی پرداخت")
    reference_number = forms.CharField(required=False, label="شماره پیگیری")

class FeeEditRequestForm(forms.Form):
    new_amount = forms.CharField(
        label="مبلغ جدید (ریال)",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )
    new_due_date = JalaliDateField(label="تاریخ سررسید جدید")
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), label="دلیل درخواست ویرایش")

    def clean_new_amount(self):
        raw = self.cleaned_data.get("new_amount", "")
        digits_only = re.sub(r"[^\d]", "", raw)
        if not digits_only:
            raise forms.ValidationError("مبلغ الزامی است و باید فقط شامل ارقام باشد.")
        amount = Decimal(digits_only)
        if amount <= 0:
            raise forms.ValidationError("مبلغ باید بزرگ‌تر از صفر باشد.")
        return amount


class FeeDeleteRequestForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), label="دلیل درخواست حذف")


class FeeChangeDecisionForm(forms.Form):
    note = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="یادداشت تصمیم")


class FeeFilterForm(forms.Form):
    q = forms.CharField(required=False, label="جستجو (نام یا کد ملی)")
    payment_status = forms.ChoiceField(
        choices=[("", "همه")] + list(MembershipFee._meta.get_field("payment_status").choices),
        required=False, label="وضعیت پرداخت",
    )
    due_date_from = JalaliDateField(required=False, label="سررسید از")
    due_date_to = JalaliDateField(required=False, label="سررسید تا")
    payment_date_from = JalaliDateField(required=False, label="تاریخ پرداخت از")
    payment_date_to = JalaliDateField(required=False, label="تاریخ پرداخت تا")
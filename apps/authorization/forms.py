import datetime
import re

from django import forms

from apps.website.utils import gregorian_to_jalali, jalali_to_gregorian

from .models import RoleAssignment


class JalaliDateField(forms.CharField):
    """
    فیلد تاریخ شمسی — همان الگوی apps/members/fee_forms.py::JalaliDateField
    (Reuse منطقی، بدون کپی مجدد از کتابخانه‌ی خارجی).
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


class RoleAssignmentCreateForm(forms.ModelForm):
    """
    عمداً assigned_by/status/approval_status/approved_by را ندارد —
    این‌ها فقط از طریق Service تعیین می‌شوند، نه فرم (طبق بخش ۴۲ سند).
    """

    start_date = JalaliDateField(label="تاریخ شروع")
    end_date = JalaliDateField(required=False, label="تاریخ پایان (اختیاری)")

    class Meta:
        model = RoleAssignment
        fields = ["user", "role", "access_scope", "start_date", "end_date", "reason"]
        labels = {
            "user": "کاربر", "role": "نقش", "access_scope": "محدوده‌ی دسترسی",
            "reason": "دلیل",
        }


class RoleAssignmentReasonForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=True, label="دلیل")


class RoleAssignmentOptionalReasonForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="دلیل (اختیاری)")
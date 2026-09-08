from django import forms

from .models import Committee, CommitteeMembership
from apps.authorization.forms import JalaliDateField


class CommitteeCreateForm(forms.ModelForm):
    """
    عمداً status/is_active را ندارد — این‌ها فقط از طریق Service Layer
    (State Machine) تغییر می‌کنند، نه فرم ایجاد.
    """

    class Meta:
        model = Committee
        fields = ["name", "code", "description", "purpose", "scope"]
        labels = {
            "name": "نام کمیته",
            "code": "کد کمیته (اختیاری)",
            "description": "توضیحات",
            "purpose": "هدف از تشکیل کمیته",
            "scope": "محدوده‌ی جغرافیایی (اختیاری)",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "purpose": forms.Textarea(attrs={"rows": 3}),
        }


class CommitteeMembershipCreateForm(forms.ModelForm):
    """
    عمداً assigned_by/is_active/is_public_visible را ندارد.
    """
    start_date = JalaliDateField(label="تاریخ شروع عضویت")

    class Meta:
        model = CommitteeMembership
        fields = ["user", "start_date", "reason"]
        labels = {
            "user": "کاربر",
            "reason": "دلیل (اختیاری)",
        }
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"})}


class CommitteeReasonForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=True, label="دلیل")


class CommitteeOptionalReasonForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="دلیل (اختیاری)")


class CommitteeMembershipEndForm(forms.Form):
    end_date = JalaliDateField(label="تاریخ پایان")
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="دلیل (اختیاری)")
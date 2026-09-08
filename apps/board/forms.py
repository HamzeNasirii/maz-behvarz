from django import forms

from .models import Board, BoardMembership
from apps.authorization.forms import JalaliDateField


class BoardCreateForm(forms.ModelForm):
    """
    عمداً فیلد name را ندارد — نام دوره خودکار و ترتیبی («دوره ۱»، «دوره
    ۲»، ...) توسط create_board() تعیین می‌شود، طبق درخواست صریح.
    """

    start_date = JalaliDateField(label="تاریخ شروع")

    class Meta:
        model = BoardMembership
        fields = ["user", "position", "start_date", "reason"]
        labels = {
            "user": "کاربر",
            "position": "سمت",
            "reason": "دلیل (اختیاری)",
        }


class BoardMembershipCreateForm(forms.ModelForm):
    start_date = JalaliDateField(label="تاریخ شروع")

    class Meta:
        model = BoardMembership
        fields = ["user", "position", "start_date", "reason"]
        labels = {
            "user": "کاربر",
            "position": "سمت",
            "reason": "دلیل (اختیاری)",
        }
        widgets = {
            "user": forms.HiddenInput(),
            "reason": forms.TextInput(),
        }


class BoardReasonForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=True, label="دلیل")


class BoardOptionalReasonForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="دلیل (اختیاری)")


class BoardMembershipEndForm(forms.Form):
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="دلیل (اختیاری)")
from django import forms

from .models import Request


class RequestCreateForm(forms.ModelForm):
    """
    عمداً requester/status/approved_by/approved_at/scope را ندارد —
    این‌ها فقط Server-side تعیین می‌شوند (بخش ۲۲ سند).
    """

    class Meta:
        model = Request
        fields = ["request_type", "title", "description"]
        labels = {
            "request_type": "نوع درخواست",
            "title": "عنوان درخواست",
            "description": "توضیحات",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

class RequestReasonForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=True, label="دلیل")


class RequestOptionalReasonForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="دلیل (اختیاری)")


class RequestFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[("", "همه")] + list(Request._meta.get_field("status").choices),
        required=False, label="وضعیت",
    )
    request_type = forms.ChoiceField(
        choices=[("", "همه")] + list(Request._meta.get_field("request_type").choices),
        required=False, label="نوع درخواست",
    )
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="از تاریخ")
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="تا تاریخ")
    q = forms.CharField(required=False, label="جستجو")
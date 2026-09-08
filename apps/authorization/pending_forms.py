from django import forms


class RejectReasonForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=True, label="دلیل رد")
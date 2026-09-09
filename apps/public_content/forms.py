from django import forms

from .models import ContactMessage


class ContactMessageForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "subject", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 5}),
        }

    def clean_message(self):
        message = self.cleaned_data["message"]
        if len(message.strip()) < 10:
            raise forms.ValidationError("متن پیام باید حداقل ۱۰ نویسه باشد.")
        return message


class SiteSearchForm(forms.Form):
    q = forms.CharField(required=True, max_length=200, label="جستجو")
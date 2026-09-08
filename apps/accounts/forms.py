from django import forms


class BaleResetRequestForm(forms.Form):
    national_code = forms.CharField(label="کد ملی", max_length=10)


class BaleResetVerifyForm(forms.Form):
    code = forms.CharField(label="کد ارسال‌شده در بله", max_length=6)
    new_password1 = forms.CharField(widget=forms.PasswordInput, label="رمز عبور جدید")
    new_password2 = forms.CharField(widget=forms.PasswordInput, label="تکرار رمز عبور جدید")

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("new_password1") != cleaned_data.get("new_password2"):
            raise forms.ValidationError("رمز عبور جدید و تکرار آن یکسان نیستند.")
        return cleaned_data
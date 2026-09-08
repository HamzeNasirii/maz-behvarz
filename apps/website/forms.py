import re

from django import forms

from apps.documents.validators import validate_document_file
from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

from .models import MembershipApplication


class MembershipApplicationForm(forms.ModelForm):
    first_name = forms.CharField(label="نام", max_length=100)
    last_name = forms.CharField(label="نام خانوادگی", max_length=100)

    province = forms.ModelChoiceField(
        queryset=Province.objects.filter(is_active=True).order_by("name"),
        label="استان",
    )
    county = forms.ModelChoiceField(
        queryset=County.objects.none(), label="شهرستان",
    )
    network = forms.ModelChoiceField(
        queryset=HealthNetwork.objects.none(), label="شبکه بهداشت و درمان",
    )
    center = forms.ModelChoiceField(
        queryset=HealthCenter.objects.none(), label="مرکز خدمات جامع سلامت",
    )
    accepted_terms = forms.BooleanField(
        required=True, label="تعهدنامه‌ی بالا را می‌پذیرم",
    )

    class Meta:
        model = MembershipApplication
        fields = [
            "national_code", "mobile_number", "health_house",
            "legal_decree_file", "network_letter_file", "accepted_terms",
        ]
        labels = {
            "national_code": "کد ملی",
            "mobile_number": "شماره موبایل",
            "health_house": "خانه بهداشت",
            "legal_decree_file": "آخرین حکم کارگزینی",
            "network_letter_file": "نامه‌ی ممهور شبکه بهداشت (دانلود نمونه پایین فرم)",
        }
        widgets = {
            "national_code": forms.TextInput(attrs={
                "inputmode": "numeric", "maxlength": "10", "placeholder": "مثال: 1234567890",
            }),
            "mobile_number": forms.TextInput(attrs={
                "inputmode": "numeric", "maxlength": "11", "placeholder": "مثال: 09121234567",
            }),
            "legal_decree_file": forms.FileInput(attrs={"class": "file-input-hidden"}),
            "network_letter_file": forms.FileInput(attrs={"class": "file-input-hidden"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["health_house"].queryset = HealthHouse.objects.none()
        self.fields["health_house"].required = True
        self.fields["legal_decree_file"].validators.append(validate_document_file)
        self.fields["network_letter_file"].validators.append(validate_document_file)

        if self.data.get("province"):
            try:
                self.fields["county"].queryset = County.objects.filter(
                    province_id=int(self.data["province"]), is_active=True
                ).order_by("name")
            except (ValueError, TypeError):
                pass

        if self.data.get("county"):
            try:
                self.fields["network"].queryset = HealthNetwork.objects.filter(
                    county_id=int(self.data["county"]), is_active=True
                ).order_by("name")
            except (ValueError, TypeError):
                pass

        if self.data.get("network"):
            try:
                self.fields["center"].queryset = HealthCenter.objects.filter(
                    network_id=int(self.data["network"]), is_active=True
                ).order_by("name")
            except (ValueError, TypeError):
                pass

        if self.data.get("center"):
            try:
                self.fields["health_house"].queryset = HealthHouse.objects.filter(
                    center_id=int(self.data["center"]), is_active=True
                ).order_by("name")
            except (ValueError, TypeError):
                pass

    def clean(self):
        cleaned_data = super().clean()
        house = cleaned_data.get("health_house")
        center = cleaned_data.get("center")
        if house and center and house.center_id != center.id:
            raise forms.ValidationError(
                "خانه بهداشت انتخابی با مرکز انتخابی مطابقت ندارد."
            )
        return cleaned_data

    def clean_national_code(self):
        code = self.cleaned_data["national_code"]
        if not re.fullmatch(r"\d{10}", code):
            raise forms.ValidationError("کد ملی باید دقیقاً ۱۰ رقم و فقط شامل عدد باشد.")
        return code

    def clean_mobile_number(self):
        number = self.cleaned_data["mobile_number"]
        if not re.fullmatch(r"0\d{10}", number):
            raise forms.ValidationError("شماره موبایل باید ۱۱ رقم باشد، فقط شامل عدد، و با ۰ شروع شود.")
        return number

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.full_name = f"{self.cleaned_data['first_name']} {self.cleaned_data['last_name']}".strip()
        if commit:
            instance.save()
        return instance


from django.contrib.auth.forms import PasswordChangeForm


class ForcedPasswordChangeForm(PasswordChangeForm):
    """
    همان PasswordChangeForm استاندارد جنگو — فقط برچسب‌ها فارسی شدند.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "رمز عبور فعلی (همان شماره ملی)"
        self.fields["new_password1"].label = "رمز عبور جدید"
        self.fields["new_password2"].label = "تکرار رمز عبور جدید"
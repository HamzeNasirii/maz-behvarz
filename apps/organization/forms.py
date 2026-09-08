from django import forms

from .models import County, HealthCenter, HealthHouse, HealthNetwork, Province


class ProvinceForm(forms.ModelForm):
    class Meta:
        model = Province
        fields = ["name", "code", "is_active"]
        labels = {"name": "نام استان", "code": "کد رسمی (اختیاری)", "is_active": "فعال"}


class CountyCreateForm(forms.ModelForm):
    """عمداً فیلد province را در Meta ندارد — از URL (والد) تعیین می‌شود، نه از کاربر."""

    class Meta:
        model = County
        fields = ["name", "code", "is_active"]
        labels = {"name": "نام شهرستان", "code": "کد رسمی (اختیاری)", "is_active": "فعال"}


class CountyEditForm(forms.ModelForm):
    class Meta:
        model = County
        fields = ["name", "code", "is_active"]
        labels = {"name": "نام شهرستان", "code": "کد رسمی (اختیاری)", "is_active": "فعال"}


class NetworkCreateForm(forms.ModelForm):
    class Meta:
        model = HealthNetwork
        fields = ["name", "code", "is_active"]
        labels = {"name": "نام شبکه بهداشت و درمان", "code": "کد رسمی (اختیاری)", "is_active": "فعال"}


class NetworkEditForm(forms.ModelForm):
    class Meta:
        model = HealthNetwork
        fields = ["name", "code", "is_active"]
        labels = {"name": "نام شبکه بهداشت و درمان", "code": "کد رسمی (اختیاری)", "is_active": "فعال"}


class CenterCreateForm(forms.ModelForm):
    class Meta:
        model = HealthCenter
        fields = ["name", "code", "is_active"]
        labels = {"name": "نام مرکز خدمات جامع سلامت", "code": "کد رسمی (اختیاری)", "is_active": "فعال"}


class CenterEditForm(forms.ModelForm):
    class Meta:
        model = HealthCenter
        fields = ["name", "code", "is_active"]
        labels = {"name": "نام مرکز خدمات جامع سلامت", "code": "کد رسمی (اختیاری)", "is_active": "فعال"}


class HouseCreateForm(forms.ModelForm):
    class Meta:
        model = HealthHouse
        fields = ["name", "code", "is_active"]
        labels = {"name": "نام خانه بهداشت", "code": "کد رسمی (اختیاری)", "is_active": "فعال"}


class HouseEditForm(forms.ModelForm):
    class Meta:
        model = HealthHouse
        fields = ["name", "code", "is_active"]
        labels = {"name": "نام خانه بهداشت", "code": "کد رسمی (اختیاری)", "is_active": "فعال"}
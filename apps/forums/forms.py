from django import forms

from .models import Forum, ForumComment, ForumPost
from apps.organization.models import County, HealthCenter, HealthNetwork, Province

class ForumCreateForm(forms.Form):
    """
    عمداً به‌جای انتخاب مستقیم AccessScope (که با تعداد زیاد محدوده‌ها
    غیرقابل‌استفاده می‌شود)، کاربر سطح و گره‌ی سازمانی را از یک زنجیره‌ی
    Cascading انتخاب می‌کند؛ AccessScope و نام فروم خودکار محاسبه
    می‌شوند. سطح «خانه بهداشت» عمداً در گزینه‌ها نیست.
    """

    LEVEL_CHOICES = [
        ("province", "استان"),
        ("county", "شهرستان"),
        ("network", "شبکه بهداشت و درمان"),
        ("center", "مرکز خدمات جامع سلامت"),
    ]

    level = forms.ChoiceField(choices=LEVEL_CHOICES, label="سطح فروم")
    province = forms.ModelChoiceField(queryset=Province.objects.none(), label="استان")
    county = forms.ModelChoiceField(queryset=County.objects.none(), required=False, label="شهرستان")
    network = forms.ModelChoiceField(queryset=HealthNetwork.objects.none(), required=False, label="شبکه بهداشت و درمان")
    center = forms.ModelChoiceField(queryset=HealthCenter.objects.none(), required=False, label="مرکز خدمات جامع سلامت")
    name = forms.CharField(required=False, label="نام فروم (اختیاری — در صورت خالی‌بودن، خودکار ساخته می‌شود)")
    description = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="توضیحات")

    def __init__(self, *args, **kwargs):
        self.editor = kwargs.pop("editor")
        super().__init__(*args, **kwargs)

        from apps.authorization.scope_helpers import get_accessible_province_ids

        accessible_province_ids = get_accessible_province_ids(self.editor)
        province_qs = Province.objects.filter(is_active=True).order_by("name")
        if accessible_province_ids is not None:
            province_qs = province_qs.filter(pk__in=accessible_province_ids)
        self.fields["province"].queryset = province_qs

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

    def clean(self):
        cleaned_data = super().clean()
        level = cleaned_data.get("level")
        required_field_map = {"county": "county", "network": "network", "center": "center"}
        if level in required_field_map and not cleaned_data.get(required_field_map[level]):
            raise forms.ValidationError(f"برای سطح انتخابی، انتخاب {dict(self.LEVEL_CHOICES)[level]} الزامی است.")
        return cleaned_data

    def get_target_instance(self):
        level = self.cleaned_data["level"]
        return self.cleaned_data[level]

class ForumPostForm(forms.ModelForm):
    class Meta:
        model = ForumPost
        fields = ["title", "content"]
        labels = {
            "title": "عنوان پست",
            "content": "متن پست",
        }
        widgets = {
            "content": forms.Textarea(attrs={"rows": 6}),
        }


class ForumCommentForm(forms.ModelForm):
    class Meta:
        model = ForumComment
        fields = ["content"]
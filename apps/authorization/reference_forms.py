from django import forms

from apps.organization.models import County, HealthCenter, HealthHouse, HealthNetwork, Province

from .models import AccessScope, Permission, Role


SENSITIVE_PERMISSION_PREFIXES = ("role.",)


class RoleForm(forms.ModelForm):
    class Meta:
        model = Role
        fields = ["code", "name", "description", "permissions", "is_active"]
        widgets = {"permissions": forms.CheckboxSelectMultiple}
        labels = {
            "code": "کد نقش", "name": "نام نقش", "description": "توضیحات",
            "permissions": "مجوزها", "is_active": "فعال",
        }

    def __init__(self, *args, **kwargs):
        self.editor = kwargs.pop("editor", None)
        super().__init__(*args, **kwargs)

        self.fields["code"].disabled = True
        self.fields["name"].disabled = True
        self.fields["description"].disabled = True

        is_full_admin = self.editor is not None and (self.editor.is_staff or self.editor.is_superuser)
        if not is_full_admin:
            self.fields["permissions"].queryset = self.fields["permissions"].queryset.exclude(
                code__startswith=SENSITIVE_PERMISSION_PREFIXES
            )


class PermissionForm(forms.ModelForm):
    class Meta:
        model = Permission
        fields = ["code", "description"]
        labels = {"code": "کد مجوز", "description": "توضیحات"}


class AccessScopeForm(forms.ModelForm):
    province = forms.ModelChoiceField(
        queryset=Province.objects.filter(is_active=True).order_by("name"), required=False, label="استان",
    )
    county = forms.ModelChoiceField(queryset=County.objects.none(), required=False, label="شهرستان")
    network = forms.ModelChoiceField(queryset=HealthNetwork.objects.none(), required=False, label="شبکه بهداشت")
    center = forms.ModelChoiceField(queryset=HealthCenter.objects.none(), required=False, label="مرکز")
    house = forms.ModelChoiceField(queryset=HealthHouse.objects.none(), required=False, label="خانه بهداشت")

    class Meta:
        model = AccessScope
        fields = ["scope_type", "province", "county", "network", "center", "house", "committee"]
        labels = {"scope_type": "نوع محدوده", "committee": "کمیته"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
                self.fields["house"].queryset = HealthHouse.objects.filter(
                    center_id=int(self.data["center"]), is_active=True
                ).order_by("name")
            except (ValueError, TypeError):
                pass

        instance = kwargs.get("instance")
        if instance and instance.pk:
            if instance.province_id:
                self.fields["county"].queryset = County.objects.filter(
                    province_id=instance.province_id
                ).order_by("name")
            if instance.county_id:
                self.fields["network"].queryset = HealthNetwork.objects.filter(
                    county_id=instance.county_id
                ).order_by("name")
            if instance.network_id:
                self.fields["center"].queryset = HealthCenter.objects.filter(
                    network_id=instance.network_id
                ).order_by("name")
            if instance.center_id:
                self.fields["house"].queryset = HealthHouse.objects.filter(
                    center_id=instance.center_id
                ).order_by("name")

    def clean(self):
        cleaned_data = super().clean()
        scope_type = cleaned_data.get("scope_type")

        level_field_map = {
            "province": "province", "county": "county", "network": "network",
            "center": "center", "house": "house",
        }
        target_field = level_field_map.get(scope_type)

        for field_name in ["province", "county", "network", "center", "house"]:
            if field_name != target_field:
                cleaned_data[field_name] = None

        return cleaned_data
from django import forms

from .choices import EmploymentType
from .models import EmploymentAssignment


class EmploymentAssignmentCreateForm(forms.ModelForm):
    """
    عمداً approval_status/approved_by/approved_at را ندارد — این‌ها
    فقط از طریق Workflow تأیید (approve_employment_transfer) تغییر
    می‌کنند، نه مستقیماً از فرم ایجاد (طبق قانون ۹ سند اصلی: Actor/
    Timestamp/Reason باید از مسیر Service ثبت شود).
    """

    class Meta:
        model = EmploymentAssignment
        fields = ["user", "health_house", "employment_type", "start_date", "is_primary", "reason"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
        }


class EmploymentAssignmentEndForm(forms.Form):
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)
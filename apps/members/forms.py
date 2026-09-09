from django import forms
from django.contrib.auth import get_user_model

from apps.documents.validators import validate_document_file
from apps.authorization.forms import JalaliDateField

from .choices import RemovalReason
from .models import Member
from ..public_content.management_forms import MultipleFileField, MultipleFileInput

User = get_user_model()


class ProfileEditForm(forms.ModelForm):
    """
    عمداً فقط شامل first_name/last_name/email است. هیچ فیلد
    Employment/Organization/Role/Membership این‌جا وجود ندارد —
    طبق تحریم صریح سند («User نباید بتواند این‌ها را از Profile
    Form تغییر دهد»).
    """
    """
        عمداً فقط شامل first_name/last_name/email/profile_picture/
        date_of_birth است — هیچ فیلد Employment/Organization/Role/
        Membership این‌جا وجود ندارد (طبق تحریم صریح سند).
    """

    date_of_birth = JalaliDateField(required=False, label="تاریخ تولد")

    class Meta:
        model = User
        fields = ["first_name", "last_name", "nickname", "email", "profile_picture", "date_of_birth"]
        labels = {
            "first_name": "نام", "last_name": "نام خانوادگی", "email": "ایمیل",
            "profile_picture": "تصویر پروفایل", "nickname": "نام نمایشی (اختیاری)",
        }
        widgets = {
            "profile_picture": forms.FileInput(attrs={"class": "file-input-hidden"}),
        }

    def clean_nickname(self):
        nickname = self.cleaned_data.get("nickname") or ""
        nickname = nickname.strip()
        return nickname or None  # رشته‌ی خالی همیشه به None تبدیل شود، طبق نکته‌ی بالا


class MembershipReasonForm(forms.Form):
    """برای Reject/Suspend/Cancel که نیاز به دلیل اجباری دارند."""
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=True, label="دلیل")


class MembershipOptionalReasonForm(forms.Form):
    """برای Reinstate/Expire که دلیل اختیاری است."""
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="دلیل (اختیاری)")


class MemberDocumentsForm(forms.ModelForm):
    birth_certificate_images = MultipleFileField(
        required=False, label="تصاویر شناسنامه (صفحه‌ی اول و دوم — می‌توانید چند تصویر انتخاب کنید)",
        widget=MultipleFileInput(attrs={"multiple": True, "class": "file-input-hidden"}),
    )

    class Meta:
        model = Member
        fields = ["legal_decree_file", "network_letter_file", "national_id_card_file"]
        labels = {
            "legal_decree_file": "آخرین حکم کارگزینی",
            "network_letter_file": "نامه‌ی ممهور شبکه بهداشت",
            "national_id_card_file": "تصویر کارت ملی",
        }
        widgets = {
            "legal_decree_file": forms.FileInput(attrs={"class": "file-input-hidden"}),
            "network_letter_file": forms.FileInput(attrs={"class": "file-input-hidden"}),
            "national_id_card_file": forms.FileInput(attrs={"class": "file-input-hidden"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["legal_decree_file"].validators.append(validate_document_file)
        self.fields["network_letter_file"].validators.append(validate_document_file)
        self.fields["legal_decree_file"].required = False
        self.fields["network_letter_file"].required = False
        self.fields["national_id_card_file"].required = False


class MemberRemovalProposalForm(forms.Form):
    reason = forms.ChoiceField(choices=RemovalReason.choices, label="دلیل پیشنهاد")
    reason_detail = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="توضیح تکمیلی")


class RemovalDecisionForm(forms.Form):
    note = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="یادداشت تصمیم")


class MemberContactForm(forms.ModelForm):
    """
    شماره تماس روی مدل Member ذخیره می‌شود (همان فیلدی که موقع تأیید
    عضویت پر شد) — نه CustomUser، تا داده تکرار نشود.
    """

    class Meta:
        model = Member
        fields = ["mobile_number"]
        labels = {"mobile_number": "شماره تماس"}


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
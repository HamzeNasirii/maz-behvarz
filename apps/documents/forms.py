from django import forms

from .models import Document


class DocumentUploadForm(forms.ModelForm):
    """
    عمداً uploaded_by/status/checksum/file_size/mime_type/version را
    ندارد — این‌ها فقط از طریق Service تعیین می‌شوند (بخش ۳۰ سند).
    """

    class Meta:
        model = Document
        fields = ["title", "document_type", "file", "visibility", "scope"]


class DocumentReasonForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=True, label="دلیل")


class DocumentOptionalReasonForm(forms.Form):
    reason = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="دلیل (اختیاری)")
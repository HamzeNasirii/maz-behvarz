"""
File Validation + Checksum — طبق بخش ۹/۱۰ سند.

نکته درباره‌ی Path Traversal (بخش ۱۱): Django's FileField/Storage
به‌صورت پیش‌فرض از django.utils.text.get_valid_filename() استفاده
می‌کند که کاراکترهای خطرناک مسیر (../، /) را حذف می‌کند؛ نیازی به
کد اضافه نیست — این در تست‌ها تأیید می‌شود.

نکته درباره‌ی MIME (بخش ۱۰): این پیاده‌سازی هم extension و هم
content_type ارسالی مرورگر را چک می‌کند، اما چون content_type از
سمت کلاینت قابل جعل است، تشخیص واقعی محتوای فایل (Magic Bytes) نیاز
به کتابخانه‌ی خارجی (مثل python-magic) دارد که در این فاز، طبق اصل
«از افزودن dependency غیرضروری خودداری کن»، اضافه نشده — در
Technical Debt مستند شده است.
"""

import hashlib

from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "docx"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 مگابایت


def validate_document_file(uploaded_file):
    extension = uploaded_file.name.rsplit(".", 1)[-1].lower() if "." in uploaded_file.name else ""
    if extension not in ALLOWED_EXTENSIONS:
        raise ValidationError(f"پسوند «{extension}» مجاز نیست.")

    content_type = getattr(uploaded_file, "content_type", None)
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        raise ValidationError("نوع فایل (MIME) مجاز نیست.")

    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValidationError("حجم فایل بیش از حد مجاز (۱۰ مگابایت) است.")


def compute_file_checksum(uploaded_file):
    sha256 = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        sha256.update(chunk)
    uploaded_file.seek(0)
    return sha256.hexdigest()
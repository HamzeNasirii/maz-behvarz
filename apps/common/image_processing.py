import io

from django.core.files.base import ContentFile
from PIL import Image

MAX_DIMENSION = 1600
JPEG_QUALITY = 82


def compress_image_field(image_field_file, max_dimension=MAX_DIMENSION, jpeg_quality=JPEG_QUALITY):
    """
    فشرده‌سازی و تغییر اندازه‌ی یک ImageFieldFile پیش از Save، به‌صورت In-place.

    - اگر عرض/ارتفاع از max_dimension بزرگ‌تر باشد، با حفظ Aspect Ratio کوچک می‌شود.
    - JPEG با کیفیت jpeg_quality فشرده می‌شود.
    - PNG فقط Resize می‌شود (بدون افت کیفیت/شفافیت).
    - فرمت‌های دیگر (WEBP, GIF, ...) و فایل‌های خراب/غیرقابل‌پردازش دست‌نخورده می‌مانند
      (Fail-safe — هرگز باعث شکست کل عملیات Save نمی‌شود).
    """
    if not image_field_file:
        return

    try:
        image_field_file.seek(0)
        img = Image.open(image_field_file)
        img_format = (img.format or "JPEG").upper()
        original_mode = img.mode

        if img.width > max_dimension or img.height > max_dimension:
            img.thumbnail((max_dimension, max_dimension), Image.LANCZOS)

        buffer = io.BytesIO()
        if img_format in ("JPEG", "JPG"):
            if original_mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(buffer, format="JPEG", quality=jpeg_quality, optimize=True)
        elif img_format == "PNG":
            img.save(buffer, format="PNG", optimize=True)
        else:
            return

        buffer.seek(0)
        file_name = image_field_file.name
        image_field_file.save(file_name, ContentFile(buffer.read()), save=False)
    except Exception:
        image_field_file.seek(0)
        return
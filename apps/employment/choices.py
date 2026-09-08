from django.db import models


class EmploymentType(models.TextChoices):
    BEHVARZ = "behvarz", "بهورز"
    ASSISTANT = "assistant", "کمک‌بهورز"
    OTHER = "other", "سایر"
from django import forms
from django.utils.text import slugify

from . import models as m
from apps.authorization.forms import JalaliDateField

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

    def value_from_datadict(self, data, files, name):
        if hasattr(files, "getlist"):
            return files.getlist(name)
        return files.get(name)


class MultipleFileField(forms.FileField):
    """
    راه‌حل رسمی مستندات Django برای پشتیبانی از چند فایل در یک فیلد —
    FileField معمولی نمی‌تواند یک لیست از فایل‌ها را Validate کند.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = forms.FileField.clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(self, d, initial) for d in data]
        else:
            result = single_file_clean(self, data, initial)
        return result


class NewsArticleForm(forms.ModelForm):
    tags_input = forms.CharField(
        required=False, label="تگ‌ها",
        widget=forms.TextInput(attrs={"placeholder": "تگ‌ها را با کاما (،) جدا کنید — مثال: سلامت، بهورز، آموزش"}),
    )
    gallery_images = MultipleFileField(
        required=False, label="تصاویر گالری (می‌توانید چند تصویر انتخاب کنید)",
        widget=MultipleFileInput(attrs={"multiple": True, "class": "file-input-hidden"}),
    )

    class Meta:
        model = m.NewsArticle
        exclude = ["slug", "author", "published_at", "category", "tags", "view_count"]
        labels = {
            "title": "عنوان خبر",
            "summary": "خلاصه",
            "content": "متن کامل خبر",
            "featured_image": "تصویر شاخص (اصلی)",
            "categories": "دسته‌بندی‌ها",
            "status": "وضعیت انتشار",
            "is_featured": "خبر ویژه",
        }
        widgets = {
            "featured_image": forms.FileInput(attrs={"class": "file-input-hidden"}),
            "categories": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["tags_input"].initial = "، ".join(
                self.instance.tags.values_list("name", flat=True)
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            base_slug = slugify(instance.title, allow_unicode=False)
            if not base_slug:
                import time
                base_slug = f"khabar-{int(time.time())}"
            slug = base_slug
            counter = 1
            while m.NewsArticle.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            instance.slug = slug
        if commit:
            instance.save()
            self.save_m2m()
            self.save_tags(instance)
        return instance

    def save_tags(self, instance):
        raw = self.cleaned_data.get("tags_input", "").strip()
        names = [n.strip() for n in raw.replace("،", ",").split(",") if n.strip()]
        tag_objects = []
        for name in names:
            tag, _ = m.Tag.objects.get_or_create(name=name)
            tag_objects.append(tag)
        instance.tags.set(tag_objects)


class HeroSlideForm(forms.ModelForm):
    class Meta:
        model = m.HeroSlide
        exclude = []
        labels = {
            "title": "عنوان",
            "subtitle": "زیرعنوان",
            "description": "توضیحات",
            "image": "تصویر",
            "cta_text": "متن دکمه",
            "cta_link": "لینک دکمه",
            "is_active": "فعال",
            "ordering": "ترتیب نمایش",
        }
        widgets = {
            "image": forms.FileInput(attrs={"class": "file-input-hidden"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }


class PublicDocumentForm(forms.ModelForm):
    files = MultipleFileField(
        required=True, label="فایل(های) سند (می‌توانید چند فایل انتخاب کنید)",
        widget=MultipleFileInput(attrs={"multiple": True, "class": "file-input-hidden"}),
    )

    class Meta:
        model = m.PublicDocument
        exclude = ["file", "file_size", "file_type", "publication_date", "category"]
        labels = {
            "title": "عنوان سند",
            "description": "توضیحات",
            "categories": "دسته‌بندی‌ها",
            "is_public": "قابل‌مشاهده برای عموم",
            "is_published": "منتشرشده",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "categories": forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["files"].required = False




class FAQForm(forms.ModelForm):
    class Meta:
        model = m.FAQ
        exclude = []
        labels = {
            "question": "سؤال",
            "answer": "پاسخ",
            "category": "دسته‌بندی",
            "ordering": "ترتیب نمایش",
            "is_active": "فعال",
        }
        widgets = {
            "answer": forms.Textarea(attrs={"rows": 4}),
        }

class RegulationForm(forms.ModelForm):
    effective_date = JalaliDateField(required=False, label="تاریخ اجرا")

    class Meta:
        model = m.Regulation
        exclude = ["slug", "published_at"]
        labels = {
            "title": "عنوان",
            "summary": "خلاصه",
            "content": "متن کامل",
            "document": "سند مرتبط (اختیاری)",
            "status": "وضعیت انتشار",
        }
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 2}),
            "content": forms.Textarea(attrs={"rows": 8}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            base_slug = slugify(instance.title, allow_unicode=False)
            if not base_slug:
                import time
                base_slug = f"regulation-{int(time.time())}"
            slug = base_slug
            counter = 1
            while m.Regulation.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            instance.slug = slug
        if commit:
            instance.save()
            self.save_m2m()
        return instance

class NewsCategoryForm(forms.ModelForm):
    class Meta:
        model = m.NewsCategory
        exclude = ["slug"]
        labels = {"name": "نام دسته‌بندی"}

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            base_slug = slugify(instance.name, allow_unicode=False)
            if not base_slug:
                import time
                base_slug = f"category-{int(time.time())}"
            slug = base_slug
            counter = 1
            while m.NewsCategory.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            instance.slug = slug
        if commit:
            instance.save()
        return instance

class DocumentCategoryForm(forms.ModelForm):
    class Meta:
        model = m.DocumentCategory
        exclude = ["slug"]
        labels = {"name": "نام دسته‌بندی"}

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            base_slug = slugify(instance.name, allow_unicode=False)
            if not base_slug:
                import time
                base_slug = f"category-{int(time.time())}"
            slug = base_slug
            counter = 1
            while m.DocumentCategory.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            instance.slug = slug
        if commit:
            instance.save()
        return instance

class AnnouncementForm(forms.ModelForm):
    class Meta:
        model = m.Announcement
        exclude = ["slug"]
        labels = {
            "title": "عنوان",
            "summary": "خلاصه",
            "content": "متن اطلاعیه",
            "is_featured": "اطلاعیه‌ی ویژه",
            "publish_at": "تاریخ انتشار",
            "is_published": "منتشرشده",
        }
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 2}),
            "content": forms.Textarea(attrs={"rows": 5}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            base_slug = slugify(instance.title, allow_unicode=False)
            if not base_slug:
                import time
                base_slug = f"announcement-{int(time.time())}"
            slug = base_slug
            counter = 1
            while m.Announcement.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            instance.slug = slug
        if commit:
            instance.save()
        return instance

class EventForm(forms.ModelForm):
    start_date = JalaliDateField(label="تاریخ شروع")
    start_time = forms.TimeField(
        label="ساعت شروع", widget=forms.TimeInput(attrs={"type": "time"}),
    )
    end_date = JalaliDateField(label="تاریخ پایان")
    end_time = forms.TimeField(
        label="ساعت پایان", widget=forms.TimeInput(attrs={"type": "time"}),
    )

    class Meta:
        model = m.Event
        exclude = ["slug", "start_datetime", "end_datetime", "published_at"]
        labels = {
            "title": "عنوان",
            "description": "توضیحات",
            "location": "مکان برگزاری",
            "image": "تصویر",
            "registration_required": "نیاز به ثبت‌نام",
            "registration_url": "لینک ثبت‌نام",
            "status": "وضعیت انتشار",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "image": forms.FileInput(attrs={"class": "file-input-hidden"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.utils import timezone

        now = timezone.localtime()
        if self.instance and self.instance.pk:
            if self.instance.start_datetime:
                self.fields["start_date"].initial = self.instance.start_datetime.date()
                self.fields["start_time"].initial = self.instance.start_datetime.time()
            if self.instance.end_datetime:
                self.fields["end_date"].initial = self.instance.end_datetime.date()
                self.fields["end_time"].initial = self.instance.end_datetime.time()
        else:
            # ساعت به‌طور خودکار با زمان فعلی پر می‌شود — کاربر می‌تواند
            # در صورت نیاز تغییرش دهد، ولی مجبور به وارد‌کردن دستی نیست.
            self.fields["start_time"].initial = now.time().replace(second=0, microsecond=0)
            self.fields["end_time"].initial = now.time().replace(second=0, microsecond=0)

    def save(self, commit=True):
        import datetime

        instance = super().save(commit=False)

        instance.start_datetime = datetime.datetime.combine(
            self.cleaned_data["start_date"], self.cleaned_data["start_time"]
        )
        instance.end_datetime = datetime.datetime.combine(
            self.cleaned_data["end_date"], self.cleaned_data["end_time"]
        )

        if not instance.slug:
            base_slug = slugify(instance.title, allow_unicode=False)
            if not base_slug:
                import time
                base_slug = f"event-{int(time.time())}"
            slug = base_slug
            counter = 1
            while m.Event.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                counter += 1
                slug = f"{base_slug}-{counter}"
            instance.slug = slug

        if commit:
            instance.save()
        return instance

class FAQCategoryForm(forms.ModelForm):
    class Meta:
        model = m.FAQCategory
        exclude = []
        labels = {"name": "نام دسته‌بندی"}

class TagForm(forms.ModelForm):
    class Meta:
        model = m.Tag
        exclude = ["slug"]
        labels = {"name": "نام تگ"}


FORM_OVERRIDES = {
    "news": NewsArticleForm,
    "hero_slide": HeroSlideForm,
    "public_document": PublicDocumentForm,
    "faq": FAQForm,
    "regulation": RegulationForm,
    "news_category": NewsCategoryForm,
    "document_category": DocumentCategoryForm,
    "announcement": AnnouncementForm,
    "event": EventForm,
    "faq_category": FAQCategoryForm,
    "tag": TagForm,
}
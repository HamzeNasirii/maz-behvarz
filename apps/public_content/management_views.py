from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.board.permissions import is_board_member

from . import models as m
from .management_forms import FORM_OVERRIDES
from .management_registry import CONTENT_TYPES


def _require_access(user):
    if not (user.is_staff or user.is_superuser or is_board_member(user)):
        raise PermissionDenied("شما مجوز مدیریت محتوای عمومی سایت را ندارید.")


def _get_config(content_type):
    config = CONTENT_TYPES.get(content_type)
    if config is None:
        raise PermissionDenied("نوع محتوای انتخاب‌شده نامعتبر است.")
    return config


def _build_form_class(content_type, model):
    if content_type in FORM_OVERRIDES:
        return FORM_OVERRIDES[content_type]
    return forms.modelform_factory(
        model, fields="__all__",
        exclude=["created_by", "created_at", "updated_at", "published_at", "archived_at"],
    )


@login_required
def hub_view(request):
    _require_access(request.user)
    cards = [
        {
            "key": key, "label": config["label"],
            "count": config["model"].objects.count(),
            "can_create": config["can_create"],
        }
        for key, config in CONTENT_TYPES.items()
    ]
    return render(request, "public_content/management_hub.html", {"cards": cards})


@login_required
def list_view(request, content_type):
    _require_access(request.user)
    config = _get_config(content_type)
    items = config["model"].objects.all().order_by("-pk")
    return render(request, "public_content/management_list.html", {
        "items": items, "label": config["label"], "content_type": content_type,
        "can_create": config["can_create"],
    })


@login_required
def create_view(request, content_type):
    _require_access(request.user)
    config = _get_config(content_type)
    if not config["can_create"]:
        raise PermissionDenied("ایجاد این نوع محتوا مجاز نیست.")
    form_class = _build_form_class(content_type, config["model"])

    if request.method == "POST":
        form = form_class(request.POST, request.FILES)
        if form.is_valid():
            instance = form.save(commit=False)
            if hasattr(instance, "created_by_id") and not instance.created_by_id:
                instance.created_by = request.user
            if hasattr(instance, "author_id") and not instance.author_id:
                instance.author = request.user

            extra_document_files = []
            if content_type == "public_document":
                from django.utils import timezone
                uploaded_files = form.cleaned_data.get("files") or []
                if uploaded_files and not instance.file:
                    instance.file = uploaded_files[0]
                    extra_document_files = uploaded_files[1:]
                else:
                    extra_document_files = uploaded_files
                if not instance.publication_date:
                    instance.publication_date = timezone.localdate()

            instance.save()
            form.save_m2m()
            if hasattr(form, "save_tags"):
                form.save_tags(instance)

            if content_type == "news":
                for f in request.FILES.getlist("gallery_images"):
                    m.NewsImage.objects.create(news_article=instance, image=f)

            if content_type == "public_document":
                for f in extra_document_files:
                    m.PublicDocumentFile.objects.create(document=instance, file=f, title=f.name)

            messages.success(request, f"{config['label']} با موفقیت ایجاد شد.")
            return redirect("public_content_mgmt:list", content_type=content_type)
    else:
        form = form_class()

    return render(request, "public_content/management_form.html", {
        "form": form, "label": config["label"], "mode": "create", "content_type": content_type,
    })


@login_required
def edit_view(request, content_type, pk):
    _require_access(request.user)
    config = _get_config(content_type)
    instance = get_object_or_404(config["model"], pk=pk)
    form_class = _build_form_class(content_type, config["model"])

    attachments = None
    if content_type == "public_document":
        attachments = instance.attachments.all()

    if request.method == "POST":
        form = form_class(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            saved_instance = form.save(commit=False)

            extra_document_files = []
            if content_type == "public_document":
                uploaded_files = form.cleaned_data.get("files") or []
                if uploaded_files and not saved_instance.file:
                    saved_instance.file = uploaded_files[0]
                    extra_document_files = uploaded_files[1:]
                else:
                    extra_document_files = uploaded_files

            saved_instance.save()
            form.save_m2m()
            if hasattr(form, "save_tags"):
                form.save_tags(saved_instance)

            if content_type == "public_document":
                for f in extra_document_files:
                    m.PublicDocumentFile.objects.create(document=saved_instance, file=f, title=f.name)

            messages.success(request, f"{config['label']} با موفقیت ویرایش شد.")
            return redirect("public_content_mgmt:edit", content_type=content_type, pk=pk)
    else:
        form = form_class(instance=instance)

    return render(request, "public_content/management_form.html", {
        "form": form, "label": config["label"], "mode": "edit", "content_type": content_type,
        "instance": instance, "attachments": attachments,
    })


@login_required
def delete_view(request, content_type, pk):
    _require_access(request.user)
    config = _get_config(content_type)
    instance = get_object_or_404(config["model"], pk=pk)
    if request.method == "POST":
        instance.delete()
        messages.success(request, f"{config['label']} حذف شد.")
    return redirect("public_content_mgmt:list", content_type=content_type)


@login_required
def quick_category_create_view(request, content_type):
    """
    ایجاد سریع یک دسته‌بندی مرتبط، بدون ترک صفحه‌ی افزودن محتوا —
    فقط برای content_typeهایی که یک دسته‌بندی متناظر دارند.
    """
    from django.http import JsonResponse
    from django.utils.text import slugify

    _require_access(request.user)

    category_map = {
        "news": m.NewsCategory,
        "public_document": m.DocumentCategory,
        "faq": m.FAQCategory,
    }
    category_model = category_map.get(content_type)
    if category_model is None:
        return JsonResponse({"error": "این نوع محتوا دسته‌بندی ندارد."}, status=400)

    name = request.POST.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "نام دسته‌بندی الزامی است."}, status=400)

    existing = category_model.objects.filter(name=name).first()
    if existing:
        return JsonResponse({"id": existing.pk, "name": existing.name, "created": False})

    create_kwargs = {"name": name}
    if hasattr(category_model, "slug"):
        base_slug = slugify(name, allow_unicode=False) or f"cat-{content_type}"
        slug = base_slug
        counter = 1
        while category_model.objects.filter(slug=slug).exists():
            counter += 1
            slug = f"{base_slug}-{counter}"
        create_kwargs["slug"] = slug

    category = category_model.objects.create(**create_kwargs)
    return JsonResponse({"id": category.pk, "name": category.name, "created": True})


@login_required
def tag_suggestions_view(request):
    from django.http import JsonResponse

    _require_access(request.user)
    query = request.GET.get("q", "").strip()
    if len(query) < 1:
        return JsonResponse({"results": []})

    tags = m.Tag.objects.filter(name__icontains=query).order_by("name")[:10]
    return JsonResponse({"results": [t.name for t in tags]})


@login_required
def tag_quick_create_view(request):
    from django.http import JsonResponse

    _require_access(request.user)
    name = request.POST.get("name", "").strip()
    if not name:
        return JsonResponse({"error": "نام تگ الزامی است."}, status=400)

    tag, created = m.Tag.objects.get_or_create(name=name)
    return JsonResponse({"id": tag.pk, "name": tag.name, "created": created})


@login_required
def news_gallery_view(request, pk):
    _require_access(request.user)
    article = get_object_or_404(m.NewsArticle, pk=pk)

    if request.method == "POST":
        files = request.FILES.getlist("images")
        for f in files:
            m.NewsImage.objects.create(news_article=article, image=f)
        if files:
            messages.success(request, f"{len(files)} تصویر با موفقیت اضافه شد.")
        return redirect("public_content_mgmt:news_gallery", pk=pk)

    images = article.gallery_images.all()
    return render(request, "public_content/news_gallery.html", {"article": article, "images": images})


@login_required
def news_gallery_delete_view(request, pk, image_pk):
    _require_access(request.user)
    image = get_object_or_404(m.NewsImage, pk=image_pk, news_article_id=pk)
    if request.method == "POST":
        image.delete()
        messages.success(request, "تصویر حذف شد.")
    return redirect("public_content_mgmt:news_gallery", pk=pk)


@login_required
def document_attachments_view(request, pk):
    _require_access(request.user)
    document = get_object_or_404(m.PublicDocument, pk=pk)

    if request.method == "POST":
        files = request.FILES.getlist("files")
        for f in files:
            m.PublicDocumentFile.objects.create(document=document, file=f, title=f.name)
        if files:
            messages.success(request, f"{len(files)} فایل با موفقیت اضافه شد.")
        return redirect("public_content_mgmt:document_attachments", pk=pk)

    attachments = document.attachments.all()
    return render(request, "public_content/document_attachments.html", {
        "document": document, "attachments": attachments,
    })


@login_required
def document_attachment_delete_view(request, pk, file_pk):
    _require_access(request.user)
    attachment = get_object_or_404(m.PublicDocumentFile, pk=file_pk, document_id=pk)
    if request.method == "POST":
        attachment.delete()
        messages.success(request, "فایل حذف شد.")
    return redirect("public_content_mgmt:edit", content_type="public_document", pk=pk)
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.db import models

from . import selectors
from .forms import ContactMessageForm, SiteSearchForm
from .models import Announcement, Event, FAQ, NewsArticle, PublicDocument, Regulation
from .services import submit_contact_message


def news_list_view(request):
    category_slug = request.GET.get("category")
    search = request.GET.get("q", "").strip()
    queryset = selectors.get_published_news(category_slug=category_slug, search=search)
    from .models import NewsCategory
    all_categories = NewsCategory.objects.filter(news_articles_multi__isnull=False).distinct().order_by("name")
    featured_news = selectors.get_featured_news()
    paginator = Paginator(queryset, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "public_content/news_list.html", {
        "page_obj": page_obj,
        "featured_news": featured_news,
        "all_categories": all_categories,
        "all_categories": all_categories,
        "search": search,
    })


def news_detail_view(request, slug):
    article = selectors.get_news_by_slug(slug)
    if article is None:
        from django.http import Http404
        raise Http404("خبر مورد نظر یافت نشد.")

    from .models import NewsArticle
    NewsArticle.objects.filter(pk=article.pk).update(view_count=models.F("view_count") + 1)

    return render(request, "public_content/news_detail.html", {
        "article": article,
        "related_news": selectors.get_related_news(article),
    })


def announcement_list_view(request):
    queryset = selectors.get_published_announcements()
    paginator = Paginator(queryset, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "public_content/announcement_list.html", {"page_obj": page_obj})


def announcement_detail_view(request, slug):
    announcement = selectors.get_announcement_by_slug(slug)
    if announcement is None:
        from django.http import Http404
        raise Http404("اطلاعیه مورد نظر یافت نشد.")
    return render(request, "public_content/announcement_detail.html", {"announcement": announcement})


def event_list_view(request):
    upcoming = selectors.get_upcoming_events()
    past = selectors.get_past_events()
    paginator = Paginator(past, 10)
    past_page = paginator.get_page(request.GET.get("page"))
    return render(request, "public_content/event_list.html", {
        "upcoming_events": upcoming,
        "past_page_obj": past_page,
    })


def event_detail_view(request, slug):
    event = selectors.get_event_by_slug(slug)
    if event is None:
        from django.http import Http404
        raise Http404("رویداد مورد نظر یافت نشد.")
    return render(request, "public_content/event_detail.html", {"event": event})


def document_list_view(request):
    category_slug = request.GET.get("category")
    queryset = selectors.get_visible_documents(category_slug=category_slug)
    paginator = Paginator(queryset, 15)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "public_content/document_list.html", {"page_obj": page_obj})


def regulation_list_view(request):
    queryset = selectors.get_published_regulations()
    paginator = Paginator(queryset, 15)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "public_content/regulation_list.html", {"page_obj": page_obj})


def regulation_detail_view(request, slug):
    regulation = selectors.get_regulation_by_slug(slug)
    if regulation is None:
        from django.http import Http404
        raise Http404("مورد یافت نشد.")
    return render(request, "public_content/regulation_detail.html", {"regulation": regulation})


def faq_view(request):
    faqs = selectors.get_active_faqs()
    return render(request, "public_content/faq.html", {"faqs": faqs})


def contact_view(request):
    if request.method == "POST":
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            submit_contact_message(**form.cleaned_data)
            messages.success(request, "پیام شما با موفقیت ارسال شد.")
            return redirect("public_content:contact")
    else:
        form = ContactMessageForm()
    return render(request, "public_content/contact.html", {"form": form})


def search_view(request):
    form = SiteSearchForm(request.GET or None)
    results = {"news": [], "announcements": [], "events": [], "documents": [], "faqs": []}
    query = ""

    if form.is_valid():
        query = form.cleaned_data["q"]
        results["news"] = selectors.get_published_news().filter(title__icontains=query)[:10]
        results["announcements"] = selectors.get_published_announcements().filter(
            title__icontains=query
        )[:10]
        results["events"] = Event.objects.published().filter(title__icontains=query)[:10]
        results["documents"] = selectors.get_visible_documents().filter(title__icontains=query)[:10]
        results["faqs"] = selectors.get_active_faqs().filter(question__icontains=query)[:10]

    total_count = sum(len(v) for v in results.values())
    return render(request, "public_content/search.html", {
        "form": form, "results": results, "query": query, "total_count": total_count,
    })


def board_view(request):
    """
    طبق STEP 14 سند: از مدل BoardMembership موجود استفاده می‌شود،
    نه یک مدل مستقل جدید. فقط رکوردهای Public + Active نمایش داده می‌شوند.
    """
    from apps.board.models import BoardMembership

    memberships = (
        BoardMembership.objects.filter(is_active=True, is_public_visible=True)
        .select_related("user")
        .order_by("position", "start_date")
    )
    return render(request, "public_content/board.html", {"memberships": memberships})


def committees_view(request):
    """
    طبق STEP 15 سند: از مدل‌های Committee/CommitteeMembership موجود
    استفاده می‌شود.
    """
    from apps.committees.models import Committee

    committees = (
        Committee.objects.filter(is_active=True, is_public_visible=True)
        .prefetch_related("memberships__user")
    )
    return render(request, "public_content/committees.html", {"committees": committees})


from django.http import HttpResponse
from django.template.loader import render_to_string


def robots_txt_view(request):
    """
    طبق STEP 28 سند: مسیرهای حساس محدود می‌شوند، اما این ابزار
    امنیتی نیست — Authorization همچنان در Backend اجرا می‌شود.
    """
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /portal/",
        "Disallow: /login/",
        "Disallow: /api/",
        "",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def representatives_view(request):
    """
    طبق بخش ۲۱ سند: نام، عنوان مسئولیت، شهرستان — بدون اطلاعات خصوصی.
    """
    from apps.authorization.selectors import public_representatives

    representatives = public_representatives()
    return render(request, "public_content/representatives.html", {"representatives": representatives})


from apps.website.utils import full_jalali_date


def news_short_redirect_view(request, pk):
    from django.shortcuts import get_object_or_404, redirect

    from .models import NewsArticle

    article = get_object_or_404(NewsArticle, pk=pk)
    return redirect(article.get_absolute_url())
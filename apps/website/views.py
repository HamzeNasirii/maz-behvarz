from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django_ratelimit.decorators import ratelimit
from django.contrib import messages

from .constants import MEMBERSHIP_TERMS_TEXT
from .forms import MembershipApplicationForm, ForcedPasswordChangeForm


def home_view(request):
    from apps.public_content.models import HeroSlide
    from apps.public_content import selectors
    from apps.board.selectors import public_board_history

    return render(request, "website/home.html", {
        "hero_slides": HeroSlide.objects.filter(is_active=True).order_by("-created_at")[:5],
        "featured_announcements": selectors.get_published_announcements(featured_only=True)[:3],
        "latest_news": selectors.get_published_news()[:3],
        "upcoming_events": selectors.get_upcoming_events(limit=3),
        "board_history": public_board_history(),
    })

def about_view(request):
    return render(request, "website/about.html")


def contact_view(request):
    return render(request, "website/contact.html")

@ratelimit(key="ip", rate="5/h", method="POST", block=True)
def membership_application_view(request):
    if request.user.is_authenticated and hasattr(request.user, "member_profile") and request.user.member_profile.approval_status == "approved":
        messages.info(request, "شما در حال حاضر عضو تأییدشده هستید.")
        return redirect("members_portal:dashboard")

    if request.method == "POST":
        form = MembershipApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("website:membership_application_success")
    else:
        form = MembershipApplicationForm()
    return render(
        request,
        "website/membership_application.html",
        {"form": form, "terms_text": MEMBERSHIP_TERMS_TEXT},
    )

def membership_application_success_view(request):
    return render(request, "website/membership_application_success.html")

def about_history_view(request):
    return render(request, "website/about_history.html")


def about_mission_view(request):
    return render(request, "website/about_mission.html")


def about_objectives_view(request):
    return render(request, "website/about_objectives.html")


def about_organizational_structure_view(request):
    """
    طبق STEP 16/17 سند: از Organization Core واقعی (Province تا
    HealthHouse) استفاده می‌شود، هیچ ساختاری Hard-code نشده. این
    View فقط نمای درختی سطح بالا (استان → شهرستان‌ها) را نشان
    می‌دهد؛ برای عمق بیشتر، همان API آبشاری گام ۱۳ (`/api/organization/`)
    از قبل موجود است.
    """
    from apps.organization.models import Province

    provinces = Province.objects.filter(is_active=True).prefetch_related("counties")
    return render(request, "website/about_organizational_structure.html", {"provinces": provinces})


def privacy_view(request):
    return render(request, "website/privacy.html")


def terms_view(request):
    return render(request, "website/terms.html")

def membership_letter_view(request):
    from apps.organization.models import HealthHouse

    from .utils import format_jalali_today

    full_name = request.GET.get("full_name", "").strip()
    national_code = request.GET.get("national_code", "").strip()
    health_house_id = request.GET.get("health_house", "")

    health_house = HealthHouse.objects.filter(pk=health_house_id).select_related(
        "center__network"
    ).first() if health_house_id else None

    context = {
        "full_name": full_name,
        "national_code": national_code,
        "health_house": health_house,
        "network_name": health_house.center.network.name if health_house else "",
        "jalali_date": format_jalali_today(),
    }
    return render(request, "website/membership_letter.html", context)


from apps.authorization.services import Authorization
from apps.board.models import BoardMembership
from apps.committees.models import Committee
from apps.employment.models import EmploymentAssignment
from apps.members.models import Member
from apps.organization.models import County


def _has_full_access(user):
    """
    فقط Staff/Superuser واقعی — طبق تصمیم صریح اصلاح نشتی بین‌استانی،
    دیگر هیچ Bypass عمومی‌ای برای رئیس/دبیر هیئت‌مدیره وجود ندارد؛
    دسترسی آن‌ها از طریق RoleAssignment واقعیشان (Scope استان) تعیین
    می‌شود، دقیقاً مثل هر کاربر دیگری.
    """
    return user.is_superuser or user.is_staff


def member_statistics(user):
    if _has_full_access(user):
        members = Member.objects.all()
    else:
        members = Member.objects.for_user(user)

    return {
        "total": members.count(),
        "pending": members.filter(approval_status="pending").count(),
        "approved": members.filter(approval_status="approved").count(),
        "rejected": members.filter(approval_status="rejected").count(),
        "with_active_membership": members.with_active_membership().count(),
    }


def employment_statistics(user):
    if _has_full_access(user):
        assignments = EmploymentAssignment.objects.active().select_related(
            "health_house__center__network__county"
        )
    else:
        assignments = Authorization.scope_queryset(
            user, EmploymentAssignment.objects.active()
        ).select_related("health_house__center__network__county")

    by_county = {}
    for assignment in assignments:
        county_name = assignment.health_house.center.network.county.name
        by_county[county_name] = by_county.get(county_name, 0) + 1

    return {
        "total_active": assignments.count(),
        "primary_only": assignments.filter(is_primary=True).count(),
        "by_county": by_county,
    }


def board_and_committee_statistics(user):
    """
    ⚠️ نکته‌ی معماری: Board (هیئت‌مدیره) طبق تصمیم فاز ۱۴، یک نهاد
    واحد و سراسری است (بدون مفهوم Scope/استان در مدل) — پس شمارش
    اعضای هیئت‌مدیره عمداً بدون فیلتر می‌ماند. Committee برخلاف Board،
    مفهوم Scope جغرافیایی واقعی دارد (فاز ۳۰)، پس باید فیلتر شود.
    """
    committees = Committee.objects.filter(is_active=True)
    if not _has_full_access(user):
        committees = Authorization.scope_queryset(user, committees)

    return {
        "active_board_members": BoardMembership.objects.filter(is_active=True).count(),
        "committees_count": committees.count(),
    }


def county_coverage_statistics(user):
    from apps.authorization.scope_helpers import get_accessible_province_ids

    counties = County.objects.filter(is_active=True)
    accessible_province_ids = get_accessible_province_ids(user)
    if accessible_province_ids is not None:
        counties = counties.filter(province_id__in=accessible_province_ids)

    total_counties = counties.count()
    counties_with_active_members = counties.filter(
        health_networks__health_centers__health_houses__employment_assignments__is_active=True
    ).distinct().count()

    return {
        "total_counties": total_counties,
        "counties_with_active_members": counties_with_active_members,
    }


def extended_admin_statistics(user):
    """
    آمار تکمیلی Dashboard — همگی اکنون Scope-aware.
    """
    from apps.forums.models import Forum, ForumPost
    from apps.members.models import MembershipFee, MemberRemovalProposal
    from apps.requests.models import Request

    forums = Forum.objects.filter(is_active=True)
    requests_qs = Request.objects.filter(status__in=["submitted", "under_review", "resubmitted"])

    if _has_full_access(user):
        fees = MembershipFee.objects.filter(payment_status="unpaid")
        removal_proposals = MemberRemovalProposal.objects.filter(status="pending")
    else:
        forums = Authorization.scope_queryset(user, forums)
        requests_qs = Authorization.scope_queryset(user, requests_qs)
        scoped_members = Member.objects.for_user(user)
        fees = MembershipFee.objects.filter(payment_status="unpaid", member__in=scoped_members)
        removal_proposals = MemberRemovalProposal.objects.filter(status="pending", member__in=scoped_members)

    return {
        "active_forums": forums.count(),
        "total_forum_posts": ForumPost.objects.filter(is_deleted=False, forum__in=forums).count(),
        "unpaid_fees": fees.count(),
        "pending_removal_proposals": removal_proposals.count(),
        "pending_requests_total": requests_qs.count(),
    }
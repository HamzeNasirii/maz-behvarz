from django.db import models
from django.utils import timezone

from .choices import MembershipStatus


class MembershipPeriodQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def historical(self):
        return self.filter(is_active=False)

    def at_date(self, date):
        return self.filter(start_date__lte=date).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=date)
        )

    def current(self):
        return self.active().at_date(timezone.localdate())

    def for_member(self, member):
        return self.filter(member=member)


class MemberQuerySet(models.QuerySet):
    def with_active_membership(self):
        today = timezone.localdate()
        return self.filter(
            membership_periods__is_active=True,
            membership_periods__start_date__lte=today,
        ).filter(
            models.Q(membership_periods__end_date__isnull=True)
            | models.Q(membership_periods__end_date__gte=today)
        ).distinct()

    def for_user(self, user):
        """
        Scope-aware queryset — فقط اعضایی که در محدوده‌ی دسترسی فعال
        این کاربر جای می‌گیرند.
        """
        from apps.authorization.services import Authorization

        return Authorization.scope_queryset(user, self)

    # --- QuerySetهای Lifecycle (طبق بخش ۲۵ سند) ---
    def draft(self):
        return self.filter(status=MembershipStatus.DRAFT)

    def pending_review(self):
        return self.filter(status__in=[MembershipStatus.SUBMITTED, MembershipStatus.UNDER_REVIEW])

    def active(self):
        return self.filter(status=MembershipStatus.ACTIVE)

    def suspended(self):
        return self.filter(status=MembershipStatus.SUSPENDED)

    def expired(self):
        return self.filter(status=MembershipStatus.EXPIRED)

    def cancelled(self):
        return self.filter(status=MembershipStatus.CANCELLED)
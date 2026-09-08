from django.db import models
from django.utils import timezone


class RoleAssignmentQuerySet(models.QuerySet):
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

    def for_user(self, user):
        return self.filter(user=user)

    def for_user_at(self, user, date):
        return self.for_user(user).at_date(date)
from django.db import models


class CommitteeStatus(models.TextChoices):
    DRAFT = "draft", "پیش‌نویس"
    ACTIVE = "active", "فعال"
    SUSPENDED = "suspended", "معلق"
    ENDED = "ended", "پایان‌یافته"
    ARCHIVED = "archived", "بایگانی‌شده"


ALLOWED_COMMITTEE_TRANSITIONS = {
    CommitteeStatus.DRAFT: {CommitteeStatus.ACTIVE},
    CommitteeStatus.ACTIVE: {CommitteeStatus.SUSPENDED, CommitteeStatus.ENDED},
    CommitteeStatus.SUSPENDED: {CommitteeStatus.ACTIVE, CommitteeStatus.ENDED},
    CommitteeStatus.ENDED: {CommitteeStatus.ARCHIVED},
    CommitteeStatus.ARCHIVED: set(),
}
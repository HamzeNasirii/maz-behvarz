from django.db import models


class BoardPosition(models.TextChoices):
    CHAIRMAN = "chairman", "رئیس"
    VICE_CHAIRMAN = "vice_chairman", "نایب رئیس"
    TREASURER = "treasurer", "خزانه‌دار"
    SECRETARY = "secretary", "دبیر"
    MEMBER = "member", "عضو"


class BoardStatus(models.TextChoices):
    DRAFT = "draft", "پیش‌نویس"
    ACTIVE = "active", "فعال"
    SUSPENDED = "suspended", "معلق"
    ENDED = "ended", "پایان‌یافته"
    ARCHIVED = "archived", "بایگانی‌شده"


ALLOWED_BOARD_TRANSITIONS = {
    BoardStatus.DRAFT: {BoardStatus.ACTIVE},
    BoardStatus.ACTIVE: {BoardStatus.SUSPENDED, BoardStatus.ENDED},
    BoardStatus.SUSPENDED: {BoardStatus.ACTIVE, BoardStatus.ENDED},
    BoardStatus.ENDED: {BoardStatus.ARCHIVED},
    BoardStatus.ARCHIVED: set(),
}
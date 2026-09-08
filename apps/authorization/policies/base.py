class BasePolicy:
    """
    هر Policy می‌تواند can_view/can_create/can_update/can_delete/can_approve
    را بازنویسی کند. رسیدن به این‌جا یعنی RBAC و Scope قبلاً تأیید شده‌اند؛
    Policy فقط قواعد تجاری اضافه (ABAC) را اعمال می‌کند.
    """

    def can_view(self, user, obj):
        return True

    def can_create(self, user, obj):
        return True

    def can_update(self, user, obj):
        return True

    def can_delete(self, user, obj):
        return True

    def can_approve(self, user, obj):
        return True
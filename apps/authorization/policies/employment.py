from .base import BasePolicy


class EmploymentAssignmentPolicy(BasePolicy):
    def can_delete(self, user, obj):
        # طبق قاعده‌ی ABAC سند: «Assignment تاریخی نباید Delete شود»
        return False
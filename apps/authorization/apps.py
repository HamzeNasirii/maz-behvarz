from django.apps import AppConfig


class AuthorizationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.authorization"
    verbose_name = "احراز هویت و دسترسی"

    def ready(self):
        from apps.employment.models import EmploymentAssignment
        from apps.members.models import Member

        from .policies.employment import EmploymentAssignmentPolicy
        from .policies.member import MemberPolicy
        from .registry import register_policy
        from .resolvers import register_all

        register_all()
        register_policy(Member, MemberPolicy())
        register_policy(EmploymentAssignment, EmploymentAssignmentPolicy())
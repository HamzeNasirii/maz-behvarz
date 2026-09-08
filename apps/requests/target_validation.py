"""
Generic Relation Security — Whitelist مدل‌های مجاز برای اتصال به
Request از طریق content_object. این لیست از Audit واقعی (بخش A تا I
بالا) استخراج شده، نه حدسی: هر مدلی که در فاز‌های قبل واقعاً بخشی از
Workflow اداری انجمن بوده اینجاست.
"""

from django.core.exceptions import ValidationError


def get_allowed_target_models():
    from apps.authorization.models import RoleAssignment
    from apps.board.models import Board, BoardMembership
    from apps.committees.models import Committee, CommitteeMembership
    from apps.documents.models import Document
    from apps.employment.models import EmploymentAssignment
    from apps.members.models import Member

    return (
        Member,
        EmploymentAssignment,
        RoleAssignment,
        Committee,
        CommitteeMembership,
        Board,
        BoardMembership,
        Document,
    )


def validate_target_object(content_object):
    """
    فقط Type را Whitelist می‌کند — چک Scope/Authorization خود آبجکت
    در جای دیگری (Authorization.can روی خود Request) انجام می‌شود.
    """
    if content_object is None:
        return
    allowed_models = get_allowed_target_models()
    if not isinstance(content_object, allowed_models):
        raise ValidationError(
            f"نوع «{type(content_object).__name__}» مجاز به اتصال به Request نیست."
        )
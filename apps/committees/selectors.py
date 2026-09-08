from .authorization import committees_for_user
from .choices import CommitteeStatus
from .models import Committee, CommitteeMembership


def active_committees(user):
    return committees_for_user(user, Committee.objects.filter(status=CommitteeStatus.ACTIVE))


def public_committees():
    return Committee.objects.filter(status=CommitteeStatus.ACTIVE, is_public_visible=True, is_active=True)


def memberships_for_committee(committee):
    return CommitteeMembership.objects.filter(committee=committee, is_active=True).select_related("user")


def committee_history(user, committee):
    return committee.status_history.select_related("actor").all()
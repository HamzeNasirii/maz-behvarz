from .permissions import can_manage_organization


def organization_management_flag(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {"can_manage_organization": can_manage_organization(user)}
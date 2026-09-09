def can_manage_members_flag(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}

    from .permissions import can_manage_members

    return {"can_manage_members_ctx": can_manage_members(user)}
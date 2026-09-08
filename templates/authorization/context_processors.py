from apps.board.permissions import is_board_leadership


def pending_dashboard_flag(request):
    if not request.user.is_authenticated:
        return {}
    user = request.user
    can_view = user.is_superuser or user.is_staff or is_board_leadership(user)
    return {"can_view_pending_dashboard": can_view}
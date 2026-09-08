def can_manage_organization(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True

    from apps.board.permissions import is_board_leadership

    return is_board_leadership(user)
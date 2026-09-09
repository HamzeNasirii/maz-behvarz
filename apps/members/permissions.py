def can_manage_members(user):
    """
    دسترسی کامل به مدیریت اعضا — طبق همون قاعده‌ی همیشگی پروژه: staff/
    superuser یا رئیس/دبیر صنف (چون انجمن فقط یک استان دارد).
    """
    """
        دسترسی کامل به مدیریت اعضا — Staff/Superuser، رئیس/نایب‌رئیس/دبیر،
        و از این پس خزانه‌دار (برای مدیریت حق‌عضویت‌ها و پرداخت‌ها).
        """
    if not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True

    from apps.board.permissions import is_board_leadership, is_treasurer

    return is_board_leadership(user) or is_treasurer(user)
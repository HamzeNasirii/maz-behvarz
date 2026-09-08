from .choices import BoardStatus
from .models import Board, BoardMembership


def current_board():
    """طبق طراحی، معمولاً فقط یک Board در وضعیت ACTIVE داریم."""
    return Board.objects.filter(status=BoardStatus.ACTIVE).first()


def historical_boards():
    return Board.objects.exclude(status=BoardStatus.ACTIVE)


def public_boards():
    return Board.objects.filter(status=BoardStatus.ACTIVE, is_public_visible=True)


def memberships_for_board(board):
    return BoardMembership.objects.filter(board=board, is_active=True).select_related("user")


def board_history(board):
    return board.status_history.select_related("actor").all()

def public_board_history():
    """
    تاریخچه‌ی دوره‌های هیئت‌مدیره برای نمایش عمومی — فقط دوره‌ها و
    عضویت‌هایی که صراحتاً is_public_visible=True هستند.
    """
    from .models import Board

    boards = Board.objects.filter(is_public_visible=True).order_by("start_date").select_related()

    result = []
    for index, board in enumerate(boards, start=1):
        memberships = board.memberships.filter(is_public_visible=True).select_related(
            "user", "user__member_profile"
        ).order_by("position")
        result.append({"period_number": index, "board": board, "memberships": memberships})
    return result
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
    جدیدترین دوره ابتدا نمایش داده می‌شود؛ period_number اما بر
    اساس ترتیب زمانی واقعی (قدیمی‌ترین = ۱) محاسبه می‌شود، نه
    ترتیب نمایش.
    """
    from django.db.models import Case, When, Value, IntegerField
    from .choices import BoardPosition
    from .models import Board

    position_order = [
        BoardPosition.CHAIRMAN, BoardPosition.VICE_CHAIRMAN,
        BoardPosition.TREASURER, BoardPosition.SECRETARY, BoardPosition.MEMBER,
    ]
    position_rank = Case(
        *[When(position=pos, then=Value(i)) for i, pos in enumerate(position_order)],
        default=Value(len(position_order)),
        output_field=IntegerField(),
    )

    boards = Board.objects.filter(is_public_visible=True).order_by("start_date").select_related()

    result = []
    for index, board in enumerate(boards, start=1):
        memberships = (
            board.memberships.filter(is_public_visible=True)
            .select_related("user", "user__member_profile")
            .annotate(_position_rank=position_rank)
            .order_by("_position_rank")
        )
        result.append({"period_number": index, "board": board, "memberships": memberships})

    result.reverse()  # جدیدترین دوره بالا؛ شماره‌ی واقعی دوره حفظ می‌شود
    return result
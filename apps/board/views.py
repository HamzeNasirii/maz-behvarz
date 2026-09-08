from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.db.models import Count, Q

from apps.authorization.services import Authorization

from . import selectors
from .forms import (
    BoardCreateForm,
    BoardMembershipCreateForm,
    BoardMembershipEndForm,
    BoardOptionalReasonForm,
    BoardReasonForm,
)
from .models import Board, BoardMembership
from .services import (
    activate_board,
    add_board_member,
    archive_board,
    create_board,
    end_board,
    remove_board_member,
    suspend_board,
)


@login_required
def management_list_view(request):
    if not Authorization.has_permission_code(request.user, "board.view"):
        raise PermissionDenied("شما مجوز مشاهده‌ی این فهرست را ندارید.")

    create_form = None
    if Authorization.has_permission_code(request.user, "board.create"):
        if request.method == "POST":
            create_form = BoardCreateForm(request.POST)
            if create_form.is_valid():
                create_board(created_by=request.user, **create_form.cleaned_data)
                messages.success(request, "دوره‌ی جدید هیئت‌مدیره ایجاد شد.")
                return redirect("board_mgmt:list")
        else:
            create_form = BoardCreateForm()

    boards = Board.objects.annotate(
        member_count=Count("memberships", filter=Q(memberships__is_active=True))
    ).all()
    return render(request, "board/management_list.html", {"boards": boards, "create_form": create_form})


@login_required
def management_detail_view(request, pk):
    board = get_object_or_404(Board, pk=pk)
    if not Authorization.has_permission_code(request.user, "board.view"):
        raise PermissionDenied("شما مجوز مشاهده‌ی این دوره را ندارید.")

    members = selectors.memberships_for_board(board)
    history = selectors.board_history(board)
    add_member_form = BoardMembershipCreateForm()

    return render(request, "board/management_detail.html", {
        "board": board, "members": members, "history": history, "add_member_form": add_member_form,
    })


@login_required
def management_create_view(request):
    """طبق درخواست صریح، این صفحه دیگر جداگانه استفاده نمی‌شود — مسیر فقط برای سازگاری عقب‌رو نگه داشته شده."""
    return redirect("board_mgmt:list")


def _handle_board_transition(request, pk, transition_func, requires_reason, success_message):
    board = get_object_or_404(Board, pk=pk)
    if request.method == "POST":
        form = BoardReasonForm(request.POST) if requires_reason else BoardOptionalReasonForm(request.POST)
        if form.is_valid():
            try:
                transition_func(board=board, actor=request.user, reason=form.cleaned_data.get("reason", ""))
                messages.success(request, success_message)
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
            return redirect("board_mgmt:detail", pk=board.pk)
    else:
        form = BoardReasonForm() if requires_reason else BoardOptionalReasonForm()
    return render(request, "board/transition_form.html", {"form": form, "board": board})


@login_required
def activate_view(request, pk):
    return _handle_board_transition(request, pk, activate_board, False, "دوره فعال شد.")


@login_required
def suspend_view(request, pk):
    return _handle_board_transition(request, pk, suspend_board, True, "دوره معلق شد.")


@login_required
def end_view(request, pk):
    return _handle_board_transition(request, pk, end_board, False, "دوره پایان یافت.")


@login_required
def archive_view(request, pk):
    return _handle_board_transition(request, pk, archive_board, False, "دوره بایگانی شد.")


@login_required
def member_add_view(request, pk):
    board = get_object_or_404(Board, pk=pk)
    if not Authorization.has_permission_code(request.user, "board.manage_members"):
        raise PermissionDenied("شما مجوز افزودن عضو را ندارید.")

    if request.method == "POST":
        form = BoardMembershipCreateForm(request.POST)
        if form.is_valid():
            try:
                add_board_member(
                    board=board, added_by=request.user,
                    user=form.cleaned_data["user"], position=form.cleaned_data["position"],
                    start_date=form.cleaned_data["start_date"], reason=form.cleaned_data["reason"],
                )
                messages.success(request, "عضو با موفقیت اضافه شد.")
            except (PermissionDenied, ValidationError) as exc:
                messages.error(request, str(exc))
            return redirect("board_mgmt:detail", pk=board.pk)
    else:
        form = BoardMembershipCreateForm()
    return render(request, "board/member_add.html", {"form": form, "board": board})


@login_required
def member_remove_view(request, membership_pk):
    membership = get_object_or_404(BoardMembership, pk=membership_pk)
    if not Authorization.has_permission_code(request.user, "board.manage_members"):
        raise PermissionDenied("شما مجوز حذف این عضو را ندارید.")

    if request.method == "POST":
        form = BoardMembershipEndForm(request.POST)
        if form.is_valid():
            remove_board_member(
                membership=membership, removed_by=request.user,
                end_date=form.cleaned_data["end_date"], reason=form.cleaned_data["reason"],
            )
            messages.success(request, "عضویت پایان یافت.")
            return redirect("board_mgmt:detail", pk=membership.board_id or 0)
    else:
        form = BoardMembershipEndForm(initial={"end_date": timezone.localdate()})
    return render(request, "board/member_remove.html", {"form": form, "membership": membership})


@login_required
def user_search_suggestions_view(request):
    from django.http import JsonResponse
    from apps.members.models import Member

    if not Authorization.has_permission_code(request.user, "board.manage_members"):
        raise PermissionDenied("شما مجوز این عملیات را ندارید.")

    query = request.GET.get("q", "").strip()
    if len(query) < 2:
        return JsonResponse({"results": []})

    from django.db.models import Q
    members = Member.objects.filter(
        Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query) | Q(user__username__icontains=query),
        status="active",
    ).select_related("user")[:15]

    results = [
        {"pk": m.user.pk, "name": m.user.get_full_name() or m.user.username, "national_code": m.user.username}
        for m in members
    ]
    return JsonResponse({"results": results})
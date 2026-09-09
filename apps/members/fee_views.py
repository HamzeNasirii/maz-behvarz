from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .fee_forms import MembershipFeeCreateForm, MembershipFeePaymentForm
from .models import Member, MembershipFee
from .permissions import can_manage_members
from .services import record_fee_payment
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.exceptions import PermissionDenied, ValidationError
from apps.board.permissions import is_board_leadership


def _require_access(user):
    if not can_manage_members(user):
        raise PermissionDenied("شما مجوز مدیریت حق عضویت را ندارید.")


@login_required
def fee_list_view(request):
    from django.db.models import Exists, OuterRef, Q

    from .fee_forms import FeeFilterForm
    from .models import FeeChangeRequest

    _require_access(request.user)

    fees = MembershipFee.objects.select_related("member__user").annotate(
        has_pending_change=Exists(
            FeeChangeRequest.objects.filter(fee=OuterRef("pk"), status="pending")
        )
    ).order_by("-due_date")

    filter_form = FeeFilterForm(request.GET or None)
    if filter_form.is_valid():
        data = filter_form.cleaned_data
        if data.get("q"):
            fees = fees.filter(
                Q(member__user__first_name__icontains=data["q"])
                | Q(member__user__last_name__icontains=data["q"])
                | Q(member__user__username__icontains=data["q"])
            )
        if data.get("payment_status"):
            fees = fees.filter(payment_status=data["payment_status"])
        if data.get("due_date_from"):
            fees = fees.filter(due_date__gte=data["due_date_from"])
        if data.get("due_date_to"):
            fees = fees.filter(due_date__lte=data["due_date_to"])
        if data.get("payment_date_from"):
            fees = fees.filter(payment_date__gte=data["payment_date_from"])
        if data.get("payment_date_to"):
            fees = fees.filter(payment_date__lte=data["payment_date_to"])

    from apps.board.permissions import is_treasurer

    return render(request, "members/fee_list.html", {
        "fees": fees, "filter_form": filter_form,
        "can_decide": is_board_leadership(request.user) or is_treasurer(
            request.user) or request.user.is_staff or request.user.is_superuser,
    })


@login_required
def fee_change_cancel_view(request, pk):
    from .models import FeeChangeRequest
    from .services import cancel_fee_change

    change_request = get_object_or_404(FeeChangeRequest, pk=pk)
    if request.method == "POST":
        try:
            cancel_fee_change(change_request=change_request, actor=request.user)
            messages.success(request, "درخواست شما لغو شد.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, str(exc))
    return redirect("members_fees:change_list")


@login_required
def fee_create_view(request, member_pk):
    """
    عضو از طریق URL (نه فرم) مشخص می‌شود — طبق قاعده‌ی «کاربر نباید
    خودش عضو را از یک فهرست انتخاب کند»، این View همیشه از صفحه‌ی
    جزئیات یک عضو مشخص باز می‌شود.
    """
    _require_access(request.user)
    member = get_object_or_404(Member, pk=member_pk)

    if request.method == "POST":
        form = MembershipFeeCreateForm(request.POST)
        if form.is_valid():
            fee = form.save(commit=False)
            fee.member = member
            fee.save()
            messages.success(request, "حق عضویت با موفقیت ثبت شد.")
            return redirect("members_portal:member_detail", pk=member.pk)
    else:
        form = MembershipFeeCreateForm()

    return render(request, "members/fee_form.html", {"form": form, "mode": "create", "member": member})


@login_required
def fee_mark_paid_view(request, pk):
    _require_access(request.user)
    fee = get_object_or_404(MembershipFee, pk=pk)

    if request.method == "POST":
        form = MembershipFeePaymentForm(request.POST)
        if form.is_valid():
            record_fee_payment(
                fee=fee, paid_by=request.user,
                payment_date=form.cleaned_data["payment_date"],
                payment_method=form.cleaned_data["payment_method"],
                reference_number=form.cleaned_data["reference_number"],
            )
            messages.success(request, "پرداخت ثبت شد.")
            return redirect("members_portal:member_detail", pk=fee.member.pk)
    else:
        form = MembershipFeePaymentForm()
    return render(request, "members/fee_payment_form.html", {"form": form, "fee": fee})


@login_required
def fee_delete_view(request, pk):
    from django.contrib import messages
    from apps.members.services import delete_membership_fee

    fee = get_object_or_404(MembershipFee, pk=pk)
    member_pk = fee.member_id

    if request.method == "POST":
        try:
            delete_membership_fee(fee=fee, actor=request.user)
            messages.success(request, "حق عضویت حذف شد.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, str(exc))

    return redirect("members_portal:member_detail", pk=member_pk)


@login_required
def fee_edit_request_view(request, pk):
    from .fee_forms import FeeEditRequestForm
    from .services import propose_fee_edit

    fee = get_object_or_404(MembershipFee, pk=pk)
    _require_access(request.user)

    if request.method == "POST":
        form = FeeEditRequestForm(request.POST)
        if form.is_valid():
            try:
                propose_fee_edit(
                    fee=fee, proposed_by=request.user,
                    new_amount=form.cleaned_data["new_amount"], new_due_date=form.cleaned_data["new_due_date"],
                    reason=form.cleaned_data["reason"],
                )
                messages.success(request, "درخواست اصلاح ثبت شد و برای تصمیم‌گیری ارسال شد.")
                return redirect("members_fees:list")
            except PermissionDenied as exc:
                messages.error(request, str(exc))
    else:
        form = FeeEditRequestForm(initial={"new_amount": int(fee.amount), "new_due_date": fee.due_date})

    return render(request, "members/fee_change_request_form.html", {"form": form, "fee": fee, "action_label": "ویرایش"})


@login_required
def fee_delete_request_view(request, pk):
    from .fee_forms import FeeDeleteRequestForm
    from .services import propose_fee_delete

    fee = get_object_or_404(MembershipFee, pk=pk)
    _require_access(request.user)

    if request.method == "POST":
        form = FeeDeleteRequestForm(request.POST)
        if form.is_valid():
            try:
                propose_fee_delete(fee=fee, proposed_by=request.user, reason=form.cleaned_data["reason"])
                messages.success(request, "درخواست حذف ثبت شد و برای تصمیم‌گیری ارسال شد.")
                return redirect("members_fees:list")
            except PermissionDenied as exc:
                messages.error(request, str(exc))
    else:
        form = FeeDeleteRequestForm()

    return render(request, "members/fee_change_request_form.html", {"form": form, "fee": fee, "action_label": "حذف"})


@login_required
def fee_change_list_view(request):
    from .models import FeeChangeRequest

    if not (request.user.is_staff or request.user.is_superuser or is_board_leadership(request.user)):
        raise PermissionDenied("شما مجوز مشاهده‌ی این فهرست را ندارید.")

    change_requests = FeeChangeRequest.objects.select_related(
        "fee__member__user", "proposed_by", "decided_by"
    ).order_by("-created_at")

    if not (request.user.is_staff or request.user.is_superuser):
        from . import selectors
        scoped_members = selectors._members_queryset_for(request.user)
        change_requests = change_requests.filter(fee__member__in=scoped_members)

    return render(request, "members/fee_change_list.html", {"change_requests": change_requests})


@login_required
def fee_change_approve_view(request, pk):
    from .models import FeeChangeRequest
    from .services import approve_fee_change

    change_request = get_object_or_404(FeeChangeRequest, pk=pk)
    if request.method == "POST":
        try:
            approve_fee_change(change_request=change_request, actor=request.user, note=request.POST.get("note", ""))
            messages.success(request, "درخواست تأیید و اعمال شد.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, str(exc))
    return redirect("members_fees:change_list")


@login_required
def fee_change_reject_view(request, pk):
    from .models import FeeChangeRequest
    from .services import reject_fee_change

    change_request = get_object_or_404(FeeChangeRequest, pk=pk)
    if request.method == "POST":
        try:
            reject_fee_change(change_request=change_request, actor=request.user, note=request.POST.get("note", ""))
            messages.success(request, "درخواست رد شد.")
        except (PermissionDenied, ValidationError) as exc:
            messages.error(request, str(exc))
    return redirect("members_fees:change_list")


@login_required
def treasurer_financial_report_view(request):
    import json
    from django.db.models import Sum, Count
    from django.db.models.functions import TruncMonth
    from apps.board.permissions import is_board_leadership, is_treasurer
    from .fee_forms import FeeFilterForm

    if not (request.user.is_staff or request.user.is_superuser or is_board_leadership(request.user) or is_treasurer(
            request.user)):
        raise PermissionDenied("شما مجوز مشاهده‌ی گزارش‌های مالی را ندارید.")

    fees = MembershipFee.objects.select_related(
        "member__user"
    ).select_related(None)

    if not (request.user.is_staff or request.user.is_superuser):
        from . import selectors
        scoped_members = selectors._members_queryset_for(request.user)
        fees = fees.filter(member__in=scoped_members)

    filter_form = FeeFilterForm(request.GET or None)
    if filter_form.is_valid():
        data = filter_form.cleaned_data
        if data.get("q"):
            from django.db.models import Q
            fees = fees.filter(
                Q(member__user__first_name__icontains=data["q"])
                | Q(member__user__last_name__icontains=data["q"])
                | Q(member__user__username__icontains=data["q"])
            )
        if data.get("payment_status"):
            fees = fees.filter(payment_status=data["payment_status"])
        if data.get("due_date_from"):
            fees = fees.filter(due_date__gte=data["due_date_from"])
        if data.get("due_date_to"):
            fees = fees.filter(due_date__lte=data["due_date_to"])
        if data.get("payment_date_from"):
            fees = fees.filter(payment_date__gte=data["payment_date_from"])
        if data.get("payment_date_to"):
            fees = fees.filter(payment_date__lte=data["payment_date_to"])

    payment_method_filter = request.GET.get("payment_method", "")
    if payment_method_filter:
        fees = fees.filter(payment_method=payment_method_filter)

    paid_fees = fees.filter(payment_status="paid")
    unpaid_fees = fees.filter(payment_status="unpaid")

    summary = {
        "total_paid_amount": int(paid_fees.aggregate(s=Sum("amount"))["s"] or 0),
        "total_paid_count": paid_fees.count(),
        "total_unpaid_amount": int(unpaid_fees.aggregate(s=Sum("amount"))["s"] or 0),
        "total_unpaid_count": unpaid_fees.count(),
    }

    monthly_trend = (
        paid_fees.exclude(payment_date__isnull=True)
        .annotate(month=TruncMonth("payment_date"))
        .values("month")
        .annotate(total=Sum("amount"))
        .order_by("month")
    )
    from apps.website.utils import gregorian_to_jalali
    monthly_labels = []
    monthly_values = []
    for row in monthly_trend:
        jy, jm, _ = gregorian_to_jalali(row["month"].year, row["month"].month, 1)
        monthly_labels.append(f"{jy}/{jm:02d}")
        monthly_values.append(int(row["total"]))

    method_breakdown = (
        paid_fees.values("payment_method").annotate(total=Sum("amount"), count=Count("id")).order_by("-total")
    )
    method_labels = [dict(MembershipFee._meta.get_field("payment_method").choices).get(row["payment_method"], row[
        "payment_method"] or "نامشخص") for row in method_breakdown]
    method_values = [int(row["total"]) for row in method_breakdown]

    county_breakdown = (
        paid_fees.exclude(member__user__employment_assignments__isnull=True)
        .values("member__user__employment_assignments__health_house__center__network__county__name")
        .annotate(total=Sum("amount"))
        .order_by("-total")[:10]
    )
    county_labels = [
        row["member__user__employment_assignments__health_house__center__network__county__name"] or "نامشخص" for row in
        county_breakdown]
    county_values = [int(row["total"]) for row in county_breakdown]

    context = {
        "filter_form": filter_form,
        "summary": summary,
        "chart_data": json.dumps({
            "monthly_labels": monthly_labels,
            "monthly_values": monthly_values,
            "method_labels": method_labels,
            "method_values": method_values,
            "status_labels": ["پرداخت‌شده", "پرداخت‌نشده"],
            "status_values": [summary["total_paid_count"], summary["total_unpaid_count"]],
            "county_labels": county_labels,
            "county_values": county_values,
        }),
    }
    return render(request, "members/treasurer_report.html", context)

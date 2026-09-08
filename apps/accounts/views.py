from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from .bale_services import send_password_reset_code, verify_reset_code
from .forms import BaleResetRequestForm, BaleResetVerifyForm

User = get_user_model()


def bale_reset_request_view(request):
    if request.method == "POST":
        form = BaleResetRequestForm(request.POST)
        if form.is_valid():
            user = User.objects.filter(username=form.cleaned_data["national_code"]).first()
            if user and user.bale_chat_id:
                send_password_reset_code(user)
                request.session["bale_reset_user_id"] = user.pk
                return redirect("accounts:bale_reset_verify")
            form.add_error(None, "کاربری با این کد ملی و حساب بله متصل‌شده یافت نشد.")
    else:
        form = BaleResetRequestForm()
    return render(request, "accounts/bale_reset_request.html", {"form": form})


def bale_reset_verify_view(request):
    user_id = request.session.get("bale_reset_user_id")
    if not user_id:
        return redirect("accounts:bale_reset_request")
    user = User.objects.filter(pk=user_id).first()

    if request.method == "POST":
        form = BaleResetVerifyForm(request.POST)
        if form.is_valid():
            if not verify_reset_code(user, form.cleaned_data["code"]):
                form.add_error("code", "کد وارد‌شده نامعتبر یا منقضی‌شده است.")
            else:
                try:
                    validate_password(form.cleaned_data["new_password1"], user)
                except ValidationError as exc:
                    form.add_error("new_password1", exc)
                else:
                    user.set_password(form.cleaned_data["new_password1"])
                    user.must_change_password = False
                    user.save()
                    del request.session["bale_reset_user_id"]
                    return redirect("login")
    else:
        form = BaleResetVerifyForm()
    return render(request, "accounts/bale_reset_verify.html", {"form": form})
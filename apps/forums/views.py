from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from apps.board.permissions import is_board_member

from . import selectors
from .choices import ReactionType
from .forms import ForumCommentForm, ForumCreateForm, ForumPostForm
from .models import Forum, ForumComment, ForumPost
from .permissions import can_moderate_forum, can_view_forum
from .services import add_comment, create_post, delete_comment, delete_post, toggle_reaction


@login_required
def forum_list_view(request):
    forums = selectors.forums_for_user(request.user)
    unread_counts = selectors.get_unread_counts(request.user, forums)

    member_documents_pending = False
    if not (request.user.is_staff or request.user.is_superuser):
        try:
            member = request.user.member_profile
            member_documents_pending = member.documents_verified_at is None
        except Exception:
            pass

    return render(request, "forums/list.html", {
        "forums": forums, "unread_counts": unread_counts,
        "member_documents_pending": member_documents_pending,
    })


@login_required
def forum_detail_view(request, pk):
    from .models import ForumLastSeen

    forum = get_object_or_404(Forum, pk=pk)
    if not can_view_forum(request.user, forum):
        raise PermissionDenied("شما به این فروم دسترسی ندارید.")
    posts = forum.posts.filter(is_deleted=False).select_related("author")

    ForumLastSeen.objects.update_or_create(user=request.user, forum=forum, defaults={})

    return render(request, "forums/detail.html", {
        "forum": forum, "posts": posts, "can_moderate": can_moderate_forum(request.user, forum),
    })


@login_required
def post_create_view(request, forum_pk):
    forum = get_object_or_404(Forum, pk=forum_pk)
    if not can_view_forum(request.user, forum):
        raise PermissionDenied("شما به این فروم دسترسی ندارید.")

    if request.method == "POST":
        form = ForumPostForm(request.POST)
        if form.is_valid():
            post = create_post(forum=forum, author=request.user, **form.cleaned_data)
            return redirect("forums:post_detail", pk=post.pk)
    else:
        form = ForumPostForm()
    return render(request, "forums/post_form.html", {"form": form, "forum": forum})


@login_required
def post_detail_view(request, pk):
    post = get_object_or_404(ForumPost, pk=pk, is_deleted=False)
    if not can_view_forum(request.user, post.forum):
        raise PermissionDenied("شما به این فروم دسترسی ندارید.")

    if request.method == "POST":
        form = ForumCommentForm(request.POST)
        if form.is_valid():
            parent_id = request.POST.get("parent_id") or None
            parent_comment = None
            if parent_id:
                parent_comment = get_object_or_404(ForumComment, pk=parent_id, post=post)
                if parent_comment.parent_id:
                    parent_comment = parent_comment.parent
            add_comment(
                post=post, author=request.user, content=form.cleaned_data["content"], parent=parent_comment,
            )
            return redirect("forums:post_detail", pk=post.pk)
    else:
        form = ForumCommentForm()

    top_level_comments = post.comments.filter(is_deleted=False, parent__isnull=True).select_related(
        "author"
    ).prefetch_related("replies__author")

    post_reactions = selectors.get_reaction_summary(request.user, post)

    return render(request, "forums/post_detail.html", {
        "post": post, "comments": top_level_comments, "comment_form": form,
        "can_moderate": can_moderate_forum(request.user, post.forum),
        "post_reactions": post_reactions,
    })


@login_required
def reaction_toggle_view(request, target_type, pk):
    model_map = {"post": ForumPost, "comment": ForumComment}
    model = model_map.get(target_type)
    if model is None:
        raise PermissionDenied("نوع هدف نامعتبر است.")
    target = get_object_or_404(model, pk=pk)

    reaction_type = request.POST.get("reaction_type")
    if reaction_type not in (ReactionType.LIKE, ReactionType.DISLIKE):
        raise PermissionDenied("نوع واکنش نامعتبر است.")

    toggle_reaction(user=request.user, target=target, reaction_type=reaction_type)
    if target_type == "post":
        return redirect("forums:post_detail", pk=target.pk)
    return redirect("forums:post_detail", pk=target.post_id)


@login_required
def post_delete_view(request, pk):
    post = get_object_or_404(ForumPost, pk=pk)
    if request.method == "POST":
        try:
            delete_post(post=post, actor=request.user)
            messages.success(request, "پست حذف شد.")
        except PermissionDenied as exc:
            messages.error(request, str(exc))
    return redirect("forums:detail", pk=post.forum_id)


@login_required
def comment_delete_view(request, pk):
    comment = get_object_or_404(ForumComment, pk=pk)
    post_pk = comment.post_id
    if request.method == "POST":
        try:
            delete_comment(comment=comment, actor=request.user)
            messages.success(request, "کامنت حذف شد.")
        except PermissionDenied as exc:
            messages.error(request, str(exc))
    return redirect("forums:post_detail", pk=post_pk)


# --- مدیریت خود Forumها (ایجاد/CRUD) ---

@login_required
def forum_management_list_view(request):
    from apps.authorization.services import Authorization

    if not Authorization._has_delegated_full_access(request.user) and not request.user.is_superuser:
        raise PermissionDenied("شما مجوز مدیریت فروم‌ها را ندارید.")
    forums = Forum.objects.select_related("scope").all()
    return render(request, "forums/management_list.html", {"forums": forums})


@login_required
def forum_management_create_view(request):
    if not (request.user.is_staff or request.user.is_superuser or is_board_member(request.user)):
        raise PermissionDenied("شما مجوز ایجاد فروم را ندارید.")

    if request.method == "POST":
        form = ForumCreateForm(request.POST, editor=request.user)
        if form.is_valid():
            from apps.organization.scope_sync import ensure_access_scope_for

            level = form.cleaned_data["level"]
            instance = form.get_target_instance()
            scope = ensure_access_scope_for(level, instance)

            forum, created = Forum.objects.get_or_create(
                scope=scope,
                defaults={
                    "name": form.cleaned_data["name"] or f"فروم {dict(form.LEVEL_CHOICES)[level]} {instance.name}",
                    "description": form.cleaned_data["description"],
                },
            )
            if not created:
                messages.info(request, "فرومی برای این محدوده از قبل وجود داشت — همان فروم نمایش داده می‌شود.")
            else:
                messages.success(request, "فروم ایجاد شد.")
            return redirect("forums:management_list")
    else:
        form = ForumCreateForm(editor=request.user)
    return render(request, "forums/management_form.html", {"form": form})


@login_required
def forum_coverage_view(request):
    if not (request.user.is_staff or request.user.is_superuser or is_board_member(request.user)):
        raise PermissionDenied("شما مجوز مشاهده‌ی این صفحه را ندارید.")

    from apps.authorization.choices import AccessScopeType
    from apps.authorization.models import AccessScope
    from apps.authorization.scope_helpers import get_accessible_province_ids
    from apps.organization.models import County, HealthCenter, HealthNetwork, Province

    def scope_for_node(level, instance):
        field_map = {"province": "province", "county": "county", "network": "network", "center": "center"}
        scope_type_map = {
            "province": AccessScopeType.PROVINCE, "county": AccessScopeType.COUNTY,
            "network": AccessScopeType.NETWORK, "center": AccessScopeType.CENTER,
        }
        return AccessScope.objects.filter(
            scope_type=scope_type_map[level], **{field_map[level]: instance}
        ).first()

    def forum_status_for(level, instance):
        scope = scope_for_node(level, instance)
        if scope is None:
            return "no_scope", None
        forum = Forum.objects.filter(scope=scope).first()
        if forum is None:
            return "missing", None
        return ("active" if forum.is_active else "inactive"), forum.pk

    accessible_province_ids = get_accessible_province_ids(request.user)
    provinces = Province.objects.filter(is_active=True).order_by("name")
    if accessible_province_ids is not None:
        provinces = provinces.filter(pk__in=accessible_province_ids)

    rows = []
    for province in provinces:
        status, forum_pk = forum_status_for("province", province)
        rows.append({
            "level": "province", "name": province.name, "pk": province.pk,
            "status": status, "forum_pk": forum_pk, "depth": 0,
        })
        for county in County.objects.filter(province=province, is_active=True).order_by("name"):
            status, forum_pk = forum_status_for("county", county)
            rows.append({
                "level": "county", "name": county.name, "pk": county.pk,
                "status": status, "forum_pk": forum_pk, "depth": 1,
            })
            for network in HealthNetwork.objects.filter(county=county, is_active=True).order_by("name"):
                status, forum_pk = forum_status_for("network", network)
                rows.append({
                    "level": "network", "name": network.name, "pk": network.pk,
                    "status": status, "forum_pk": forum_pk, "depth": 2,
                })
                for center in HealthCenter.objects.filter(network=network, is_active=True).order_by("name"):
                    status, forum_pk = forum_status_for("center", center)
                    rows.append({
                        "level": "center", "name": center.name, "pk": center.pk,
                        "status": status, "forum_pk": forum_pk, "depth": 3,
                    })

    return render(request, "forums/coverage.html", {"rows": rows})


@login_required
def forum_quick_create_view(request, level, pk):
    """
    ایجاد فوری فروم برای یک گره‌ی مشخص، مستقیم از صفحه‌ی «وضعیت پوشش»
    — بدون فرم، بدون انتخاب مجدد؛ نام و محدوده خودکار از خود گره
    گرفته می‌شوند.
    """
    if not (request.user.is_staff or request.user.is_superuser or is_board_member(request.user)):
        raise PermissionDenied("شما مجوز ایجاد فروم را ندارید.")
    if request.method != "POST":
        raise PermissionDenied("این عملیات فقط از طریق POST مجاز است.")

    from apps.authorization.scope_helpers import get_accessible_province_ids
    from apps.organization.models import County, HealthCenter, HealthNetwork, Province
    from apps.organization.scope_sync import ensure_access_scope_for

    level_model_map = {
        "province": Province, "county": County, "network": HealthNetwork, "center": HealthCenter,
    }
    level_label_map = {
        "province": "استان", "county": "شهرستان", "network": "شبکه بهداشت و درمان", "center": "مرکز خدمات جامع سلامت",
    }
    model = level_model_map.get(level)
    if model is None:
        raise PermissionDenied("سطح نامعتبر است.")

    instance = get_object_or_404(model, pk=pk)

    # بررسی Scope مجاز کاربر (جلوگیری از IDOR: ساخت فروم برای استان دیگر)
    accessible_province_ids = get_accessible_province_ids(request.user)
    if accessible_province_ids is not None:
        from apps.organization.management_views import _get_province_id_of
        if _get_province_id_of(level, instance) not in accessible_province_ids:
            raise PermissionDenied("شما مجوز ایجاد فروم برای این محدوده را ندارید.")

    scope = ensure_access_scope_for(level, instance)
    forum, created = Forum.objects.get_or_create(
        scope=scope, defaults={"name": f"فروم {level_label_map[level]} {instance.name}"},
    )
    if created:
        messages.success(request, f"فروم «{forum.name}» با موفقیت ایجاد شد.")
    else:
        messages.info(request, "فرومی برای این محدوده از قبل وجود داشت.")

    return redirect("forums:coverage")


@login_required
def forum_toggle_active_view(request, pk):
    forum = get_object_or_404(Forum, pk=pk)
    if not (request.user.is_staff or request.user.is_superuser or is_board_member(request.user)):
        raise PermissionDenied("شما مجوز تغییر وضعیت فروم را ندارید.")
    if request.method != "POST":
        raise PermissionDenied("این عملیات فقط از طریق POST مجاز است.")

    forum.is_active = not forum.is_active
    forum.save(update_fields=["is_active"])
    state = "فعال" if forum.is_active else "غیرفعال"
    messages.success(request, f"فروم «{forum.name}» {state} شد.")
    return redirect("forums:coverage")

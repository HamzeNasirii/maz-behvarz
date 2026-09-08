from django.db import connection
from django.http import JsonResponse
from django.shortcuts import render


def health_check_view(request):
    db_ok = True
    try:
        connection.ensure_connection()
    except Exception:
        db_ok = False

    status = "ok" if db_ok else "degraded"
    return JsonResponse({"status": status, "database": db_ok})


def custom_400(request, exception=None):
    return render(request, "errors/400.html", status=400)


def custom_403(request, exception=None):
    return render(request, "errors/403.html", status=403)


def custom_404(request, exception=None):
    return render(request, "errors/404.html", status=404)


def custom_500(request):
    return render(request, "errors/500.html", status=500)
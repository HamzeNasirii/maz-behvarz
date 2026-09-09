from django.urls import path

from . import views

app_name = "public_content"

urlpatterns = [
    path("news/", views.news_list_view, name="news_list"),
    path("news/<slug:slug>/", views.news_detail_view, name="news_detail"),

    path("announcements/", views.announcement_list_view, name="announcement_list"),
    path("announcements/<slug:slug>/", views.announcement_detail_view, name="announcement_detail"),

    path("events/", views.event_list_view, name="event_list"),
    path("events/<slug:slug>/", views.event_detail_view, name="event_detail"),
    path("board/", views.board_view, name="board"),
    path("committees/", views.committees_view, name="committees"),
    path("documents/", views.document_list_view, name="document_list"),

    path("regulations/", views.regulation_list_view, name="regulation_list"),
    path("regulations/<slug:slug>/", views.regulation_detail_view, name="regulation_detail"),

    path("representatives/", views.representatives_view, name="representatives"),
    path("faq/", views.faq_view, name="faq"),
    path("news/id/<int:pk>/", views.news_short_redirect_view, name="news_short_redirect"),
    path("contact-us/", views.contact_view, name="contact"),
    path("search/", views.search_view, name="search"),
]

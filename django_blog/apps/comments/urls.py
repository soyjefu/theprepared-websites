from django.urls import path

from . import views

urlpatterns = [
    path("submit/", views.submit, name="submit"),
    path("<int:comment_id>/delete/", views.delete_own, name="delete"),
    path("<int:comment_id>/update/", views.update_own, name="update"),
    path("like/<int:page_id>/", views.toggle_like, name="toggle_like"),
    path("nickname/", views.change_nickname, name="change_nickname"),
]

from django.urls import path

from . import views

app_name = "posts"
urlpatterns = [
    path("", views.index, name="index"),
    # Generic Views
    path("feed", views.user_feed, name="user_feed"),
    path("post/create", views.PostCreate.as_view(), name="post_create"),
    path("categories", views.CategoryList.as_view(), name="category_list"),
    path("users", views.UserList.as_view(), name="user_list"),
    # Sub
    path("category/create", views.CategoryCreate.as_view(), name="category_create"),
    path("r/<str:category_slug>/", views.category_detail, name="category_detail"),
    path("r/<str:category_slug>/subscribe", views.subscribe, name="subscribe"),
    path("r/<str:category_slug>/unsubscribe", views.unsubscribe, name="unsubscribe"),
    path("r/random", views.random, name="random"),
    path("u/<str:username>/", views.user, name="user"),
    path("<str:post_id>/save", views.save_post, name="save_post"),
    path("<str:post_id>/unsave", views.unsave_post, name="unsave_post"),
    path("<str:post_id>/upvote", views.upvote_post, name="upvote_post"),
    path("<str:post_id>/downvote", views.downvote_post, name="downvote_post"),
    path("<str:post_id>/comment", views.comment, name="comment"),
    path("<str:post_id>/<str:post_slug>/", views.post_detail, name="post_detail"),
]

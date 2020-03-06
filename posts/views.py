from django import forms
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import (
    Case,
    Count,
    Exists,
    F,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView

from posts.models import Category, Comment, Favourite, Post, Subscription, Vote


class UserList(ListView):
    model = User
    paginate_by = 50
    template_name = "posts/user_list.html"
    queryset = User.objects.annotate(
        post_karma=Coalesce(Sum("posts__votes__choice"), Value(0)),
        comment_karma=Coalesce(Sum("comments__votes__choice"), Value(0)),
        karma=F("post_karma") + F("comment_karma"),
    ).order_by("-karma", "-date_joined", "username")


class CategoryList(ListView):
    model = Category


class CategoryCreate(CreateView):
    model = Category
    fields = ("name", "description", "avatar")


class PostCreate(CreateView):
    model = Post
    fields = ("title", "body", "link", "photo", "category")

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.user = self.request.user
        return super().form_valid(form)


@login_required
def user_feed(request):

    posts = (
        Post.ranked.select_related("user", "category")
        .filter(category__in=request.user.subscriptions.values("category__id"))
        .order_by("-score", "-created_on")
    )

    user_votes = Vote.objects.filter(user=request.user)
    user_favs = Favourite.objects.filter(user=request.user, object_id=OuterRef("pk"))
    posts = posts.annotate(
        has_saved=Exists(user_favs, distinct=True),
        upvoted=Exists(
            user_votes.filter(object_id=OuterRef("pk"), choice=Vote.Choice.UP),
            distinct=True,
        ),
        downvoted=Exists(
            user_votes.filter(object_id=OuterRef("pk"), choice=Vote.Choice.DOWN),
            distinct=True,
        ),
    )

    paginator = Paginator(posts, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(
        request,
        "posts/index.html",
        {"page_obj": page_obj, "form": AuthenticationForm,},
    )


def index(request):
    # Equivalent to /r/all
    posts = Post.ranked.select_related("user", "category")

    if request.user.is_authenticated:
        # Filter down all the votes for a given user

        # [TODO] Annotate with upvote/downvote in order to display in template
        user_votes = Vote.objects.filter(user=request.user)
        user_favs = Favourite.objects.filter(
            user=request.user, object_id=OuterRef("pk")
        )
        posts = posts.annotate(
            has_saved=Exists(user_favs, distinct=True),
            upvoted=Exists(
                user_votes.filter(object_id=OuterRef("pk"), choice=Vote.Choice.UP),
                distinct=True,
            ),
            downvoted=Exists(
                user_votes.filter(object_id=OuterRef("pk"), choice=Vote.Choice.DOWN),
                distinct=True,
            ),
        )

    posts = posts.order_by("-score", "-created_on")

    paginator = Paginator(posts, 50)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "posts/index.html", {"page_obj": page_obj},)


def user_detail(request, username):

    posts_query = Post.ranked.select_related("category").order_by(
        "-score", "created_on"
    )

    if request.user.is_authenticated:
        # Filter down all the votes for a given user
        user_votes = Vote.objects.filter(user=request.user, object_id=OuterRef("pk"))
        user_favs = Favourite.objects.filter(
            user=request.user, object_id=OuterRef("pk")
        )
        posts_query = posts_query.annotate(
            has_saved=Exists(user_favs, distinct=True),
            upvoted=Exists(
                user_votes.filter(object_id=OuterRef("pk"), choice=Vote.Choice.UP),
                distinct=True,
            ),
            downvoted=Exists(
                user_votes.filter(object_id=OuterRef("pk"), choice=Vote.Choice.DOWN),
                distinct=True,
            ),
        )

    # Pre-fetch a user and all their corresponding posts
    user_query = User.objects.prefetch_related(Prefetch("posts", queryset=posts_query))

    # Annotate the user with the sum of their total post/comment Karma
    user_query = user_query.annotate(
        post_karma=Coalesce(Sum("posts__votes__choice"), Value(0)),
        comment_karma=Coalesce(Sum("comments__votes__choice"), Value(0)),
        karma=F("post_karma") + F("comment_karma"),
    )

    user = get_object_or_404(user_query, username=username,)

    paginator = Paginator(user.posts.all(), 50)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(request, "posts/user.html", {"user": user, "page_obj": page_obj},)


def random(request):
    category = Category.objects.order_by("?").first()
    if category is None:
        raise Http404("No categories exist")
    return redirect(category)


@login_required
def unsubscribe(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    Subscription.objects.get(user=request.user, category=category).delete()
    return redirect(category)


@login_required
def subscribe(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    Subscription.objects.create(user=request.user, category=category).save()
    return redirect(category)


def category_detail(request, category_slug):

    posts_query = Post.ranked.select_related("user").order_by("-score", "created_on")

    # Default the category query is all the category objects
    category_query = Category.objects.annotate(total_subscribers=Count("subscribers"))

    if request.user.is_authenticated:
        # Determine whether the user is subscribed
        has_subscription = Subscription.objects.filter(
            user=request.user, category__slug=category_slug
        )

        category_query = category_query.annotate(subscribed=Exists(has_subscription))

        # Determine what posts the uer has favourited/voted on
        user_votes = Vote.objects.filter(user=request.user, object_id=OuterRef("pk"))
        user_favs = Favourite.objects.filter(
            user=request.user, object_id=OuterRef("pk")
        )
        posts_query = posts_query.annotate(
            has_saved=Exists(user_favs, distinct=True),
            upvoted=Exists(
                user_votes.filter(object_id=OuterRef("pk"), choice=Vote.Choice.UP),
                distinct=True,
            ),
            downvoted=Exists(
                user_votes.filter(object_id=OuterRef("pk"), choice=Vote.Choice.DOWN),
                distinct=True,
            ),
        )

    category_query = category_query.prefetch_related(
        "subscribers", Prefetch("posts", posts_query)
    )

    category = get_object_or_404(category_query, slug=category_slug)

    paginator = Paginator(category.posts.all(), 50)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request, "posts/category.html", {"category": category, "page_obj": page_obj,},
    )


@login_required
def save_post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    f = Favourite(content_object=post, user=request.user)
    f.save()
    # [TODO] Check if this is okay
    return redirect(request.GET.get("next"))


@login_required
def unsave_post(request, post_id):
    # [TODO] This is two queries, wen can probably do it in one by looking up
    # the corresponding Favourite for the post/user id combination
    post = get_object_or_404(Post, pk=post_id)
    post.favourites.filter(user=request.user).delete()
    return redirect(request.GET.get("next"))


@login_required
@require_POST
def comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    reply = Comment(content=request.POST["content"], post=post, user=request.user)
    reply.save()
    post.comments.add(reply)
    post.save()
    return redirect(post)


def resolve_vote(request, choice, post_id):
    post = get_object_or_404(Post, pk=post_id)
    Vote.objects.update_or_create(
        object_id=post_id,
        user=request.user,
        defaults={
            "choice": choice,
            "user": request.user,
            "object_id": post_id,
            "content_object": post,
        },
    )
    return redirect(request.GET.get("next"))


@login_required
def upvote_post(request, post_id):
    return resolve_vote(request, Vote.Choice.UP, post_id)


@login_required
def downvote_post(request, post_id):
    return resolve_vote(request, Vote.Choice.DOWN, post_id)


def resolve_comment_vote(request, choice, comment_id):
    comment = get_object_or_404(Comment, pk=comment_id)
    Vote.objects.update_or_create(
        object_id=comment_id,
        user=request.user,
        defaults={
            "choice": choice,
            "user": request.user,
            "object_id": comment_id,
            "content_object": comment,
        },
    )
    return redirect(request.GET.get("next"))


@login_required
def upvote_comment(request, comment_id):
    return resolve_comment_vote(request, Vote.Choice.UP, comment_id)


@login_required
def downvote_comment(request, comment_id):
    return resolve_comment_vote(request, Vote.Choice.DOWN, comment_id)


def post_detail(request, post_id, post_slug):

    post_query = Post.ranked.select_related("category", "user").prefetch_related(
        Prefetch(
            "comments", Comment.objects.select_related("user").select_related("reply")
        )
    )

    if request.user.is_authenticated:
        user_votes = Vote.objects.filter(user=request.user, object_id=post_id)
        user_favs = Favourite.objects.filter(user=request.user, object_id=post_id)
        post_query = post_query.annotate(
            has_saved=Exists(user_favs, distinct=True),
            upvoted=Exists(user_votes.filter(choice=Vote.Choice.UP), distinct=True,),
            downvoted=Exists(
                user_votes.filter(choice=Vote.Choice.DOWN), distinct=True,
            ),
        )

    post = get_object_or_404(post_query, id=post_id)

    return render(request, "posts/post_detail.html", {"post": post})

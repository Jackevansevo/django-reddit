import uuid

from django.db.models.functions import Coalesce
from django.db.models import Sum, Value, Count
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import IntegrityError, models
from django.utils.text import slugify


def get_sentinel_user():
    return get_user_model().objects.get_or_create(username="deleted")[0]


class TimeStamp(models.Model):

    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Comment(TimeStamp):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    content = models.TextField(max_length=2000)

    post = models.ForeignKey("Post", on_delete=models.CASCADE, related_name="comments")

    favourites = GenericRelation("Favourite", related_name="favourites")

    votes = GenericRelation("Vote", related_name="votes")

    # Top level comments are those that aren't replies to other comments
    reply = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="replies"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET(get_sentinel_user),
        related_name="comments",
    )

    def __str__(self) -> str:
        return self.content


# First, define the Manager subclass.
class RankedManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(
                total_comments=Coalesce(Count("comments", distinct=True), Value(0)),
                score=Coalesce(Sum("votes__choice", distinct=True), Value(0)),
            )
        )


class Post(TimeStamp):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    slug = models.SlugField(editable=False)

    # The content type of the post
    body = models.TextField(max_length=2000, blank=True)
    link = models.URLField(blank=True)
    photo = models.ImageField(blank=True)

    votes = GenericRelation("Vote", related_query_name="post")
    favourites = GenericRelation("Favourite", related_query_name="post")

    category = models.ForeignKey(
        "Category", on_delete=models.CASCADE, related_name="posts"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET(get_sentinel_user),
        related_name="posts",
    )

    objects = models.Manager()
    ranked = RankedManager()

    class Meta:
        ordering = ("-created_on",)

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("posts:post_detail", args=[str(self.id), self.slug])

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        if not self.link:
            self.link = self.get_absolute_url()
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return self.title


class Category(TimeStamp):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(editable=False)
    description = models.CharField(max_length=200)
    avatar = models.ImageField(blank=True)

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("posts:category_detail", args=[self.slug])

    def save(self, *args, **kwargs):
        self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "categories"

    def __str__(self) -> str:
        return self.name


class Favourite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET(get_sentinel_user),
        related_name="favourites",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey()

    def __str__(self) -> str:
        return str(self.object_id)


class Subscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET(get_sentinel_user),
        related_name="subscriptions",
    )
    category = models.ForeignKey(
        "Category", on_delete=models.CASCADE, related_name="subscribers"
    )

    class Meta:
        unique_together = ["user", "category"]

    def __str__(self):
        return f"({self.user} {self.category})"


class Message(TimeStamp):

    title = models.CharField(max_length=200)
    content = models.TextField(max_length=2000)

    # Top level comments are those that aren't replies to other comments
    reply = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="replies"
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET(get_sentinel_user),
        related_name="messages",
    )

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET(get_sentinel_user),
    )


class Vote(TimeStamp):
    class Choice(models.IntegerChoices):
        UP = 1
        DOWN = -1

    choice = models.IntegerField(choices=Choice.choices)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET(get_sentinel_user),
        related_name="votes",
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.UUIDField()
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        unique_together = ["object_id", "user"]
        ordering = ("-created_on",)

    def __str__(self) -> str:
        return "Upvote" if self.choice == 1 else "Downvote"

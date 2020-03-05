from django.contrib import admin

from posts.models import Category, Comment, Favourite, Post, Subscription, Vote


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "category")


@admin.register(Favourite)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = ("user", "content_object")


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("user", "content_object", "choice")


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("content", "post", "reply", "user")


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    exclude = ("slug",)
    search_fields = ["name"]


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "user",
        "created_on",
    )
    search_fields = ("title", "user__username")
    list_filter = ("category",)
    readonly_fields = ("user", "slug", "id")
    exclude = ("user", "id")

    def get_readonly_fields(self, request, obj=None):
        # If object is being viewed, show user as readonly
        if obj is not None:
            return self.readonly_fields
        return ()

    def get_exclude(self, request, obj=None):
        # If post is being created don't exclude the user field
        if obj is not None:
            return ()
        return self.exclude

    def save_model(self, request, obj, form, change):
        obj.user = request.user
        super().save_model(request, obj, form, change)

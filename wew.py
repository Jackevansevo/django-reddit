comment_query = Comment.objects.annotate(num_replies=Count("replies")).order_by(
    "created_on"
)
post = Post.objects.prefetch_related(Prefetch("comments", comment_query)).get(
    id="9afa43b0-3d65-420e-b53b-3c5e961f31de"
)

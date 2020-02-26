import argparse
import json

from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from posts.models import Category, Post


class Command(BaseCommand):
    help = "Loads scraped data into the database"

    def add_arguments(self, parser):
        parser.add_argument("infile", nargs="?", type=argparse.FileType("r"))

    def handle(self, *args, **options):
        posts = json.load(options["infile"])
        users = {post["username"] for post in posts}
        categories = {post["subreddit"] for post in posts}

        User.objects.bulk_create([User(username=name) for name in users])
        Category.objects.bulk_create(
            [Category(name=name, slug=slugify(name)) for name in categories]
        )

        Post.objects.bulk_create(
            [
                Post(
                    title=post["title"],
                    category=Category.objects.get(name=post["subreddit"]),
                    link=post.get("href"),
                    user=User.objects.get(username=post["username"]),
                    slug=slugify(post["title"]),
                )
                for post in posts
            ]
        )

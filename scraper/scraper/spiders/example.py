import scrapy
from posixpath import basename, dirname
from urllib.parse import urlparse
from functools import partial


class PostSpider(scrapy.Spider):
    name = "subreddits"

    def start_requests(self):
        subreddits = ["programming", "askreddit", "linux"]
        for subreddit in subreddits:
            parser = partial(self.parse, subreddit=subreddit)
            yield scrapy.Request(
                url=f"http://old.reddit.com/r/{subreddit}/", callback=parser
            )

    def parse(self, response, subreddit=None):
        posts = response.xpath('//div[@id="siteTable"]/div[contains(@class, "thing")]')
        # [TODO] Recursively crawl the subpage of each post
        for post in posts:
            info = post.xpath('div[@class="entry unvoted"]/div/p/a')
            anchor, user = info
            yield {
                "title": anchor.xpath("text()").get(),
                "href": anchor.xpath("@href").get(),
                "username": user.xpath("text()").get(),
                "subreddit": subreddit,
            }

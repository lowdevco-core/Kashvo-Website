from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from .models import Post


class StaticSitemap(Sitemap):
    changefreq = "weekly"
    protocol = "https"

    def items(self):
        return ["home", "about", "pricing", "why", "blog"]

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return 1.0 if item == "home" else 0.8


class PostSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.6
    protocol = "https"

    def items(self):
        return Post.published.filter(noindex=False)

    def lastmod(self, obj):
        return obj.updated_at

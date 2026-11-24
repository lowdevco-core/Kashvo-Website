"""Load the blog articles in apps/cms/articles/ into the database, with a generated cover for each.

    python manage.py load_articles            # add or update articles by slug
    python manage.py load_articles --replace  # delete every other post first
"""
import json
import re
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify
from lucide import _render_icon

from apps.cms.models import Category, Post, Tag

ARTICLES = Path(__file__).resolve().parents[2] / "articles"
PHOTOS = settings.BASE_DIR / "static" / "img" / "blog"  # Unsplash photos, named <slug>.jpg
FRONT = re.compile(r"\A<!--(.*?)-->\s*", re.S)


def cover_svg(icon, seed):
    """1200x630 brand cover: teal gradient, dot grid, a large Lucide icon in a white tile."""
    glyph = _render_icon(icon, 160, **{"stroke": "#0f766e", "stroke-width": "1.5", "x": "520", "y": "235"})
    hue = ["#0f766e", "#115e59", "#0d9488", "#134e4a"][seed % 4]
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" width="1200" height="630">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{hue}"/><stop offset="1" stop-color="#0b3b38"/></linearGradient>
<pattern id="d" width="32" height="32" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="2" fill="#fff" opacity=".09"/></pattern></defs>
<rect width="1200" height="630" fill="url(#g)"/><rect width="1200" height="630" fill="url(#d)"/>
<circle cx="{180 + seed * 47 % 300}" cy="{520 - seed * 31 % 200}" r="220" fill="#fff" opacity=".05"/>
<circle cx="{1020 - seed * 29 % 260}" cy="{110 + seed * 17 % 160}" r="150" fill="#fde68a" opacity=".12"/>
<rect x="460" y="175" width="280" height="280" rx="64" fill="#fff"/>
<rect x="460" y="175" width="280" height="280" rx="64" fill="none" stroke="#fde68a" stroke-width="6" opacity=".9"/>
{glyph}
</svg>'''


class Command(BaseCommand):
    help = "Load blog articles from apps/cms/articles/*.html"

    def add_arguments(self, parser):
        parser.add_argument("--replace", action="store_true", help="Delete posts that are not in apps/cms/articles/")

    def handle(self, replace, **opts):
        author = User.objects.filter(is_superuser=True).order_by("pk").first()
        files = sorted(ARTICLES.glob("*.html"))
        now = timezone.now()
        slugs = []
        for i, path in enumerate(files):
            text = path.read_text(encoding="utf-8")
            m = FRONT.match(text)
            if not m:
                raise SystemExit(f"{path.name}: missing <!--{{json}}--> header")
            meta, body = json.loads(m.group(1)), text[m.end():].strip()
            cat, _ = Category.objects.get_or_create(slug=slugify(meta["category"]), defaults={"name": meta["category"]})
            post = Post.objects.filter(slug=meta["slug"]).first() or Post(slug=meta["slug"])
            post.title, post.body, post.excerpt = meta["title"], body, meta["excerpt"]
            post.category, post.status, post.author = cat, Post.PUBLISHED, post.author or author
            post.meta_title, post.meta_description = meta.get("meta_title", ""), meta["excerpt"][:170]
            post.meta_keywords = ", ".join(meta["keywords"])
            post.cover_alt = meta["cover_alt"]
            post.featured = i == len(files) - 1
            # newest file first in the blog: space articles three days apart going back from today
            post.published_at = now - timedelta(days=3 * (len(files) - 1 - i))
            if post.cover:
                post.cover.delete(save=False)
            photo = PHOTOS / f"{meta['slug']}.jpg"
            if photo.exists():
                post.cover.save(photo.name, ContentFile(photo.read_bytes()), save=False)
            else:
                post.cover.save(f"{meta['slug']}.svg", ContentFile(cover_svg(meta["icon"], i).encode()), save=False)
            post.save()
            post.tags.set([Tag.objects.get_or_create(slug=slugify(t), defaults={"name": t})[0] for t in meta["tags"]])
            slugs.append(post.slug)
        if replace:
            gone, _ = Post.objects.exclude(slug__in=slugs).delete()
            self.stdout.write(f"Removed {gone} old rows.")
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(slugs)} articles."))

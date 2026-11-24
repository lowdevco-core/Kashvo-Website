import re
from pathlib import Path
from urllib.parse import unquote, urlparse

from django.conf import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver


def delete_post_media(instance):
    """Delete cover, OG image, and embedded body images from media/ when a blog post is deleted."""
    # 1. Delete cover image if not used by any other post
    if instance.cover:
        try:
            name = instance.cover.name
            if name:
                from .models import Post
                if not Post.objects.exclude(pk=instance.pk).filter(cover=name).exists():
                    instance.cover.storage.delete(name)
        except Exception:
            pass

    # 2. Delete OG image if not used by any other post or page SEO
    if instance.og_image:
        try:
            name = instance.og_image.name
            if name:
                from .models import PageSeo, Post
                in_posts = Post.objects.exclude(pk=instance.pk).filter(og_image=name).exists()
                in_pages = PageSeo.objects.filter(og_image=name).exists()
                if not in_posts and not in_pages:
                    instance.og_image.storage.delete(name)
        except Exception:
            pass

    # 3. Delete all images embedded in the post body (e.g. from CKEditor)
    if instance.body:
        try:
            media_url = settings.MEDIA_URL
            if not media_url.startswith("/"):
                media_url = "/" + media_url
            media_root = Path(settings.MEDIA_ROOT).resolve()

            img_sources = set(re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', instance.body, re.IGNORECASE))
            for src in img_sources:
                parsed_path = unquote(urlparse(src).path)
                if parsed_path.startswith(media_url):
                    rel = parsed_path[len(media_url):].lstrip("/\\")
                    target = (media_root / rel).resolve()
                    if target.is_relative_to(media_root) and target.is_file():
                        from .models import Post
                        other = Post.objects.exclude(pk=instance.pk).filter(body__contains=src).exists()
                        if not other:
                            target.unlink(missing_ok=True)
        except Exception:
            pass


@receiver(post_delete, sender="cms.Post")
def on_post_delete(sender, instance, **kwargs):
    delete_post_media(instance)

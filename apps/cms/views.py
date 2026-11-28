from pathlib import Path

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from .models import Category, PageSeo, Post, SlugRedirect


def page(template, key):
    def view(request):
        return render(request, template, {"seo": PageSeo.objects.filter(page=key).first(), "page_key": key})
    view.__name__ = key
    return view


def blog_list(request, slug=None):
    posts = Post.published.select_related("category")
    category = None
    if slug:
        category = get_object_or_404(Category, slug=slug)
        posts = posts.filter(category=category)
    q = request.GET.get("q", "").strip()
    if q:
        posts = posts.filter(Q(title__icontains=q) | Q(excerpt__icontains=q) | Q(body__icontains=q))
    page_num = request.GET.get("page")
    featured = None if (q or slug or (page_num and str(page_num) != "1")) else Post.published.filter(featured=True).first()
    if featured:
        posts = posts.exclude(pk=featured.pk)
    page_obj = Paginator(posts, 9).get_page(page_num)
    return render(request, "blog/list.html", {
        "page_obj": page_obj, "category": category, "q": q,
        "categories": Category.objects.filter(posts__status=Post.PUBLISHED).distinct(),
        "featured": featured,
        "seo": PageSeo.objects.filter(page="blog").first(), "page_key": "blog",
    })


def blog_detail(request, slug):
    post = Post.published.select_related("category", "author").prefetch_related("tags").filter(slug=slug).first()
    if not post:
        old = SlugRedirect.objects.select_related("post").filter(old_slug=slug).first()
        if old:
            return redirect(old.post, permanent=True)
        # staff can preview drafts
        if request.user.is_staff:
            post = get_object_or_404(Post, slug=slug)
        else:
            return render(request, "404.html", status=404)
    related = Post.published.filter(category=post.category).exclude(pk=post.pk)[:3] if post.category else []
    return render(request, "blog/detail.html", {"post": post, "seo": post, "related": related, "page_key": "blog"})


@require_GET
def robots(request):
    lines = ["User-agent: *", "Disallow: /admin/", "Disallow: /django-admin/", "Disallow: /ckeditor5/", f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}"]
    return HttpResponse("\n".join(lines) + "\n", content_type="text/plain")


def custom_404(request, exception=None):
    if request.path.startswith("/admin/") and request.user.is_authenticated and request.user.is_staff:
        from .panel import ctx
        return render(request, "panel/404.html", ctx(request, active="dashboard"), status=404)
    return render(request, "404.html", status=404)


def preview_404(request):
    return render(request, "404.html", status=404)


@require_GET
def download_desktop_app(request):
    """Serve the desktop app installer from app-upload/ without accepting any user-supplied path."""
    upload_dir = Path(getattr(settings, "APP_UPLOAD_DIR", Path(settings.BASE_DIR) / "app-upload")).resolve()
    if not upload_dir.is_dir():
        return render(request, "404.html", status=404)

    candidates = [
        p for p in upload_dir.iterdir()
        if not p.name.startswith(".")
        and not p.is_symlink()
        and p.is_file()
        and p.resolve().parent == upload_dir
    ]
    if not candidates:
        return render(request, "404.html", status=404)

    target = max(candidates, key=lambda p: p.stat().st_mtime)
    return FileResponse(target.open("rb"), as_attachment=True, filename=target.name)

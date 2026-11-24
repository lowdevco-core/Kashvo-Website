from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import Category, PageSeo, Post, SlugRedirect, Tag

admin.site.site_header = "Kashvo · Django admin"

SEO = ("SEO", {"fields": ("meta_title", "meta_description", "meta_keywords", "og_image", "noindex"), "classes": ("collapse",)})


class SlugRedirectInline(admin.TabularInline):
    model = SlugRedirect
    extra = 0
    verbose_name_plural = "Old URLs (301 redirect here)"


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "category", "featured", "published_at", "view_link")
    list_filter = ("status", "category", "featured", "tags")
    list_editable = ("status", "featured")
    search_fields = ("title", "slug", "body", "meta_keywords")
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ("category", "tags")
    date_hierarchy = "published_at"
    inlines = [SlugRedirectInline]
    actions = ["publish", "unpublish"]
    fieldsets = (
        (None, {"fields": ("title", "slug", "body")}),
        ("Card & cover", {"fields": ("excerpt", "cover", "cover_alt")}),
        ("Publishing", {"fields": ("status", "published_at", "featured", "category", "tags", "author")}),
        SEO,
    )

    def save_model(self, request, obj, form, change):
        obj.author = obj.author or request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Link")
    def view_link(self, obj):
        return format_html('<a href="{}" target="_blank">View ↗</a>', obj.get_absolute_url())

    @admin.action(description="Publish selected posts now")
    def publish(self, request, qs):
        qs.update(status=Post.PUBLISHED, published_at=timezone.now())

    @admin.action(description="Move selected posts to draft")
    def unpublish(self, request, qs):
        qs.update(status=Post.DRAFT)


@admin.register(Category, Tag)
class NamedAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(PageSeo)
class PageSeoAdmin(admin.ModelAdmin):
    list_display = ("page", "meta_title", "noindex")
    fields = ("page",) + SEO[1]["fields"]

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.utils.text import slugify
from django_ckeditor_5.fields import CKEditor5Field


class Seo(models.Model):
    """SEO fields every public page or post carries."""
    meta_title = models.CharField(max_length=70, blank=True, help_text="Shown in Google. Blank uses the title. Keep under 60 characters.")
    meta_description = models.CharField(max_length=170, blank=True, help_text="Google snippet. Aim for 140–160 characters.")
    meta_keywords = models.CharField(max_length=255, blank=True, help_text="Comma separated.")
    og_image = models.ImageField(upload_to="og/", blank=True, help_text="Share image, 1200 × 630. Blank uses the default.")
    noindex = models.BooleanField(default=False, help_text="Hide this from search engines.")

    class Meta:
        abstract = True


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("blog_category", args=[self.slug])


class Tag(models.Model):
    name = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status=Post.PUBLISHED, published_at__lte=timezone.now())


class Post(Seo):
    DRAFT, PUBLISHED = "draft", "published"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, help_text="The URL: /blog/<slug>/. Changing it keeps the old URL working with a redirect.")
    excerpt = models.TextField(max_length=300, blank=True, help_text="Short summary for cards. Blank uses the start of the body.")
    body = CKEditor5Field(config_name="default")
    cover = models.ImageField(upload_to="blog/", blank=True)
    cover_alt = models.CharField(max_length=160, blank=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="posts")
    tags = models.ManyToManyField(Tag, blank=True, related_name="posts")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=10, choices=[(DRAFT, "Draft"), (PUBLISHED, "Published")], default=DRAFT)
    featured = models.BooleanField(default=False)
    published_at = models.DateTimeField(default=timezone.now, help_text="A future date schedules the post.")
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    published = PublishedManager()

    class Meta:
        ordering = ["-published_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("blog_detail", args=[self.slug])

    @property
    def summary(self):
        return self.excerpt or strip_tags(self.body)[:200].rsplit(" ", 1)[0] + "…"

    @property
    def author_name(self):
        return (self.author.get_full_name() or self.author.username) if self.author else "Kashvo team"

    @property
    def read_minutes(self):
        return max(1, round(len(strip_tags(self.body).split()) / 200))

    def save(self, *args, **kwargs):
        self.slug = self.slug or slugify(self.title)[:220]
        if self.pk:
            old = Post.objects.filter(pk=self.pk).values_list("slug", flat=True).first()
            if old and old != self.slug:
                SlugRedirect.objects.update_or_create(old_slug=old, defaults={"post": self})
        super().save(*args, **kwargs)
        # a slug that is live again must not redirect away
        SlugRedirect.objects.filter(old_slug=self.slug).delete()


class SlugRedirect(models.Model):
    old_slug = models.SlugField(max_length=220, unique=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="old_slugs")

    def __str__(self):
        return f"/blog/{self.old_slug}/ → {self.post.slug}"


class PageSeo(Seo):
    """Editable SEO for the fixed pages (home, about, pricing, why-kashvo, blog index)."""
    PAGES = [("home", "Home"), ("about", "About us"), ("pricing", "Pricing"), ("why", "Why Kashvo"), ("blog", "Blog index")]
    page = models.CharField(max_length=20, choices=PAGES, unique=True)

    class Meta:
        verbose_name = "page SEO"
        verbose_name_plural = "page SEO"

    def __str__(self):
        return self.get_page_display()

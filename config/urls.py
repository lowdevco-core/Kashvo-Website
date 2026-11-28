from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from apps.cms import views
from apps.cms.sitemaps import PostSitemap, StaticSitemap

urlpatterns = [
    path("", views.page("home.html", "home"), name="home"),
    path("about/", views.page("about.html", "about"), name="about"),
    path("pricing/", views.page("pricing.html", "pricing"), name="pricing"),
    path("why-kashvo/", views.page("why.html", "why"), name="why"),
    path("blog/", views.blog_list, name="blog"),
    path("blog/category/<slug:slug>/", views.blog_list, name="blog_category"),
    path("blog/<slug:slug>/", views.blog_detail, name="blog_detail"),
    path("404/", views.preview_404, name="preview_404"),
    path("download-desktop-app/", views.download_desktop_app, name="download_desktop_app"),
    path("robots.txt", views.robots),
    path("sitemap.xml", sitemap, {"sitemaps": {"pages": StaticSitemap, "posts": PostSitemap}}, name="sitemap"),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("admin/", include("apps.cms.panel")),
    path("django-admin/", admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler404 = "apps.cms.views.custom_404"

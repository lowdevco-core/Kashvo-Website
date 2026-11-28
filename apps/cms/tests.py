from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from .models import Post


class SiteTests(TestCase):
    def setUp(self):
        self.post = Post.objects.create(title="Hello GST", slug="hello-gst", body="<p>Body text</p>", status=Post.PUBLISHED)

    def test_pages_render(self):
        for url in ["/", "/about/", "/pricing/", "/why-kashvo/", "/blog/", "/blog/hello-gst/", "/robots.txt", "/sitemap.xml"]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_changed_slug_redirects_permanently(self):
        self.post.slug = "gst-basics"
        self.post.save()
        r = self.client.get("/blog/hello-gst/")
        self.assertEqual((r.status_code, r["Location"]), (301, "/blog/gst-basics/"))
        # changing back must not loop
        self.post.slug = "hello-gst"
        self.post.save()
        self.assertEqual(self.client.get("/blog/hello-gst/").status_code, 200)
        self.assertEqual(self.client.get("/blog/gst-basics/").status_code, 301)

    def test_drafts_and_scheduled_hidden(self):
        Post.objects.create(title="Draft", slug="draft", body="x")
        Post.objects.create(title="Later", slug="later", body="x", status=Post.PUBLISHED, published_at=timezone.now() + timedelta(days=1))
        self.assertEqual(self.client.get("/blog/draft/").status_code, 404)
        self.assertEqual(self.client.get("/blog/later/").status_code, 404)
        self.assertNotContains(self.client.get("/sitemap.xml"), "/blog/later/")

    def test_meta_tags(self):
        html = self.client.get("/blog/hello-gst/").content.decode()
        for tag in ['name="description"', 'name="keywords"', 'rel="canonical"', 'og:title', "BlogPosting"]:
            self.assertIn(tag, html)

    def test_website_404_page(self):
        r = self.client.get("/non-existent-page-12345/")
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "This page went out of stock", status_code=404)

        r_preview = self.client.get("/404/")
        self.assertEqual(r_preview.status_code, 404)
        self.assertContains(r_preview, "This page went out of stock", status_code=404)


class PanelTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User
        self.boss = User.objects.create_superuser("boss", password="x")
        self.editor = User.objects.create_user("ed", password="x", is_staff=True)
        self.visitor = User.objects.create_user("v", password="x")

    def test_login_required_and_staff_only(self):
        self.assertRedirects(self.client.get("/admin/"), "/admin/login/?next=/admin/")
        self.client.force_login(self.visitor)
        self.assertEqual(self.client.get("/admin/").status_code, 302)
        r = self.client.post("/admin/login/", {"username": "v", "password": "x"})
        self.assertContains(r, "can&#x27;t sign in")

    def test_every_module_renders(self):
        self.client.force_login(self.boss)
        Post.objects.create(title="P", slug="p", body="x")
        for key in ["posts", "categories", "tags", "pages", "redirects", "users"]:
            self.assertEqual(self.client.get(f"/admin/{key}/").status_code, 200, key)
            self.assertEqual(self.client.get(f"/admin/{key}/add/").status_code, 200, key)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
        self.assertEqual(self.client.get("/django-admin/").status_code, 200)

    def test_editor_cannot_manage_users(self):
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get("/admin/users/").status_code, 403)
        self.assertNotContains(self.client.get("/admin/"), "/admin/users/")

    def test_create_post_sets_author(self):
        self.client.force_login(self.editor)
        r = self.client.post("/admin/posts/add/", {"title": "New", "slug": "new", "body": "<p>Hi</p>", "status": "published",
                                                    "published_at": "2026-01-01T10:00"})
        post = Post.objects.get(slug="new")
        self.assertRedirects(r, f"/admin/posts/{post.pk}/")
        self.assertEqual(post.author, self.editor)

    def test_cannot_delete_self(self):
        self.client.force_login(self.boss)
        self.client.post(f"/admin/users/{self.boss.pk}/delete/")
        self.assertTrue(type(self.boss).objects.filter(pk=self.boss.pk).exists())

    def test_cms_404_page(self):
        self.client.force_login(self.boss)
        r = self.client.get("/admin/non-existent-module-xyz/")
        self.assertEqual(r.status_code, 404)
        self.assertContains(r, "This CMS page doesn't exist", status_code=404)

        r_preview = self.client.get("/admin/404/")
        self.assertEqual(r_preview.status_code, 404)
        self.assertContains(r_preview, "This CMS page doesn't exist", status_code=404)


class LoadArticlesTests(TestCase):
    def test_loads_every_article_with_cover_and_seo(self):
        import tempfile
        from django.core.management import call_command
        from django.test import override_settings
        Post.objects.create(title="Old", slug="old", body="x", status=Post.PUBLISHED)
        with tempfile.TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            call_command("load_articles", "--replace", verbosity=0)
            posts = Post.published.all()
            self.assertEqual(posts.count(), 20)
            self.assertFalse(Post.objects.filter(slug="old").exists())
            for p in posts:
                self.assertTrue(p.cover.name.endswith(".jpg") and p.meta_keywords and p.excerpt, p.slug)
                self.assertEqual(self.client.get(p.get_absolute_url()).status_code, 200, p.slug)


class MediaCleanupTests(TestCase):
    def test_ckeditor_storage_saves_to_ckeditor_folder(self):
        import tempfile
        from pathlib import Path
        from django.core.files.base import ContentFile
        from django.test import override_settings
        from apps.cms.storage import CKEditorStorage
        with tempfile.TemporaryDirectory() as temp_media:
            with override_settings(MEDIA_ROOT=temp_media, MEDIA_URL="/media/"):
                storage = CKEditorStorage()
                saved_name = storage.save("sample.png", ContentFile(b"test image data"))
                self.assertTrue((Path(temp_media) / "ckeditor" / saved_name).exists())
                self.assertEqual(storage.url(saved_name), f"/media/ckeditor/{saved_name}")

    def test_deleting_post_cleans_up_cover_og_and_body_images(self):
        import tempfile
        from pathlib import Path
        from django.core.files.base import ContentFile
        from django.test import override_settings
        with tempfile.TemporaryDirectory() as temp_media:
            with override_settings(MEDIA_ROOT=temp_media, MEDIA_URL="/media/"):
                ck_dir = Path(temp_media) / "ckeditor"
                ck_dir.mkdir(parents=True, exist_ok=True)
                body_img = ck_dir / "chart.png"
                body_img.write_bytes(b"chart bytes")

                post = Post(
                    title="Test Media Cleanup",
                    slug="test-media-cleanup",
                    body='<p>Content <img src="/media/ckeditor/chart.png" alt="Chart"></p>',
                    status=Post.PUBLISHED,
                )
                post.cover.save("test_cover.jpg", ContentFile(b"cover bytes"), save=False)
                post.og_image.save("test_og.jpg", ContentFile(b"og bytes"), save=False)
                post.save()

                cover_path = Path(post.cover.path)
                og_path = Path(post.og_image.path)
                self.assertTrue(cover_path.is_file())
                self.assertTrue(og_path.is_file())
                self.assertTrue(body_img.is_file())

                post.delete()

                self.assertFalse(cover_path.is_file())
                self.assertFalse(og_path.is_file())
                self.assertFalse(body_img.is_file())


class DesktopAppDownloadAndSecurityTests(TestCase):
    def test_home_uses_qr_image_and_download_button(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "kashvo-qr.png")
        self.assertContains(r, "/download-desktop-app/")
        self.assertContains(r, "Download app")
        self.assertContains(r, "data-download-app")
        self.assertContains(r, "https://app.kashvo.in/")
        self.assertNotContains(r, "/login")

    def test_download_desktop_app_serves_uploaded_file_only(self):
        import tempfile
        from pathlib import Path
        from django.test import override_settings

        with tempfile.TemporaryDirectory() as tmp:
            upload_dir = Path(tmp)
            (upload_dir / ".gitkeep").write_bytes(b"")
            with override_settings(APP_UPLOAD_DIR=upload_dir):
                # Only .gitkeep present -> 404
                self.assertEqual(self.client.get("/download-desktop-app/").status_code, 404)

                installer = upload_dir / "Kashvo-Setup.exe"
                installer.write_bytes(b"installer-binary-content")

                r = self.client.get("/download-desktop-app/?file=../.env")
                self.assertEqual(r.status_code, 200)
                self.assertEqual(r["Content-Disposition"], 'attachment; filename="Kashvo-Setup.exe"')
                self.assertEqual(b"".join(r.streaming_content), b"installer-binary-content")

    def test_sensitive_and_arbitrary_paths_blocked(self):
        for path in [
            "/app-upload/",
            "/app-upload/.gitkeep",
            "/.env",
            "/config/settings.py",
            "/site.sqlite3",
            "/download-desktop-app/../../.env",
        ]:
            self.assertEqual(self.client.get(path).status_code, 404, path)

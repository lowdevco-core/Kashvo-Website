"""Kashvo CMS at /admin/: dashboard plus one generic list / add / edit / delete per module."""
from django import forms
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse

from .models import Category, PageSeo, Post, SlugRedirect, Tag

staff_member_required = user_passes_test(lambda u: u.is_active and u.is_staff, login_url="cms_login")

SEO_FIELDS = ["meta_title", "meta_description", "meta_keywords", "og_image", "noindex"]


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ["title", "slug", "body", "excerpt", "cover", "cover_alt", "status", "published_at", "featured",
                  "category", "tags", *SEO_FIELDS]
        widgets = {"published_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
                   "tags": forms.CheckboxSelectMultiple, "excerpt": forms.Textarea(attrs={"rows": 3}),
                   "meta_title": forms.TextInput(attrs={"data-counter": 60}),
                   "meta_description": forms.Textarea(attrs={"rows": 3, "data-counter": 160})}


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False,
                               help_text="Leave blank to keep the current password.")

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email", "is_active", "is_superuser"]
        labels = {"is_superuser": "Super admin (can manage users)"}

    def clean_password(self):
        pw = self.cleaned_data["password"]
        if not self.instance.pk and not pw:
            raise forms.ValidationError("Set a password for the new user.")
        return pw

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True  # everyone added here can sign in to the CMS
        if self.cleaned_data["password"]:
            user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


# form: a ModelForm class or a list of fields; cols: list columns; superuser: only super admins see it
MODULES = {
    "posts": dict(model=Post, label="Blog posts", one="post", icon="newspaper", form=PostForm,
                  cols=[("title", "Title"), ("status", "Status"), ("category", "Category"), ("published_at", "Date")],
                  search=["title", "slug", "body"], filters=("status", [("published", "Published"), ("draft", "Draft")])),
    "categories": dict(model=Category, label="Categories", one="category", icon="folder", form=["name", "slug"],
                       cols=[("name", "Name"), ("slug", "Slug")], search=["name"]),
    "tags": dict(model=Tag, label="Tags", one="tag", icon="tags", form=["name", "slug"],
                 cols=[("name", "Name"), ("slug", "Slug")], search=["name"]),
    "pages": dict(model=PageSeo, label="Page SEO", one="page", icon="file-search", form=["page", *SEO_FIELDS],
                  cols=[("page", "Page"), ("meta_title", "Meta title"), ("noindex", "Hidden")], search=["meta_title"]),
    "redirects": dict(model=SlugRedirect, label="Redirects", one="redirect", icon="corner-up-right", form=["old_slug", "post"],
                      cols=[("old_slug", "Old slug"), ("post", "Goes to")], search=["old_slug"]),
    "users": dict(model=User, label="Users", one="user", icon="users", form=UserForm, superuser=True,
                  cols=[("username", "Username"), ("get_full_name", "Name"), ("email", "Email"), ("is_superuser", "Super admin")],
                  search=["username", "email", "first_name", "last_name"]),
}

NAV = [  # sidebar groups
    ("Content", ["posts", "categories", "tags"]),
    ("Website", ["pages", "redirects"]),
    ("Access", ["users"]),
]


def module(request, key):
    m = MODULES.get(key)
    if not m:
        raise Http404
    if m.get("superuser") and not request.user.is_superuser:
        raise PermissionDenied
    return m


def form_class(m):
    if isinstance(m["form"], type):
        return m["form"]
    return forms.modelform_factory(m["model"], fields=m["form"])


def ctx(request, **extra):
    nav = [(title, [(k, MODULES[k]) for k in keys if request.user.is_superuser or not MODULES[k].get("superuser")]) for title, keys in NAV]
    return {"nav": [g for g in nav if g[1]], **extra}


@staff_member_required
def dashboard(request):
    cards = [
        ("posts", "Posts", Post.objects.count(), "newspaper"),
        ("posts", "Published", Post.published.count(), "circle-check"),
        ("posts", "Drafts", Post.objects.filter(status=Post.DRAFT).count(), "pencil-line"),
        ("categories", "Categories", Category.objects.count(), "folder"),
        ("tags", "Tags", Tag.objects.count(), "tags"),
        ("pages", "Pages with SEO", PageSeo.objects.count(), "file-search"),
        ("redirects", "Redirects", SlugRedirect.objects.count(), "corner-up-right"),
        ("users", "Users", User.objects.filter(is_staff=True).count(), "users"),
    ]
    if not request.user.is_superuser:
        cards = [c for c in cards if c[0] != "users"]
    recent = Post.objects.select_related("category").order_by("-updated_at")[:6]
    return render(request, "panel/dashboard.html", ctx(request, cards=cards, recent=recent, active="dashboard"))


@staff_member_required
def list_view(request, key):
    m = module(request, key)
    qs = m["model"].objects.all()
    if not qs.ordered:
        qs = qs.order_by("pk")
    q = request.GET.get("q", "").strip()
    if q:
        cond = Q()
        for f in m["search"]:
            cond |= Q(**{f"{f}__icontains": q})
        qs = qs.filter(cond)
    status = request.GET.get("status", "")
    if m.get("filters") and status:
        qs = qs.filter(**{m["filters"][0]: status})
    page = Paginator(qs, 20).get_page(request.GET.get("page"))
    rows = [(obj, [cell(obj, f) for f, _ in m["cols"]]) for obj in page]
    return render(request, "panel/list.html", ctx(request, m=m, key=key, page=page, rows=rows, q=q, status=status, active=key))


def cell(obj, field):
    if hasattr(obj, f"get_{field}_display"):
        return getattr(obj, f"get_{field}_display")()
    value = getattr(obj, field)
    return value() if callable(value) else value


@staff_member_required
def edit_view(request, key, pk=None):
    m = module(request, key)
    obj = get_object_or_404(m["model"], pk=pk) if pk else None
    Form = form_class(m)
    form = Form(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        saved = form.save(commit=False)
        if key == "posts" and not saved.author_id:
            saved.author = request.user
        saved.save()
        form.save_m2m()
        messages.success(request, f"Saved {m['one']} “{saved}”.")
        if "add_another" in request.POST:
            return redirect("cms_add", key=key)
        return redirect("cms_edit", key=key, pk=saved.pk)
    return render(request, "panel/form.html", ctx(request, m=m, key=key, obj=obj, form=form, active=key))


@staff_member_required
def delete_view(request, key, pk):
    m = module(request, key)
    obj = get_object_or_404(m["model"], pk=pk)
    if obj == request.user:
        messages.error(request, "You can't delete your own account.")
        return redirect("cms_list", key=key)
    if request.method == "POST":
        name = str(obj)
        obj.delete()
        messages.success(request, f"Deleted {m['one']} “{name}”.")
        return redirect("cms_list", key=key)
    return render(request, "panel/delete.html", ctx(request, m=m, key=key, obj=obj, active=key))


class Login(auth_views.LoginView):
    template_name = "panel/login.html"

    def dispatch(self, request, *args, **kwargs):
        # only staff skip the form; a signed-in non-staff user would otherwise loop login -> dashboard -> login
        self.redirect_authenticated_user = request.user.is_staff
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return self.get_redirect_url() or reverse("cms_dashboard")

    def form_valid(self, form):
        if not form.get_user().is_staff:
            form.add_error(None, "This account can't sign in to the CMS.")
            return self.form_invalid(form)
        return super().form_valid(form)


@staff_member_required
def panel_404(request):
    return render(request, "panel/404.html", ctx(request, active="dashboard"), status=404)


urlpatterns = [
    path("", dashboard, name="cms_dashboard"),
    path("404/", panel_404, name="cms_404"),
    path("login/", Login.as_view(), name="cms_login"),
    path("logout/", auth_views.LogoutView.as_view(next_page="cms_login"), name="cms_logout"),
    path("<slug:key>/", list_view, name="cms_list"),
    path("<slug:key>/add/", edit_view, name="cms_add"),
    path("<slug:key>/<int:pk>/", edit_view, name="cms_edit"),
    path("<slug:key>/<int:pk>/delete/", delete_view, name="cms_delete"),
]

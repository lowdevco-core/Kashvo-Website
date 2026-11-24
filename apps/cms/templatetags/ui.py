from django import template
from lucide.templatetags.lucide import lucide

register = template.Library()


@register.simple_tag
def icon(name, cls=""):
    """Lucide icon sized by CSS (.icon)."""
    return lucide(name, size=None, **{"class": f"icon {cls}".strip(), "aria-hidden": "true"})

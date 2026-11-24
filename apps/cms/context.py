from django.conf import settings


def site(request):
    return {"SITE_URL": settings.SITE_URL, "APP_URL": settings.APP_URL, "PHONE": settings.PHONE, "PHONE_LINK": settings.PHONE_LINK}

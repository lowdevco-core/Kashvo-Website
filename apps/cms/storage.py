from pathlib import Path
from django.conf import settings
from django.core.files.storage import FileSystemStorage


class CKEditorStorage(FileSystemStorage):
    """Stores CKEditor uploads under media/ckeditor/ instead of media root."""

    def __init__(self, **kwargs):
        media_root = Path(settings.MEDIA_ROOT)
        location = media_root / "ckeditor"
        location.mkdir(parents=True, exist_ok=True)
        base_url = f"{settings.MEDIA_URL}ckeditor/"
        super().__init__(location=str(location), base_url=base_url, **kwargs)

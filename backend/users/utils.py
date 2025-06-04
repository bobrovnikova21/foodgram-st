import base64
from django.core.files.base import ContentFile


def save_base64_image(base64_string, filename):
    format, imgstr = base64_string.split(";base64,")
    ext = format.split("/")[-1]
    return ContentFile(base64.b64decode(imgstr), name=f"{filename}.{ext}")

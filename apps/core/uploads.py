"""Validasi upload gambar. /media/ disajikan langsung oleh Nginx dari origin yang sama, jadi
file selain gambar raster (HTML, SVG) yang lolos upload akan menjadi XSS tersimpan."""
from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 2 * 1024 * 1024
ALLOWED_IMAGE_FORMATS = {'PNG': 'png', 'JPEG': 'jpg', 'WEBP': 'webp', 'GIF': 'gif'}


def validated_image_extension(uploaded_file, max_bytes=MAX_IMAGE_BYTES):
    """Kembalikan ekstensi aman berdasarkan isi file (bukan nama file), atau ValidationError."""
    if uploaded_file.size > max_bytes:
        raise ValidationError(f"Ukuran gambar maksimal {max_bytes // (1024 * 1024)} MB.")
    try:
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as img:
            image_format = img.format
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ValidationError("File bukan gambar PNG, JPG, WEBP, atau GIF yang valid.")
    finally:
        uploaded_file.seek(0)
    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError("Format gambar harus PNG, JPG, WEBP, atau GIF.")
    return ALLOWED_IMAGE_FORMATS[image_format]

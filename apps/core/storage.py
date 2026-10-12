from whitenoise.storage import CompressedManifestStaticFilesStorage


class HashedStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """
    Nama file statis memuat hash isi (app.3f2a9c.css), sehingga cache immutable 1 tahun di Nginx
    aman tanpa cache-bust manual. Referensi yang tidak ada di manifest jatuh ke nama asli, bukan error 500.
    """
    manifest_strict = False

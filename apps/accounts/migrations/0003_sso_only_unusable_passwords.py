from django.contrib.auth.hashers import make_password
from django.db import migrations


def disable_local_passwords(apps, schema_editor):
    """
    Semua peran login lewat SSO Keycloak. Kata sandi lokal lama (Jingga123, jingga{NIS})
    bisa ditebak, jadi dicabut untuk semua akun kecuali superuser (jalur login darurat).
    """
    User = apps.get_model('accounts', 'CustomUser')
    count = 0
    for user in User.objects.filter(is_superuser=False).exclude(password__startswith='!').only('id', 'password'):
        user.password = make_password(None)
        user.save(update_fields=['password'])
        count += 1
    if count:
        print(f"\n  kata sandi lokal dicabut: {count} akun", end='')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_customuser_full_name_customuser_nis_and_more'),
    ]

    operations = [
        migrations.RunPython(disable_local_passwords, migrations.RunPython.noop),
    ]

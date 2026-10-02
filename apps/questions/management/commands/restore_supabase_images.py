import os
import json
import psycopg
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.questions.models import Question


class Command(BaseCommand):
    help = "Restores original Supabase Cloud image URLs for questions and options, and optionally downloads local backup."

    def add_arguments(self, parser):
        parser.add_argument(
            '--supabase-db-url',
            type=str,
            default=os.environ.get(
                'SUPABASE_DB_URL',
                'postgresql://postgres:Rpljingga123@db.vlawnrlczxagcitlaokh.supabase.co:5432/postgres'
            ),
            help='PostgreSQL connection URI for Supabase Cloud',
        )
        parser.add_argument(
            '--json-file',
            type=str,
            default='',
            help='Path to a JSON file containing exported image records',
        )
        parser.add_argument(
            '--export-json',
            type=str,
            default='',
            help='Export records from Supabase Cloud to a JSON file instead of updating database',
        )
        parser.add_argument(
            '--download',
            action='store_true',
            default=True,
            help='Also download physical image files to local MEDIA_ROOT/questions as backup',
        )
        parser.add_argument(
            '--no-download',
            dest='download',
            action='store_false',
            help='Only update database URLs without downloading files',
        )

    def handle(self, *args, **options):
        db_url = options['supabase_db_url']
        json_file = options.get('json_file')
        export_json = options.get('export_json')
        do_download = options['download']

        default_json_path = os.path.join(settings.BASE_DIR, 'data', 'supabase_question_images.json')
        cloud_rows = []

        if json_file or (not export_json and os.path.exists(default_json_path) and not db_url.startswith('postgres')):
            target_json = json_file if json_file else default_json_path
            self.stdout.write(self.style.NOTICE(f"Loading image records from JSON file: {target_json}"))
            with open(target_json, 'r', encoding='utf-8') as f:
                cloud_rows = json.load(f)
        elif json_file:
            self.stdout.write(self.style.NOTICE(f"Loading image records from JSON file: {json_file}"))
            with open(json_file, 'r', encoding='utf-8') as f:
                cloud_rows = json.load(f)
        else:
            self.stdout.write(self.style.NOTICE("Connecting to Supabase Cloud PostgreSQL..."))
            try:
                cloud_conn = psycopg.connect(db_url, connect_timeout=15)
            except Exception as e:
                if os.path.exists(default_json_path):
                    self.stdout.write(self.style.WARNING(f"Direct connection failed ({e}). Falling back to {default_json_path}"))
                    with open(default_json_path, 'r', encoding='utf-8') as f:
                        cloud_rows = json.load(f)
                else:
                    self.stderr.write(self.style.ERROR(f"Failed to connect to Supabase Cloud: {e}"))
                    return
            else:
                self.stdout.write(self.style.NOTICE("Fetching question image records from Supabase Cloud..."))
                with cloud_conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, question_image, image_a, image_b, image_c, image_d, image_e
                        FROM questions
                        WHERE (question_image IS NOT NULL AND question_image != '')
                           OR (image_a IS NOT NULL AND image_a != '')
                           OR (image_b IS NOT NULL AND image_b != '')
                           OR (image_c IS NOT NULL AND image_c != '')
                           OR (image_d IS NOT NULL AND image_d != '')
                           OR (image_e IS NOT NULL AND image_e != '');
                    """)
                    raw_rows = cur.fetchall()
                cloud_conn.close()

                cloud_rows = [
                    {
                        'id': str(r[0]),
                        'question_image': r[1] or '',
                        'image_a': r[2] or '',
                        'image_b': r[3] or '',
                        'image_c': r[4] or '',
                        'image_d': r[5] or '',
                        'image_e': r[6] or '',
                    }
                    for r in raw_rows
                ]

        if export_json:
            os.makedirs(os.path.dirname(os.path.abspath(export_json)), exist_ok=True)
            with open(export_json, 'w', encoding='utf-8') as f:
                json.dump(cloud_rows, f, indent=2)
            self.stdout.write(self.style.SUCCESS(f"Exported {len(cloud_rows)} records to {export_json}"))
            return

        total_cloud = len(cloud_rows)
        self.stdout.write(self.style.NOTICE(f"Processing {total_cloud} questions with images."))

        media_root = getattr(settings, 'MEDIA_ROOT', os.path.join(settings.BASE_DIR, 'media'))
        q_dir = os.path.join(media_root, 'questions')
        opt_dir = os.path.join(media_root, 'questions', 'options')
        if do_download:
            os.makedirs(q_dir, exist_ok=True)
            os.makedirs(opt_dir, exist_ok=True)

        updated_count = 0
        downloaded_count = 0
        not_found_count = 0

        with transaction.atomic():
            for item in cloud_rows:
                if isinstance(item, (list, tuple)):
                    qid = str(item[0])
                    q_img = item[1] or ''
                    img_a = item[2] or ''
                    img_b = item[3] or ''
                    img_c = item[4] or ''
                    img_d = item[5] or ''
                    img_e = item[6] or ''
                else:
                    qid = str(item['id'])
                    q_img = item.get('question_image') or ''
                    img_a = item.get('image_a') or ''
                    img_b = item.get('image_b') or ''
                    img_c = item.get('image_c') or ''
                    img_d = item.get('image_d') or ''
                    img_e = item.get('image_e') or ''

                q = Question.objects.filter(id=qid).first()
                if not q:
                    not_found_count += 1
                    continue

                q.question_image = q_img
                q.image_a = img_a
                q.image_b = img_b
                q.image_c = img_c
                q.image_d = img_d
                q.image_e = img_e
                q.save(update_fields=[
                    'question_image', 'image_a', 'image_b', 'image_c', 'image_d', 'image_e'
                ])
                updated_count += 1

                if do_download:
                    # Download question image
                    if q_img.startswith('http://') or q_img.startswith('https://'):
                        ext = q_img.split('?')[0].split('.')[-1].lower()
                        if ext not in ['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg']:
                            ext = 'jpg'
                        target_file = os.path.join(q_dir, f"{qid}.{ext}")
                        if not os.path.exists(target_file):
                            try:
                                resp = requests.get(q_img, timeout=10)
                                if resp.status_code == 200:
                                    with open(target_file, 'wb') as f:
                                        f.write(resp.content)
                                    downloaded_count += 1
                            except Exception as dl_err:
                                self.stderr.write(f"Download error for {qid}: {dl_err}")

                    # Download option images
                    for opt_key, opt_url in [('a', img_a), ('b', img_b), ('c', img_c), ('d', img_d), ('e', img_e)]:
                        if opt_url and (opt_url.startswith('http://') or opt_url.startswith('https://')):
                            ext = opt_url.split('?')[0].split('.')[-1].lower()
                            if ext not in ['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg']:
                                ext = 'jpg'
                            opt_file = os.path.join(opt_dir, f"{qid}_{opt_key}.{ext}")
                            if not os.path.exists(opt_file):
                                try:
                                    resp = requests.get(opt_url, timeout=10)
                                    if resp.status_code == 200:
                                        with open(opt_file, 'wb') as f:
                                            f.write(resp.content)
                                        downloaded_count += 1
                                except Exception as dl_err:
                                    self.stderr.write(f"Download error for {qid}_{opt_key}: {dl_err}")

        self.stdout.write(self.style.SUCCESS(
            f"Successfully updated {updated_count} questions with Supabase Cloud URLs. "
            f"Downloaded {downloaded_count} physical image files as local backup. "
            f"Not found in Django: {not_found_count}."
        ))

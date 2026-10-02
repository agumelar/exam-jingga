import os
import requests
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.questions.models import Question


class Command(BaseCommand):
    help = "Cache remote Supabase question and option images to local media storage for offline lab CBT operation."

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of questions to process (0 for all)',
        )

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT
        q_dir = os.path.join(media_root, 'questions')
        opt_dir = os.path.join(media_root, 'questions', 'options')
        os.makedirs(q_dir, exist_ok=True)
        os.makedirs(opt_dir, exist_ok=True)

        questions = Question.objects.all()
        limit = options.get('limit')
        if limit and limit > 0:
            questions = questions[:limit]

        total = questions.count()
        self.stdout.write(self.style.NOTICE(f"Scanning {total} questions for remote Supabase images..."))

        cached_q_count = 0
        cached_opt_count = 0
        failed_count = 0

        for q in questions:
            # 1. Check question_image
            raw_q_img = str(q.question_image) if q.question_image else ''
            if raw_q_img.startswith('http://') or raw_q_img.startswith('https://'):
                ext = raw_q_img.split('?')[0].split('.')[-1]
                if ext.lower() not in ['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg']:
                    ext = 'jpg'
                local_rel_path = f"questions/{q.id}.{ext}"
                local_abs_path = os.path.join(media_root, local_rel_path)

                if not os.path.exists(local_abs_path):
                    try:
                        resp = requests.get(raw_q_img, timeout=10)
                        if resp.status_code == 200:
                            with open(local_abs_path, 'wb') as f:
                                f.write(resp.content)
                            q.question_image.name = local_rel_path
                            q.save(update_fields=['question_image'])
                            cached_q_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        self.stderr.write(f"Failed to download question {q.id} image: {e}")
                        failed_count += 1
                else:
                    q.question_image.name = local_rel_path
                    q.save(update_fields=['question_image'])
                    cached_q_count += 1

            # 2. Check options image_a - image_e
            for opt_key in ['a', 'b', 'c', 'd', 'e']:
                field_name = f"image_{opt_key}"
                raw_opt_img = str(getattr(q, field_name, '')) if getattr(q, field_name, None) else ''
                if raw_opt_img.startswith('http://') or raw_opt_img.startswith('https://'):
                    ext = raw_opt_img.split('?')[0].split('.')[-1]
                    if ext.lower() not in ['jpg', 'jpeg', 'png', 'webp', 'gif', 'svg']:
                        ext = 'jpg'
                    local_rel_path = f"questions/options/{q.id}_{opt_key}.{ext}"
                    local_abs_path = os.path.join(media_root, local_rel_path)

                    if not os.path.exists(local_abs_path):
                        try:
                            resp = requests.get(raw_opt_img, timeout=10)
                            if resp.status_code == 200:
                                with open(local_abs_path, 'wb') as f:
                                    f.write(resp.content)
                                getattr(q, field_name).name = local_rel_path
                                q.save(update_fields=[field_name])
                                cached_opt_count += 1
                            else:
                                failed_count += 1
                        except Exception as e:
                            self.stderr.write(f"Failed to download option {opt_key} for {q.id}: {e}")
                            failed_count += 1
                    else:
                        getattr(q, field_name).name = local_rel_path
                        q.save(update_fields=[field_name])
                        cached_opt_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Cached {cached_q_count} question images and {cached_opt_count} option images locally. Failed: {failed_count}."
            )
        )

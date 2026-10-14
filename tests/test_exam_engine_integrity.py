"""Fase 1 audit: integritas ujian siswa (kepemilikan sesi, eligibility, waktu, pengacakan)."""
from collections import Counter
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import Role
from apps.exam_engine.models import ExamSession, StudentAnswer
from apps.exam_engine.utils import initialize_session_answers
from apps.master_data.models import ClassRoom, Major, Student, Subject, Teacher, TeacherAssignment
from apps.questions.models import Question, detect_cross_referencing_options
from apps.schedules.models import Exam, ExamQuestion, Schedule

User = get_user_model()


class World:
    """Satu kelas, satu guru, satu UH terverifikasi berisi 5 soal."""

    def __init__(self, tag='w', exam_type='UH', n_questions=5, shuffle=True):
        self.major = Major.objects.create(name=f'Jurusan {tag}', code=f'J{tag}'[:10])
        self.cls = ClassRoom.objects.create(name=f'X {tag} 1', level=10, major=self.major)
        self.other_cls = ClassRoom.objects.create(name=f'X {tag} 2', level=10, major=self.major)
        self.subject = Subject.objects.create(name=f'Mapel {tag}')
        tuser = User.objects.create_user(username=f'guru_{tag}', role=Role.GURU)
        self.teacher = Teacher.objects.create(user=tuser, full_name=f'Guru {tag}', email=f'guru_{tag}@x.id')
        TeacherAssignment.objects.create(teacher=self.teacher, subject=self.subject, class_room=self.cls)
        self.exam = Exam.objects.create(teacher=self.teacher, subject=self.subject, title=f'{exam_type} {tag}',
                                        exam_type=exam_type, level=10, status='validated', duration=60,
                                        target_question_count=n_questions, token='TKN123',
                                        shuffle_questions=shuffle, shuffle_options=shuffle)
        self.questions = []
        for i in range(n_questions):
            q = Question.objects.create(subject=self.subject, level=10, created_by=self.teacher,
                                        question_text=f'Soal {tag} {i}', option_a=f'a{i}', option_b=f'b{i}',
                                        option_c=f'c{i}', option_d=f'd{i}', option_e=f'e{i}', correct_answer='C')
            ExamQuestion.objects.create(exam=self.exam, question=q, order_number=i + 1)
            self.questions.append(q)
        now = timezone.now()
        self.schedule = Schedule.objects.create(exam=self.exam, class_room=self.cls, teacher=self.teacher,
                                                start_time=now - timedelta(minutes=5), end_time=now + timedelta(hours=2),
                                                token='TKN123', teacher_quota=n_questions)

    def student(self, nis, cls=None, status='aktif'):
        user = User.objects.create_user(username=nis, nis=nis, role=Role.SISWA)
        return Student.objects.create(user=user, nis=nis, full_name=f'Siswa {nis}', class_room=cls or self.cls, status=status)

    def start(self, client, student):
        client.force_login(student.user)
        res = client.post(reverse('exam_engine:confirm_token'), {'schedule_id': str(self.schedule.id), 'token': 'TKN123'},
                          HTTP_HX_REQUEST='true')
        return res, ExamSession.objects.filter(student=student, schedule=self.schedule).first()


def _save(client, session, **data):
    return client.post(reverse('exam_engine:save_answer', args=[session.id]), data, HTTP_HX_REQUEST='true')


# ==============================================================================
# Kepemilikan sesi
# ==============================================================================

@pytest.mark.django_db
def test_other_student_cannot_save_answers_into_my_session(client):
    w = World('own')
    me, other = w.student('1001'), w.student('1002')
    _, session = w.start(client, me)
    q = w.questions[0]

    client.force_login(other.user)
    res = _save(client, session, question_id=q.id, chosen_answer='C')

    assert res.status_code == 404
    assert StudentAnswer.objects.get(session=session, question=q).chosen_answer is None


@pytest.mark.django_db
@pytest.mark.parametrize('name', ['finish_exam', 'violation_handler', 'check_status', 'exam_interface'])
def test_anonymous_cannot_touch_session_endpoints(client, name):
    w = World(f'anon{name[:3]}')
    stu = w.student(f'20{len(name)}')
    _, session = w.start(client, stu)
    client.logout()

    method = client.get if name in ('check_status', 'exam_interface') else client.post
    res = method(reverse(f'exam_engine:{name}', args=[session.id]))

    session.refresh_from_db()
    assert res.status_code in (302, 404)
    assert session.status == 'active'
    assert session.violation_count == 0


@pytest.mark.django_db
def test_teacher_cannot_open_student_session(client):
    w = World('tch')
    _, session = w.start(client, w.student('3001'))
    client.force_login(w.teacher.user)

    assert client.get(reverse('exam_engine:exam_interface', args=[session.id])).status_code == 404


@pytest.mark.django_db
def test_staff_without_student_profile_cannot_start_exam(client):
    w = World('staff')
    client.force_login(w.teacher.user)

    client.post(reverse('exam_engine:confirm_token'), {'schedule_id': str(w.schedule.id), 'token': 'TKN123'})

    assert not Student.objects.filter(user=w.teacher.user).exists()
    assert not ExamSession.objects.exists()


# ==============================================================================
# Eligibility di gerbang token
# ==============================================================================

@pytest.mark.django_db
def test_student_from_other_class_rejected_even_with_token(client):
    w = World('cls')
    outsider = w.student('4001', cls=w.other_cls)

    res, session = w.start(client, outsider)

    assert session is None
    assert 'bukan untuk kelas Anda' in res.content.decode()


@pytest.mark.django_db
def test_inactive_student_rejected(client):
    w = World('inact')
    res, session = w.start(client, w.student('4002', status='keluar'))
    assert session is None


@pytest.mark.django_db
def test_student_without_class_sees_no_exams(client):
    w = World('nocls')
    user = User.objects.create_user(username='4003', nis='4003', role=Role.SISWA)
    Student.objects.create(user=user, nis='4003', full_name='Tanpa Kelas', class_room=None)
    client.force_login(user)

    res = client.get(reverse('exam_engine:student_dashboard'))

    assert res.context['available_exams'] == []
    assert 'belum terdaftar di kelas' in res.content.decode()


@pytest.mark.django_db
def test_token_error_is_rendered_with_swappable_status(client):
    w = World('tokerr')
    stu = w.student('4004')
    client.force_login(stu.user)

    res = client.post(reverse('exam_engine:confirm_token'), {'schedule_id': str(w.schedule.id), 'token': 'SALAH1'},
                      HTTP_HX_REQUEST='true')

    assert res.status_code == 200
    assert 'Token ujian tidak valid' in res.content.decode()


# ==============================================================================
# Jawaban, Ragu, waktu
# ==============================================================================

@pytest.mark.django_db
def test_doubt_toggle_keeps_chosen_answer(client):
    w = World('doubt')
    _, session = w.start(client, w.student('5001'))
    q = w.questions[0]
    _save(client, session, question_id=q.id, chosen_answer='C')

    _save(client, session, question_id=q.id, toggle_doubt='1')

    ans = StudentAnswer.objects.get(session=session, question=q)
    assert ans.chosen_answer == 'C'
    assert ans.is_doubt is True

    _save(client, session, question_id=q.id, chosen_answer='D')
    ans.refresh_from_db()
    assert ans.chosen_answer == 'D'
    assert ans.is_doubt is True

    _save(client, session, question_id=q.id, toggle_doubt='1')
    ans.refresh_from_db()
    assert ans.is_doubt is False


@pytest.mark.django_db
def test_answer_after_time_up_is_rejected_and_session_graded(client):
    w = World('late')
    _, session = w.start(client, w.student('5002'))
    q = w.questions[0]
    ExamSession.objects.filter(pk=session.pk).update(started_at=timezone.now() - timedelta(minutes=61))

    res = _save(client, session, question_id=q.id, chosen_answer='C')

    session.refresh_from_db()
    assert session.status == 'finished'
    assert res.headers.get('HX-Redirect') == '/student/dashboard/'
    assert StudentAnswer.objects.get(session=session, question=q).chosen_answer is None


@pytest.mark.django_db
def test_grade_expired_sessions_command(client):
    w = World('cron')
    _, session = w.start(client, w.student('5003'))
    _, fresh = w.start(client, w.student('5004'))
    ExamSession.objects.filter(pk=session.pk).update(started_at=timezone.now() - timedelta(minutes=90))

    call_command('grade_expired_sessions')

    session.refresh_from_db()
    fresh.refresh_from_db()
    assert session.status == 'finished'
    assert session.finished_at is not None
    assert fresh.status == 'active'


@pytest.mark.django_db
def test_finishing_twice_keeps_first_finished_at(client):
    w = World('twice')
    _, session = w.start(client, w.student('5005'))
    client.post(reverse('exam_engine:finish_exam', args=[session.id]))
    session.refresh_from_db()
    first = session.finished_at

    client.post(reverse('exam_engine:finish_exam', args=[session.id]))

    session.refresh_from_db()
    assert session.finished_at == first


@pytest.mark.django_db
def test_exam_pages_are_not_cached(client):
    w = World('cache')
    _, session = w.start(client, w.student('5006'))

    res = client.get(reverse('exam_engine:exam_interface', args=[session.id]))

    assert 'no-store' in res.headers.get('Cache-Control', '')


@pytest.mark.django_db
def test_violation_count_and_heartbeat(client):
    w = World('viol', exam_type='PAS')
    _, session = w.start(client, w.student('5007'))

    client.post(reverse('exam_engine:violation_handler', args=[session.id]))
    client.post(reverse('exam_engine:violation_handler', args=[session.id]))
    client.post(reverse('exam_engine:heartbeat', args=[session.id]), {'visible': '1'})

    session.refresh_from_db()
    assert session.violation_count == 2
    assert session.status == 'locked'
    assert session.last_seen_at is not None


@pytest.mark.django_db
def test_uh_violation_never_locks(client):
    w = World('violuh', exam_type='UH')
    _, session = w.start(client, w.student('5008'))
    for _ in range(4):
        client.post(reverse('exam_engine:violation_handler', args=[session.id]))
    session.refresh_from_db()
    assert session.status == 'active'
    assert session.violation_count == 4


# ==============================================================================
# Urutan & pengacakan
# ==============================================================================

@pytest.mark.django_db
def test_question_reused_in_two_exams_appears_once(client):
    w = World('reuse', shuffle=False)
    other = Exam.objects.create(subject=w.subject, title='Lain', level=10, status='validated', target_question_count=1)
    ExamQuestion.objects.create(exam=other, question=w.questions[0], order_number=7)
    _, session = w.start(client, w.student('6001'))

    res = client.get(reverse('exam_engine:exam_interface', args=[session.id]))

    assert res.context['total_count'] == 5
    assert [item['question'].id for item in res.context['questions']] == [q.id for q in w.questions]


@pytest.mark.django_db
def test_shuffle_stores_order_and_option_permutation(client):
    w = World('shuf', n_questions=8)
    _, session = w.start(client, w.student('6002'))

    answers = list(StudentAnswer.objects.filter(session=session).order_by('order_number'))
    assert [a.order_number for a in answers] == list(range(1, 9))
    for a in answers:
        assert sorted(a.option_order) == list('ABCDE')


@pytest.mark.django_db
def test_shuffled_option_answer_is_stored_in_original_letter(client):
    w = World('orig')
    _, session = w.start(client, w.student('6003'))
    ans = StudentAnswer.objects.filter(session=session).order_by('order_number').first()
    StudentAnswer.objects.filter(pk=ans.pk).update(option_order='CABED')

    res = client.get(reverse('exam_engine:question_swap', args=[session.id, 1]))
    displayed = res.context['current_item']['options']
    assert [o['display_key'] for o in displayed] == list('ABCDE')
    assert [o['key'] for o in displayed] == list('CABED')

    _save(client, session, question_id=ans.question_id, chosen_answer='C')
    ans.refresh_from_db()
    assert ans.chosen_answer == 'C'
    assert ans.is_correct is True


@pytest.mark.django_db
def test_locked_option_order_is_never_shuffled(client):
    w = World('lockopt', n_questions=6)
    Question.objects.filter(pk__in=[q.pk for q in w.questions]).update(lock_option_order=True)
    _, session = w.start(client, w.student('6004'))

    assert set(StudentAnswer.objects.filter(session=session).values_list('option_order', flat=True)) == {'ABCDE'}


@pytest.mark.django_db
def test_missing_option_e_excluded_from_permutation(client):
    w = World('noe', n_questions=1)
    Question.objects.filter(pk=w.questions[0].pk).update(option_e='')
    _, session = w.start(client, w.student('6005'))

    order = StudentAnswer.objects.get(session=session).option_order
    assert sorted(order) == list('ABCD')


@pytest.mark.django_db
def test_initialize_is_idempotent():
    w = World('idem')
    stu = w.student('6006')
    session = ExamSession.objects.create(student=stu, schedule=w.schedule)
    initialize_session_answers(session)
    initialize_session_answers(session)
    assert StudentAnswer.objects.filter(session=session).count() == 5
    assert Counter(StudentAnswer.objects.filter(session=session).values_list('order_number', flat=True)).most_common(1)[0][1] == 1


@pytest.mark.parametrize('options,expected', [
    (['Merah', 'Biru', 'Hijau', 'Kuning', 'Semua jawaban benar'], True),
    (['1', '2', 'A dan B benar', '4', '5'], True),
    (['x', 'y', 'Jawaban a dan c', 'z', 'w'], True),
    (['Tidak ada jawaban yang benar', 'b', 'c', 'd', 'e'], True),
    (['Jakarta', 'Bandung', 'Surabaya', 'Medan', 'Makassar'], False),
    (['Ada dan tiada', 'Semut', 'Gajah', 'Kuda', 'Sapi'], False),
])
def test_detect_cross_referencing_options(options, expected):
    assert detect_cross_referencing_options(options) is expected


@pytest.mark.django_db
def test_violation_locks_only_the_session_row(client):
    # PostgreSQL menolak FOR UPDATE yang mencakup outer join (guru jadwal dan mapel boleh kosong);
    # SQLite mengabaikan FOR UPDATE, jadi yang diuji adalah argumen penguncian
    from django.db.models.query import QuerySet
    w = World('pglock', exam_type='PAS')
    _, session = w.start(client, w.student('8801'))
    calls = []
    original = QuerySet.select_for_update

    def spy(self, *args, **kwargs):
        calls.append(kwargs)
        return original(self, *args, **kwargs)

    from unittest.mock import patch
    with patch.object(QuerySet, 'select_for_update', spy):
        client.post(reverse('exam_engine:violation_handler', args=[session.id]))

    assert calls and all(c.get('of') == ('self',) for c in calls)
    session.refresh_from_db()
    assert session.violation_count == 1

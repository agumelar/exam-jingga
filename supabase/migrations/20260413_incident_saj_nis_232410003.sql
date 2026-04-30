-- INCIDENT HOTFIX (SAJ)
-- Target:
--   schedule_id = 35a74185-e703-446f-b698-e022158a60eb
--   nis         = 232410003
--
-- Tujuan:
-- 1) Diagnostik cepat akar masalah blank setelah token
-- 2) Reset sesi ghost-finished (finished tanpa jawaban)
-- 3) Cek kesiapan soal pada exam terkait

begin;

-- =========================================================
-- A. DIAGNOSTIK CEPAT
-- =========================================================

-- A1) Data siswa target
select id, nis, full_name, status, class_id
from public.students
where nis = '232410003';

-- A2) Data schedule + exam target
select
  s.id as schedule_id,
  s.exam_id,
  s.class_id as schedule_class_id,
  s.teacher_id as schedule_teacher_id,
  s.session_no,
  s.status as schedule_status,
  s.start_time,
  s.end_time,
  e.title as exam_title,
  e.type as exam_type,
  e.level as exam_level,
  e.subject_id,
  e.status as exam_status,
  e.duration,
  e.target_question_count
from public.schedules s
join public.exams e on e.id = s.exam_id
where s.id = '35a74185-e703-446f-b698-e022158a60eb';

-- A3) Teacher assignment untuk kelas siswa + subject exam
with stu as (
  select id as student_id, class_id
  from public.students
  where nis = '232410003'
), sch as (
  select s.id as schedule_id, s.exam_id, e.subject_id
  from public.schedules s
  join public.exams e on e.id = s.exam_id
  where s.id = '35a74185-e703-446f-b698-e022158a60eb'
)
select ta.teacher_id, ta.class_id, ta.subject_id
from public.teacher_assignments ta, stu, sch
where ta.class_id = stu.class_id
  and ta.subject_id = sch.subject_id;

-- A4) Total soal exam dan soal by allowed teachers
with sch as (
  select s.id as schedule_id, s.exam_id, e.subject_id
  from public.schedules s
  join public.exams e on e.id = s.exam_id
  where s.id = '35a74185-e703-446f-b698-e022158a60eb'
), stu as (
  select id as student_id, class_id
  from public.students
  where nis = '232410003'
), allowed_teachers as (
  select ta.teacher_id
  from public.teacher_assignments ta, stu, sch
  where ta.class_id = stu.class_id
    and ta.subject_id = sch.subject_id
)
select
  (select count(*) from public.exam_questions eq join sch on sch.exam_id = eq.exam_id) as total_exam_questions,
  (
    select count(*)
    from public.exam_questions eq
    join public.questions q on q.id = eq.question_id
    join sch on sch.exam_id = eq.exam_id
    where q.created_by in (select teacher_id from allowed_teachers)
  ) as questions_by_allowed_teachers;

-- A5) Session siswa pada schedule target + jumlah jawaban
with stu as (
  select id as student_id
  from public.students
  where nis = '232410003'
)
select
  es.id as session_id,
  es.status,
  es.started_at,
  es.finished_at,
  es.score,
  es.violation_count,
  (
    select count(*)
    from public.student_answers sa
    where sa.session_id = es.id
  ) as answer_count
from public.exam_sessions es, stu
where es.student_id = stu.student_id
  and es.schedule_id = '35a74185-e703-446f-b698-e022158a60eb'
order by es.started_at desc;


-- =========================================================
-- B. HOTFIX DATA: GHOST FINISHED -> ACTIVE
-- =========================================================
-- Kriteria ghost:
-- - status = finished
-- - tidak punya jawaban sama sekali
-- - hanya untuk schedule target (agar sangat aman)

with target_student as (
  select id as student_id
  from public.students
  where nis = '232410003'
)
update public.exam_sessions es
set
  status = 'active',
  finished_at = null,
  score = 0,
  violation_count = 0,
  started_at = now()
from target_student ts
where es.student_id = ts.student_id
  and es.schedule_id = '35a74185-e703-446f-b698-e022158a60eb'
  and es.status = 'finished'
  and not exists (
    select 1
    from public.student_answers sa
    where sa.session_id = es.id
  );


-- =========================================================
-- C. VERIFIKASI PASCA HOTFIX
-- =========================================================

-- C1) Pastikan tidak ada lagi ghost finished di target
with target_student as (
  select id as student_id
  from public.students
  where nis = '232410003'
)
select
  es.id,
  es.student_id,
  es.schedule_id,
  es.status,
  es.started_at,
  es.finished_at,
  es.score
from public.exam_sessions es
join target_student ts on ts.student_id = es.student_id
where es.schedule_id = '35a74185-e703-446f-b698-e022158a60eb'
  and es.status = 'finished'
  and not exists (
    select 1
    from public.student_answers sa
    where sa.session_id = es.id
  );

-- C2) Tampilkan sesi terbaru setelah update
with target_student as (
  select id as student_id
  from public.students
  where nis = '232410003'
)
select
  es.id as session_id,
  es.status,
  es.started_at,
  es.finished_at,
  es.score,
  es.violation_count
from public.exam_sessions es
join target_student ts on ts.student_id = es.student_id
where es.schedule_id = '35a74185-e703-446f-b698-e022158a60eb'
order by es.started_at desc;

commit;

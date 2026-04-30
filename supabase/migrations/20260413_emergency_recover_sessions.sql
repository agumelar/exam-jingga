-- EMERGENCY RECOVERY
-- Tujuan: memulihkan sesi yang ter-reset jadi active padahal siswa sudah mengerjakan.
-- Aman dijalankan berulang (idempotent untuk update status -> finished pada kandidat valid).

begin;

-- 0) Backup cepat sebelum recovery
create table if not exists public._backup_exam_sessions_20260413 as
select * from public.exam_sessions where false;

insert into public._backup_exam_sessions_20260413
select es.*
from public.exam_sessions es
where not exists (
  select 1
  from public._backup_exam_sessions_20260413 b
  where b.id = es.id
);


-- 1) Hitung metrik sesi untuk recovery score/status
with session_metrics as (
  select
    es.id as session_id,
    es.status,
    es.started_at,
    es.finished_at,
    es.score,
    es.schedule_id,
    s.exam_id,
    e.duration,
    count(sa.id) as answer_count,
    count(distinct eq.question_id) as total_questions,
    count(*) filter (
      where sa.id is not null
        and sa.chosen_answer is not null
        and upper(trim(sa.chosen_answer::text)) = upper(trim(coalesce(q.correct_answer::text, '')))
    ) as correct_count
  from public.exam_sessions es
  join public.schedules s on s.id = es.schedule_id
  join public.exams e on e.id = s.exam_id
  left join public.student_answers sa on sa.session_id = es.id
  left join public.exam_questions eq on eq.exam_id = s.exam_id
  left join public.questions q on q.id = sa.question_id
  group by es.id, s.exam_id, e.duration
), recoverable as (
  select
    sm.session_id,
    sm.answer_count,
    sm.total_questions,
    sm.correct_count,
    case
      when sm.total_questions > 0 then round((sm.correct_count::numeric / sm.total_questions::numeric) * 100)
      else 0
    end as recomputed_score,
    (sm.started_at + make_interval(mins => coalesce(sm.duration, 60))) as expected_end
  from session_metrics sm
  where sm.status = 'active'
    and sm.answer_count > 0
    and (
      sm.answer_count >= greatest(sm.total_questions, 1)
      or (sm.started_at + make_interval(mins => coalesce(sm.duration, 60))) <= now()
    )
)
update public.exam_sessions es
set
  status = 'finished',
  finished_at = coalesce(es.finished_at, now()),
  score = r.recomputed_score
from recoverable r
where es.id = r.session_id;


-- 2) Laporan hasil recovery
-- 2a) Sesi yang dipulihkan otomatis
with session_metrics as (
  select
    es.id as session_id,
    es.student_id,
    st.nis,
    es.schedule_id,
    es.status,
    es.score,
    es.started_at,
    es.finished_at,
    count(sa.id) as answer_count
  from public.exam_sessions es
  left join public.student_answers sa on sa.session_id = es.id
  left join public.students st on st.id = es.student_id
  where es.status = 'finished'
    and es.finished_at >= now() - interval '1 hour'
  group by es.id, st.nis
)
select *
from session_metrics
order by finished_at desc;

-- 2b) Kandidat yang masih butuh penanganan manual
-- (active, answer_count = 0, score = 0) -> biasanya retake lebih aman.
select
  es.id as session_id,
  st.nis,
  st.full_name,
  es.schedule_id,
  es.status,
  es.score,
  es.started_at,
  es.violation_count
from public.exam_sessions es
join public.students st on st.id = es.student_id
where es.status = 'active'
  and es.score = 0
  and not exists (
    select 1 from public.student_answers sa where sa.session_id = es.id
  )
order by es.started_at desc
limit 200;

commit;

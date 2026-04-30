-- EMERGENCY: Recompute nilai sesi dari jawaban asli
-- Dipakai saat score di exam_sessions berubah jadi 0 akibat incident update.

begin;

-- 0) Backup cepat sebelum update skor
create table if not exists public._backup_exam_sessions_score_20260413 as
select * from public.exam_sessions where false;

insert into public._backup_exam_sessions_score_20260413
select es.*
from public.exam_sessions es
where not exists (
  select 1
  from public._backup_exam_sessions_score_20260413 b
  where b.id = es.id
);

-- 1) Ambil jawaban terakhir per session + question
with latest_answers as (
  select distinct on (sa.session_id, sa.question_id)
    sa.session_id,
    sa.question_id,
    upper(trim(coalesce(sa.chosen_answer::text, ''))) as chosen_answer
  from public.student_answers sa
  order by sa.session_id, sa.question_id, sa.created_at desc, sa.id desc
),
question_keys as (
  select
    q.id as question_id,
    upper(trim(coalesce(q.correct_answer::text, ''))) as answer_key
  from public.questions q
),
session_question_set as (
  select
    es.id as session_id,
    eq.question_id
  from public.exam_sessions es
  join public.schedules s on s.id = es.schedule_id
  join public.exam_questions eq on eq.exam_id = s.exam_id
),
scoring as (
  select
    sqs.session_id,
    count(distinct sqs.question_id) as total_questions,
    count(*) filter (where la.chosen_answer <> '') as answered_count,
    count(*) filter (
      where la.chosen_answer <> ''
        and la.chosen_answer = qk.answer_key
        and qk.answer_key <> ''
    ) as correct_count
  from session_question_set sqs
  left join latest_answers la
    on la.session_id = sqs.session_id
   and la.question_id = sqs.question_id
  left join question_keys qk
    on qk.question_id = sqs.question_id
  group by sqs.session_id
),
new_scores as (
  select
    s.session_id,
    s.total_questions,
    s.answered_count,
    s.correct_count,
    case
      when s.total_questions > 0
        then round((s.correct_count::numeric / s.total_questions::numeric) * 100)
      else 0
    end as recomputed_score
  from scoring s
),
updated as (
  update public.exam_sessions es
  set score = ns.recomputed_score
  from new_scores ns
  where es.id = ns.session_id
    and ns.answered_count > 0
    and es.status in ('finished', 'active', 'locked')
    and coalesce(es.score, 0) = 0
  returning es.id, es.student_id, es.schedule_id, es.status, es.score
)
select count(*) as updated_rows from updated;

-- 2) Laporan sesi yang masih score=0 padahal punya jawaban
with answer_counts as (
  select sa.session_id, count(*) as answer_count
  from public.student_answers sa
  group by sa.session_id
)
select
  es.id as session_id,
  st.nis,
  st.full_name,
  es.schedule_id,
  es.status,
  es.score,
  ac.answer_count,
  es.started_at,
  es.finished_at
from public.exam_sessions es
join answer_counts ac on ac.session_id = es.id
join public.students st on st.id = es.student_id
where ac.answer_count > 0
  and coalesce(es.score, 0) = 0
order by es.started_at desc
limit 300;

commit;

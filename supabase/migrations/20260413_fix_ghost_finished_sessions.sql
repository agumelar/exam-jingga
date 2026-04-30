-- Hotfix: identifikasi dan perbaikan "ghost finished"
-- Kasus: session berstatus finished tetapi tidak punya jawaban sama sekali.

-- 1) Cek data terdampak (read-only)
select
  es.id,
  es.student_id,
  es.schedule_id,
  es.status,
  es.started_at,
  es.finished_at,
  es.score
from public.exam_sessions es
left join public.student_answers sa on sa.session_id = es.id
where es.status = 'finished'
group by es.id
having count(sa.id) = 0
order by es.finished_at desc nulls last;

-- 2) Perbaikan aman:
--    finished tanpa jawaban -> aktif lagi, score reset, timer mulai ulang.
--    Dibatasi hanya jadwal yang masih active agar tidak mengubah arsip ujian lampau.
update public.exam_sessions es
set
  status = 'active',
  finished_at = null,
  score = 0,
  violation_count = 0,
  started_at = now()
from public.schedules s
where s.id = es.schedule_id
  and s.status = 'active'
  and es.status = 'finished'
  and not exists (
    select 1
    from public.student_answers sa
    where sa.session_id = es.id
  );

-- 3) Verifikasi setelah perbaikan (seharusnya 0 baris untuk jadwal active)
select
  es.id,
  es.student_id,
  es.schedule_id,
  es.status,
  es.started_at,
  es.finished_at,
  es.score
from public.exam_sessions es
join public.schedules s on s.id = es.schedule_id
where s.status = 'active'
  and es.status = 'finished'
  and not exists (
    select 1
    from public.student_answers sa
    where sa.session_id = es.id
  )
order by es.finished_at desc nulls last;

-- ==============================================================================
-- POST-MIGRATION TUNING & OPTIMIZATION SCRIPT - EXAM JINGGA
-- Target Database: PostgreSQL 17 (Self-Hosted Supabase VPS)
-- ==============================================================================

-- 1. STANDARDISASI UUID NATIVE POSTGRES 17
ALTER TABLE IF EXISTS public.settings 
  ALTER COLUMN id SET DEFAULT gen_random_uuid();

ALTER TABLE IF EXISTS public.student_logistics 
  ALTER COLUMN id SET DEFAULT gen_random_uuid();

-- 2. PENAMBAHAN IDENTITAS SSO KEYCLOAK & PEMBERSIHAN DEFAULT VALUES
ALTER TABLE IF EXISTS public.students 
  ADD COLUMN IF NOT EXISTS sso_id uuid UNIQUE,
  ALTER COLUMN status SET DEFAULT 'aktif';

UPDATE public.students 
  SET status = 'aktif' 
  WHERE status = '''aktif''' OR status IS NULL OR status = '';

ALTER TABLE IF EXISTS public.teachers 
  ADD COLUMN IF NOT EXISTS sso_id uuid UNIQUE;

-- 3. INDEKS STRATEGIS UNTUK PERFORMA TINGGI (MITIGASI 400 SISWA SERENTAK)
CREATE INDEX IF NOT EXISTS idx_exam_sessions_sched_stud 
  ON public.exam_sessions(schedule_id, student_id);

CREATE INDEX IF NOT EXISTS idx_exam_sessions_status 
  ON public.exam_sessions(status);

CREATE UNIQUE INDEX IF NOT EXISTS uq_student_answers_session_question 
  ON public.student_answers(session_id, question_id);

CREATE INDEX IF NOT EXISTS idx_student_answers_session_id 
  ON public.student_answers(session_id);

CREATE INDEX IF NOT EXISTS idx_schedules_active_lookup 
  ON public.schedules(status, start_time, end_time);

CREATE INDEX IF NOT EXISTS idx_exam_questions_exam_order 
  ON public.exam_questions(exam_id, order_number);

CREATE INDEX IF NOT EXISTS idx_questions_subject_level 
  ON public.questions(subject_id, level);

CREATE INDEX IF NOT EXISTS idx_students_class 
  ON public.students(class_id);

CREATE INDEX IF NOT EXISTS idx_teacher_assignments_class 
  ON public.teacher_assignments(class_id);

-- 4. SETUP BUCKET STORAGE UNTUK ASET GAMBAR SOAL (CDN)
INSERT INTO storage.buckets (id, name, public)
VALUES ('exam-assets', 'exam-assets', true)
ON CONFLICT (id) DO NOTHING;

-- Policy agar public dapat membaca gambar soal tanpa auth token
CREATE POLICY "Public Access Exam Assets" 
  ON storage.objects FOR SELECT 
  USING (bucket_id = 'exam-assets');

-- 5. ATOMIC RPC FUNCTION: fn_start_student_exam
-- Menggabungkan 6 query serial inisialisasi ujian menjadi 1 roundtrip transaksional
CREATE OR REPLACE FUNCTION public.fn_start_student_exam(
    p_schedule_id uuid,
    p_token text,
    p_student_id uuid
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_schedule record;
    v_exam record;
    v_session record;
    v_now timestamptz := now();
    v_end_time timestamptz;
    v_remaining_seconds integer;
    v_questions jsonb;
    v_saved_answers jsonb;
BEGIN
    -- 1. Validasi Jadwal Ujian & Token
    SELECT s.*, e.duration, e.target_question_count, e.shuffle_questions, e.title as exam_title, e.subject_id, e.type as exam_type
    INTO v_schedule
    FROM public.schedules s
    JOIN public.exams e ON e.id = s.exam_id
    WHERE s.id = p_schedule_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Jadwal ujian tidak ditemukan.';
    END IF;

    IF UPPER(TRIM(v_schedule.token)) <> UPPER(TRIM(p_token)) THEN
        RAISE EXCEPTION 'Token ujian salah.';
    END IF;

    IF v_schedule.status <> 'active' THEN
        RAISE EXCEPTION 'Jadwal ujian ini sedang tidak aktif.';
    END IF;

    IF v_now < v_schedule.start_time OR v_now > v_schedule.end_time THEN
        RAISE EXCEPTION 'Waktu ujian berada di luar jadwal yang ditentukan.';
    END IF;

    -- 2. Ambil atau Buat Sesi Ujian (exam_sessions)
    SELECT * INTO v_session
    FROM public.exam_sessions
    WHERE schedule_id = p_schedule_id AND student_id = p_student_id
    LIMIT 1;

    IF FOUND THEN
        IF v_session.status = 'finished' THEN
            RAISE EXCEPTION 'Anda sudah menyelesaikan ujian ini.';
        END IF;
        IF v_session.status = 'locked' THEN
            RAISE EXCEPTION 'Sesi ujian Anda sedang terkunci. Silakan hubungi pengawas ruang.';
        END IF;
    ELSE
        INSERT INTO public.exam_sessions (student_id, schedule_id, status, started_at, violation_count, score)
        VALUES (p_student_id, p_schedule_id, 'active', v_now, 0, 0)
        RETURNING * INTO v_session;
    END IF;

    -- 3. Hitung Sisa Waktu
    v_end_time := LEAST(v_session.started_at + (v_schedule.duration || ' minutes')::interval, v_schedule.end_time);
    v_remaining_seconds := GREATEST(0, EXTRACT(EPOCH FROM (v_end_time - v_now))::integer);

    -- 4. Ambil Butir Soal (exam_questions + questions)
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', q.id,
            'order_number', eq.order_number,
            'question_text', q.question_text,
            'question_image', q.question_image,
            'option_a', q.option_a,
            'option_b', q.option_b,
            'option_c', q.option_c,
            'option_d', q.option_d,
            'option_e', q.option_e,
            'image_a', q.image_a,
            'image_b', q.image_b,
            'image_c', q.image_c,
            'image_d', q.image_d,
            'image_e', q.image_e
        ) ORDER BY eq.order_number ASC
    )
    INTO v_questions
    FROM public.exam_questions eq
    JOIN public.questions q ON q.id = eq.question_id
    WHERE eq.exam_id = v_schedule.exam_id;

    -- 5. Ambil Jawaban Tersimpan Sebelumnya (Jika Resume Sesi)
    SELECT coalesce(
        jsonb_object_agg(
            sa.question_id::text,
            jsonb_build_object(
                'chosen_answer', sa.chosen_answer,
                'is_doubt', sa.is_doubt
            )
        ),
        '{}'::jsonb
    )
    INTO v_saved_answers
    FROM public.student_answers sa
    WHERE sa.session_id = v_session.id;

    -- Return Payload Lengkap dalam 1 JSON
    RETURN jsonb_build_object(
        'success', true,
        'session_id', v_session.id,
        'schedule_id', v_schedule.id,
        'exam_title', v_schedule.exam_title,
        'duration_minutes', v_schedule.duration,
        'remaining_seconds', v_remaining_seconds,
        'questions', coalesce(v_questions, '[]'::jsonb),
        'saved_answers', v_saved_answers,
        'violation_count', v_session.violation_count,
        'status', v_session.status
    );
END;
$$;

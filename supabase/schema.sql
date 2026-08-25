-- ==============================================================================
-- BASE SCHEMA CREATION - EXAM JINGGA (POSTGRESQL 17)
-- ==============================================================================

-- 1. MAJORS
CREATE TABLE IF NOT EXISTS public.majors (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name character varying NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT majors_pkey PRIMARY KEY (id)
);

-- 2. CLASSES
CREATE TABLE IF NOT EXISTS public.classes (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  major_id uuid,
  name character varying NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT classes_pkey PRIMARY KEY (id),
  CONSTRAINT classes_major_id_fkey FOREIGN KEY (major_id) REFERENCES public.majors(id) ON DELETE SET NULL
);

-- 3. SUBJECTS
CREATE TABLE IF NOT EXISTS public.subjects (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  name character varying NOT NULL,
  CONSTRAINT subjects_pkey PRIMARY KEY (id)
);

-- 4. TEACHERS
CREATE TABLE IF NOT EXISTS public.teachers (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  sso_id uuid UNIQUE,
  full_name text NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  role_level text DEFAULT 'guru'::text CHECK (role_level = ANY (ARRAY['admin'::text, 'kurikulum'::text, 'guru'::text])),
  email text,
  password text DEFAULT 'Jingga123'::text,
  CONSTRAINT teachers_pkey PRIMARY KEY (id)
);

-- 5. STUDENTS
CREATE TABLE IF NOT EXISTS public.students (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid,
  sso_id uuid UNIQUE,
  nis character varying NOT NULL UNIQUE,
  full_name text NOT NULL,
  major_id uuid,
  class_id uuid,
  created_at timestamp with time zone DEFAULT now(),
  status text DEFAULT 'aktif'::text,
  email text,
  password_plain text,
  CONSTRAINT students_pkey PRIMARY KEY (id),
  CONSTRAINT students_major_id_fkey FOREIGN KEY (major_id) REFERENCES public.majors(id) ON DELETE SET NULL,
  CONSTRAINT students_class_id_fkey FOREIGN KEY (class_id) REFERENCES public.classes(id) ON DELETE SET NULL
);

-- 6. TEACHER ASSIGNMENTS
CREATE TABLE IF NOT EXISTS public.teacher_assignments (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  teacher_id uuid,
  subject_id uuid,
  class_id uuid,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT teacher_assignments_pkey PRIMARY KEY (id),
  CONSTRAINT teacher_assignments_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.teachers(id) ON DELETE CASCADE,
  CONSTRAINT teacher_assignments_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id) ON DELETE CASCADE,
  CONSTRAINT teacher_assignments_class_id_fkey FOREIGN KEY (class_id) REFERENCES public.classes(id) ON DELETE CASCADE
);

-- 7. QUESTIONS
CREATE TABLE IF NOT EXISTS public.questions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  question_text text NOT NULL,
  question_image text,
  option_a text NOT NULL,
  option_b text NOT NULL,
  option_c text NOT NULL,
  option_d text NOT NULL,
  option_e text NOT NULL,
  correct_answer character NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  created_by uuid,
  subject_id uuid,
  level integer,
  image_a text,
  image_b text,
  image_c text,
  image_d text,
  image_e text,
  CONSTRAINT questions_pkey PRIMARY KEY (id),
  CONSTRAINT questions_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.teachers(id) ON DELETE SET NULL,
  CONSTRAINT questions_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id) ON DELETE SET NULL
);

-- 8. EXAMS
CREATE TABLE IF NOT EXISTS public.exams (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  teacher_id uuid,
  subject_id uuid,
  title text NOT NULL,
  exam_type text,
  created_at timestamp with time zone DEFAULT now(),
  duration integer DEFAULT 60,
  target_question_count integer DEFAULT 40,
  level integer,
  status text DEFAULT 'pending_selection'::text,
  shuffle_questions boolean DEFAULT true,
  start_time timestamp with time zone,
  token text,
  type text DEFAULT 'UH'::text,
  CONSTRAINT exams_pkey PRIMARY KEY (id),
  CONSTRAINT exams_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.teachers(id) ON DELETE SET NULL,
  CONSTRAINT exams_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES public.subjects(id) ON DELETE SET NULL
);

-- 9. EXAM QUESTIONS
CREATE TABLE IF NOT EXISTS public.exam_questions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  exam_id uuid,
  question_id uuid,
  order_number integer,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT exam_questions_pkey PRIMARY KEY (id),
  CONSTRAINT exam_questions_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exams(id) ON DELETE CASCADE,
  CONSTRAINT exam_questions_question_id_fkey FOREIGN KEY (question_id) REFERENCES public.questions(id) ON DELETE CASCADE
);

-- 10. SCHEDULES
CREATE TABLE IF NOT EXISTS public.schedules (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  exam_id uuid,
  class_id uuid,
  teacher_id uuid,
  start_time timestamp with time zone NOT NULL,
  end_time timestamp with time zone NOT NULL,
  token character varying NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  session_no integer DEFAULT 1,
  room_name text,
  status text DEFAULT 'active'::text,
  teacher_quota integer DEFAULT 0,
  CONSTRAINT schedules_pkey PRIMARY KEY (id),
  CONSTRAINT schedules_exam_id_fkey FOREIGN KEY (exam_id) REFERENCES public.exams(id) ON DELETE CASCADE,
  CONSTRAINT schedules_class_id_fkey FOREIGN KEY (class_id) REFERENCES public.classes(id) ON DELETE CASCADE,
  CONSTRAINT schedules_teacher_id_fkey FOREIGN KEY (teacher_id) REFERENCES public.teachers(id) ON DELETE SET NULL
);

-- 11. EXAM SESSIONS
CREATE TABLE IF NOT EXISTS public.exam_sessions (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  student_id uuid,
  schedule_id uuid,
  status text DEFAULT 'active'::text CHECK (status = ANY (ARRAY['active'::text, 'locked'::text, 'finished'::text])),
  violation_count integer DEFAULT 0,
  score double precision DEFAULT 0,
  started_at timestamp with time zone DEFAULT now(),
  finished_at timestamp with time zone,
  CONSTRAINT exam_sessions_pkey PRIMARY KEY (id),
  CONSTRAINT exam_sessions_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE CASCADE,
  CONSTRAINT exam_sessions_schedule_id_fkey FOREIGN KEY (schedule_id) REFERENCES public.schedules(id) ON DELETE CASCADE
);

-- 12. STUDENT ANSWERS
CREATE TABLE IF NOT EXISTS public.student_answers (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  session_id uuid,
  question_id uuid,
  chosen_answer character,
  is_correct boolean,
  created_at timestamp with time zone DEFAULT now(),
  is_doubt boolean DEFAULT false,
  CONSTRAINT student_answers_pkey PRIMARY KEY (id),
  CONSTRAINT student_answers_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.exam_sessions(id) ON DELETE CASCADE
);

-- 13. STUDENT LOGISTICS
CREATE TABLE IF NOT EXISTS public.student_logistics (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  student_id uuid,
  room_name text,
  session_name text,
  exam_period text,
  created_at timestamp with time zone DEFAULT now(),
  CONSTRAINT student_logistics_pkey PRIMARY KEY (id),
  CONSTRAINT student_logistics_student_id_fkey FOREIGN KEY (student_id) REFERENCES public.students(id) ON DELETE CASCADE
);

-- 14. SETTINGS
CREATE TABLE IF NOT EXISTS public.settings (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  school_name text DEFAULT 'SMK NEGERI 1 RONGGA'::text,
  school_address text,
  academic_year text DEFAULT '2025/2026'::text,
  semester text DEFAULT 'Ganjil'::text,
  exam_name text DEFAULT 'Penilaian Akhir Semester (PAS)'::text,
  headmaster_name text,
  headmaster_nip text,
  committee_chairman text,
  updated_at timestamp with time zone DEFAULT now(),
  logo_left_url text,
  logo_right_url text,
  watermark_url text,
  school_seal_url text,
  headmaster_signature_url text,
  curriculum_signature_url text,
  curriculum_vicedir_name text,
  curriculum_vicedir_nip text,
  exam_city text DEFAULT 'Rongga'::text,
  school_majors_list text,
  school_website text,
  school_email text,
  header_1 text,
  header_2 text,
  header_3 text,
  school_phone text,
  school_postal_code text,
  exam_date text,
  CONSTRAINT settings_pkey PRIMARY KEY (id)
);

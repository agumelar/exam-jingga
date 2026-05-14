import { mapScheduleCardItem } from '../utils/index.js';

const EXAM_ID_CHUNK_SIZE = 30;
const PAGE_SIZE = 1000;

export async function fetchAssignments(supabase) {
  return supabase
    .from('teacher_assignments')
    .select(
      'subject_id, teacher_id, subjects(id, name), classes(id, name), teachers(id, full_name)'
    );
}

export async function fetchSchedulesWithRelations(supabase) {
  return supabase
    .from('schedules')
    .select('*, exams(*, subjects(name)), teachers(full_name), classes(name)')
    .order('created_at', { ascending: false });
}

export async function fetchExamQuestionsWithAuthor(supabase, examIds = []) {
  if (!Array.isArray(examIds) || examIds.length === 0) {
    return { data: [] };
  }

  const uniqueExamIds = Array.from(new Set(examIds)).filter(Boolean);
  if (uniqueExamIds.length === 0) {
    return { data: [] };
  }

  const collected = [];

  for (let i = 0; i < uniqueExamIds.length; i += EXAM_ID_CHUNK_SIZE) {
    const chunk = uniqueExamIds.slice(i, i + EXAM_ID_CHUNK_SIZE);
    let from = 0;

    while (true) {
      const query = supabase
        .from('exam_questions')
        .select('exam_id, questions!inner(created_by)')
        .in('exam_id', chunk)
        .order('id', { ascending: true });

      const { data, error } = await query.range(from, from + PAGE_SIZE - 1);

      if (error) {
        return { data: collected, error };
      }

      if (!data || data.length === 0) {
        break;
      }

      collected.push(...data);

      if (data.length < PAGE_SIZE) {
        break;
      }

      from += PAGE_SIZE;
    }
  }

  return { data: collected };
}

export function mapScheduleCards(schedules, allQuestions) {
  return (schedules || []).map((schedule) =>
    mapScheduleCardItem(schedule, allQuestions)
  );
}

export async function verifyExamStatus(supabase, examId) {
  return supabase.from('exams').update({ status: 'validated' }).eq('id', examId);
}

export async function unlockUHExam(supabase, examId) {
  return supabase
    .from('exams')
    .update({ status: 'pending_selection' })
    .eq('id', examId);
}

export async function findScheduleById(supabase, scheduleId) {
  return supabase
    .from('schedules')
    .select('id, exam_id, teacher_id')
    .eq('id', scheduleId)
    .single();
}

export async function updateExamById(supabase, examId, payload) {
  return supabase.from('exams').update(payload).eq('id', examId);
}

export async function getSchedulesByExamId(supabase, examId) {
  return supabase
    .from('schedules')
    .select('id, teacher_id')
    .eq('exam_id', examId);
}

export async function updateScheduleById(supabase, scheduleId, payload) {
  return supabase.from('schedules').update(payload).eq('id', scheduleId);
}

export async function deleteScheduleById(supabase, scheduleId) {
  return supabase.from('schedules').delete().eq('id', scheduleId);
}

export async function fetchAllScheduleIds(supabase) {
  const { data, error } = await supabase.from('schedules').select('id');
  if (error) {
    return { data: [], error };
  }
  return { data: (data || []).map((row) => row.id) };
}

export async function createExam(supabase, payload) {
  return supabase.from('exams').insert([payload]).select().single();
}

export async function fetchScheduleDetailById(supabase, scheduleId) {
  return supabase
    .from('schedules')
    .select('*, exams(*, subjects(name))')
    .eq('id', scheduleId)
    .single();
}

export async function fetchQuestionBankByTeacher(
  supabase,
  { subjectId, level, teacherId }
) {
  return supabase
    .from('questions')
    .select('*')
    .eq('subject_id', subjectId)
    .eq('level', level)
    .eq('created_by', teacherId);
}

export async function fetchExamQuestionLinksByExamId(supabase, examId) {
  return supabase
    .from('exam_questions')
    .select('question_id, questions(created_by)')
    .eq('exam_id', examId);
}

export async function fetchOwnExamQuestionLinks(supabase, { examId, teacherId }) {
  return supabase
    .from('exam_questions')
    .select('id, questions!inner(created_by)')
    .eq('exam_id', examId)
    .eq('questions.created_by', teacherId);
}

export async function deleteExamQuestionsByIds(supabase, ids) {
  return supabase.from('exam_questions').delete().in('id', ids);
}

export async function insertExamQuestionLinks(supabase, rows) {
  return supabase.from('exam_questions').insert(rows);
}

export async function insertSchedules(supabase, payloadList) {
  return supabase.from('schedules').insert(payloadList);
}

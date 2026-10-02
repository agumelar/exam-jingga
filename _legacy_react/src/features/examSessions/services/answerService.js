import { supabase } from '../../../supabaseClient.js';

export async function fetchSessionAnswers(sessionId) {
  if (typeof sessionId !== 'string' || sessionId.trim() === '') {
    return { data: null, error: new Error('sessionId required') };
  }
  return supabase
    .from('student_answers')
    .select('question_id, chosen_answer, is_doubt, created_at')
    .eq('session_id', sessionId);
}

export async function upsertSessionAnswers(sessionId, rows) {
  if (typeof sessionId !== 'string' || sessionId.trim() === '') {
    return { data: null, error: new Error('sessionId required') };
  }
  const safeRows = (rows || []).filter(r => (
    r &&
    typeof r.questionId === 'string' &&
    r.questionId.trim() !== '' &&
    typeof r.choice === 'string' &&
    r.choice.trim() !== ''
  ));
  if (!safeRows || safeRows.length === 0) return { data: [], error: null };
  return supabase
    .from('student_answers')
    .upsert(
      safeRows.map(r => ({
        session_id: sessionId,
        question_id: r.questionId,
        chosen_answer: r.choice,
        is_doubt: r.isDoubt,
      })),
      { onConflict: 'session_id, question_id' }
    );
}

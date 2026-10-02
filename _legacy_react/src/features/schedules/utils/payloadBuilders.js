export function resolveExamTitle({ type, title, subType }) {
  if (type === 'SAJ') return 'Asesmen Sumatif Akhir Jenjang';
  if (type === 'PTS' || type === 'PAS/PAT') return subType;
  return title;
}

export function buildExamPayload({
  type,
  title,
  subType,
  duration,
  targetQuestionCount,
  level,
  subjectId,
  teacherId,
  token,
}) {
  return {
    title: resolveExamTitle({ type, title, subType }),
    subject_id: subjectId,
    type,
    level: Number(level),
    teacher_id: teacherId,
    duration: Number(duration),
    target_question_count: Number(targetQuestionCount),
    token,
    status: 'pending_selection',
  };
}

export function attachTeacherProgress(schedules = []) {
  const byExam = new Map();

  schedules.forEach((schedule) => {
    const examId = schedule.exam_id;
    if (!examId) return;
    if (!byExam.has(examId)) byExam.set(examId, []);

    const quota =
      schedule.teacher_quota ?? schedule.exams?.target_question_count ?? 0;
    const filled = schedule.my_question_count ?? 0;

    byExam.get(examId).push({
      teacher_id: schedule.teacher_id,
      name: schedule.teachers?.full_name || 'Guru',
      filled,
      quota,
    });
  });

  return schedules.map((schedule) => ({
    ...schedule,
    teacher_progress_list: byExam.get(schedule.exam_id) || [],
  }));
}

export function getCollabProgressList(progressList = [], teacherId) {
  if (!teacherId) return progressList;
  return progressList.filter((item) => item.teacher_id !== teacherId);
}

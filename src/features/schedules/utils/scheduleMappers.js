import { addMinutesToLocalDateTime, normalizeLocalDateTime } from './dateTime.js';

export function mapScheduleCardItem(schedule, allQuestions = []) {
  const teacherQuestionCount =
    allQuestions?.filter(
      (item) =>
        item.exam_id === schedule.exam_id &&
        item.questions?.created_by === schedule.teacher_id
    ).length || 0;

  return {
    ...schedule,
    start_time: normalizeLocalDateTime(schedule.start_time),
    end_time: normalizeLocalDateTime(schedule.end_time),
    my_question_count: teacherQuestionCount,
    cluster_classes_text: `GABUNGAN KELAS ${schedule.exams?.level}`,
  };
}

export function buildScheduleDateRange({ startTime, duration }) {
  return {
    finalStart: normalizeLocalDateTime(startTime),
    finalEnd: addMinutesToLocalDateTime(startTime, duration),
  };
}

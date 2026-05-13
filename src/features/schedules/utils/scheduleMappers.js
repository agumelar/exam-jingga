import { toSQLDateTime } from './dateTime.js';

export function mapScheduleCardItem(schedule, allQuestions = []) {
  const teacherQuestionCount =
    allQuestions?.filter(
      (item) =>
        item.exam_id === schedule.exam_id &&
        item.questions?.created_by === schedule.teacher_id
    ).length || 0;

  return {
    ...schedule,
    start_time: schedule.start_time
      ? schedule.start_time.split('+')[0].replace('T', ' ')
      : null,
    end_time: schedule.end_time
      ? schedule.end_time.split('+')[0].replace('T', ' ')
      : null,
    my_question_count: teacherQuestionCount,
    cluster_classes_text: `GABUNGAN KELAS ${schedule.exams?.level}`,
  };
}

export function buildScheduleDateRange({ startTime, duration }) {
  const startObject = new Date(startTime);
  const endObject = new Date(startObject.getTime() + Number(duration) * 60000);

  return {
    finalStart: toSQLDateTime(startObject),
    finalEnd: toSQLDateTime(endObject),
  };
}

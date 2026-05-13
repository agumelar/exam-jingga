import test from 'node:test';
import assert from 'node:assert/strict';
import {
  attachTeacherProgress,
  getCollabProgressList,
} from './scheduleProgress.js';

test('attachTeacherProgress builds progress list per exam', () => {
  const schedules = [
    {
      exam_id: 'exam-1',
      teacher_id: 't-1',
      teachers: { full_name: 'Beni' },
      my_question_count: 10,
      teacher_quota: 20,
      exams: { target_question_count: 40 },
    },
    {
      exam_id: 'exam-1',
      teacher_id: 't-2',
      teachers: { full_name: 'Cece' },
      my_question_count: 15,
      teacher_quota: 20,
      exams: { target_question_count: 40 },
    },
    {
      exam_id: 'exam-2',
      teacher_id: 't-3',
      teachers: { full_name: 'Dodi' },
      my_question_count: 5,
      teacher_quota: 10,
      exams: { target_question_count: 10 },
    },
  ];

  const result = attachTeacherProgress(schedules);
  const exam1 = result.find((item) => item.exam_id === 'exam-1');
  const exam2 = result.find((item) => item.exam_id === 'exam-2');

  assert.equal(exam1.teacher_progress_list.length, 2);
  assert.ok(
    exam1.teacher_progress_list.some(
      (t) => t.teacher_id === 't-1' && t.filled === 10 && t.quota === 20
    )
  );
  assert.ok(
    exam1.teacher_progress_list.some(
      (t) => t.teacher_id === 't-2' && t.filled === 15 && t.quota === 20
    )
  );

  assert.equal(exam2.teacher_progress_list.length, 1);
  assert.equal(exam2.teacher_progress_list[0].name, 'Dodi');
  assert.equal(exam2.teacher_progress_list[0].filled, 5);
  assert.equal(exam2.teacher_progress_list[0].quota, 10);
});

test('getCollabProgressList excludes current teacher', () => {
  const progressList = [
    { teacher_id: 't-1', name: 'A', filled: 2, quota: 2 },
    { teacher_id: 't-2', name: 'B', filled: 0, quota: 2 },
  ];

  const result = getCollabProgressList(progressList, 't-1');

  assert.equal(result.length, 1);
  assert.equal(result[0].teacher_id, 't-2');
});

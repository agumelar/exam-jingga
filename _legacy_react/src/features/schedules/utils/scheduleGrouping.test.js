import test from 'node:test';
import assert from 'node:assert/strict';
import { buildTeacherSetGroups } from './scheduleGrouping.js';

test('buildTeacherSetGroups groups classes by sorted teacher set', () => {
  const assignments = [
    { teacher_id: 't1', class_id: 'c-a' },
    { teacher_id: 't1', class_id: 'c-b' },
    { teacher_id: 't2', class_id: 'c-b' },
    { teacher_id: 't3', class_id: 'c-c' },
    { teacher_id: 't2', class_id: 'c-c' },
    { teacher_id: 't3', class_id: 'c-c' },
  ];

  const groups = buildTeacherSetGroups(assignments);

  assert.equal(groups.length, 3);

  const solo = groups.find((g) => g.teacherSet.join(',') === 't1');
  assert.deepEqual(solo.classIds.sort(), ['c-a']);

  const pair = groups.find((g) => g.teacherSet.join(',') === 't1,t2');
  assert.deepEqual(pair.classIds.sort(), ['c-b']);

  const triple = groups.find((g) => g.teacherSet.join(',') === 't2,t3');
  assert.deepEqual(triple.classIds.sort(), ['c-c']);
});

test('buildTeacherSetGroups returns empty array for empty input', () => {
  assert.deepEqual(buildTeacherSetGroups([]), []);
});

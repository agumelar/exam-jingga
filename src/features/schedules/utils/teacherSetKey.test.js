import test from 'node:test';
import assert from 'node:assert/strict';
import { buildTeacherSetKey } from './teacherSetKey.js';

test('buildTeacherSetKey sorts and de-duplicates teacher ids', () => {
  const result = buildTeacherSetKey(['t2', 't1', 't1', 't3']);
  assert.equal(result, 't1|t2|t3');
});

test('buildTeacherSetKey returns empty string for empty input', () => {
  assert.equal(buildTeacherSetKey([]), '');
});

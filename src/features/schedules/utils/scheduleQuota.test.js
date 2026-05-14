import test from 'node:test';
import assert from 'node:assert/strict';
import { buildTeacherQuotaMap } from './scheduleQuota.js';

test('buildTeacherQuotaMap uses max teacher count per class with deterministic remainder', () => {
  const assignments = [
    { teacher_id: 't1', classes: { id: 'c-a', name: '10 RPL 1' } },
    { teacher_id: 't2', classes: { id: 'c-a', name: '10 RPL 1' } },
    { teacher_id: 't3', classes: { id: 'c-a', name: '10 RPL 1' } },
    { teacher_id: 't1', classes: { id: 'c-b', name: '10 RPL 2' } },
    { teacher_id: 't9', classes: { id: 'c-c', name: '10 TSM 1' } },
  ];

  const result = buildTeacherQuotaMap(assignments, 10);

  assert.equal(result.t1, 4);
  assert.equal(result.t2, 3);
  assert.equal(result.t3, 3);
  assert.equal(result.t9, 10);
});

test('buildTeacherQuotaMap returns empty map for empty input', () => {
  assert.deepEqual(buildTeacherQuotaMap([], 10), {});
});

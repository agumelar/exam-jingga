import test from 'node:test';
import assert from 'node:assert/strict';
import { buildScheduleDateRange } from './scheduleMappers.js';

test('buildScheduleDateRange returns SQL start/end', () => {
  const { finalStart, finalEnd } = buildScheduleDateRange({
    startTime: '2026-05-30T08:15',
    duration: 45,
  });

  assert.equal(finalStart, '2026-05-30 08:15:00');
  assert.equal(finalEnd, '2026-05-30 09:00:00');
});

import test from 'node:test';
import assert from 'node:assert/strict';
import { formatWIB, toSQLDateTime } from './dateTime.js';

test('formatWIB returns short Indonesian date', () => {
  assert.equal(formatWIB('2026-05-01 07:30:00'), '01 Mei 2026, 07:30');
});

test('toSQLDateTime converts Date object to SQL text', () => {
  const date = new Date('2026-05-01T07:30:00');
  assert.match(toSQLDateTime(date), /^2026-05-01 07:30:00$/);
});

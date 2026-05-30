import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatWIB,
  toSQLDateTime,
  parseLocalDateTime,
  normalizeLocalDateTime,
  addMinutesToLocalDateTime,
  toLocalDateKey,
  isWithinLocalRange,
} from './dateTime.js';

test('formatWIB returns short Indonesian date', () => {
  assert.equal(formatWIB('2026-05-01 07:30:00'), '01 Mei 2026, 07:30');
});

test('toSQLDateTime converts Date object to SQL text', () => {
  const date = new Date('2026-05-01T07:30:00');
  assert.match(toSQLDateTime(date), /^2026-05-01 07:30:00$/);
});

test('parseLocalDateTime parses datetime-local string', () => {
  const parsed = parseLocalDateTime('2026-05-30T08:15');
  assert.equal(parsed.getFullYear(), 2026);
  assert.equal(parsed.getMonth(), 4);
  assert.equal(parsed.getDate(), 30);
  assert.equal(parsed.getHours(), 8);
  assert.equal(parsed.getMinutes(), 15);
});

test('normalizeLocalDateTime outputs SQL format', () => {
  assert.equal(
    normalizeLocalDateTime('2026-05-30T08:15'),
    '2026-05-30 08:15:00'
  );
});

test('addMinutesToLocalDateTime adds duration in minutes', () => {
  assert.equal(
    addMinutesToLocalDateTime('2026-05-30T08:15', 45),
    '2026-05-30 09:00:00'
  );
});

test('toLocalDateKey formats date key', () => {
  const date = new Date(2026, 4, 30, 8, 15, 0);
  assert.equal(toLocalDateKey(date), '2026-05-30');
});

test('isWithinLocalRange checks now within start/end', () => {
  const now = new Date(2026, 4, 30, 8, 30, 0);
  assert.equal(
    isWithinLocalRange({
      now,
      startTime: '2026-05-30 08:00:00',
      endTime: '2026-05-30 09:00:00',
    }),
    true
  );
  assert.equal(
    isWithinLocalRange({
      now: new Date(2026, 4, 30, 9, 1, 0),
      startTime: '2026-05-30 08:00:00',
      endTime: '2026-05-30 09:00:00',
    }),
    false
  );
});

import test from 'node:test';
import assert from 'node:assert/strict';
import { buildExamPayload } from './payloadBuilders.js';

test('SAJ title forced to Asesmen Sumatif Akhir Jenjang', () => {
  const payload = buildExamPayload({
    type: 'SAJ',
    title: 'x',
    subType: '',
    duration: 90,
    targetQuestionCount: 40,
    level: 12,
    subjectId: 9,
    teacherId: 1,
    token: 'ABC123',
  });

  assert.equal(payload.title, 'Asesmen Sumatif Akhir Jenjang');
});

test('PTS title uses selected semester subtype', () => {
  const payload = buildExamPayload({
    type: 'PTS',
    title: '',
    subType: 'PTS Ganjil',
    duration: 90,
    targetQuestionCount: 40,
    level: 11,
    subjectId: 9,
    teacherId: 1,
    token: 'ABC123',
  });

  assert.equal(payload.title, 'PTS Ganjil');
});

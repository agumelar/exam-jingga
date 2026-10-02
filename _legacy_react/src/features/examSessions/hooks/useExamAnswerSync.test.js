import test from 'node:test';
import assert from 'node:assert/strict';

process.env.VITE_SUPABASE_URL = 'http://localhost:54321';
process.env.VITE_SUPABASE_ANON_KEY = 'test-key';

const loadModule = () => import('./useExamAnswerSync.js');

test('mergeAnswers prefers cache over db for same question', async () => {
  const { mergeAnswers } = await loadModule();
  const db = [{ question_id: 'q1', chosen_answer: 'b', is_doubt: false }];
  const cache = { answers: { q1: { choice: 'a', isDoubt: true } } };
  const result = mergeAnswers(db, cache);
  assert.deepEqual(result.answers, { q1: 'A' });
  assert.deepEqual(result.doubts, ['q1']);
});

test('mergeAnswers normalizes numeric ids', async () => {
  const { mergeAnswers } = await loadModule();
  const db = [{ question_id: 1, chosen_answer: 'c', is_doubt: true }];
  const cache = { answers: { '1': { choice: 'd', isDoubt: false } } };
  const result = mergeAnswers(db, cache);
  assert.deepEqual(result.answers, { '1': 'D' });
  assert.deepEqual(result.doubts, ['1']);
});

test('mergeAnswers keeps falsy numeric answers', async () => {
  const { mergeAnswers } = await loadModule();
  const db = [{ question_id: 2, chosen_answer: 0, is_doubt: false }];
  const cache = { answers: { '2': { choice: 0, isDoubt: true } } };
  const result = mergeAnswers(db, cache);
  assert.deepEqual(result.answers, { '2': '0' });
  assert.deepEqual(result.doubts, ['2']);
});

test('loadMergedAnswers falls back to cache when fetch throws', async () => {
  const { loadMergedAnswers } = await loadModule();
  const cache = { answers: { q2: { choice: 'b', isDoubt: true } } };
  const result = await loadMergedAnswers({
    sessionId: 'sess-1',
    fetchFn: async () => { throw new Error('boom'); },
    readCache: () => cache,
  });
  assert.deepEqual(result.answers, { q2: 'B' });
  assert.deepEqual(result.doubts, ['q2']);
});

test('buildCachePayload includes doubts', async () => {
  const { buildCachePayload } = await loadModule();
  const payload = buildCachePayload({
    answers: { q1: 'A', q2: 'B' },
    doubts: ['q2'],
    now: 123,
  });
  assert.equal(payload.version, 1);
  assert.equal(payload.updatedAt, 123);
  assert.equal(payload.doubts, undefined);
  assert.deepEqual(payload.answers.q1.isDoubt, false);
  assert.deepEqual(payload.answers.q2.isDoubt, true);
});

test('runFlush resets flushing and clears queue on success', async () => {
  const { runFlush } = await loadModule();
  const queue = new Map([
    ['q1', { questionId: 'q1', choice: 'A', isDoubt: false }],
  ]);
  const calls = [];
  const result = await runFlush({
    sessionId: 'sess-1',
    isLocked: false,
    queue,
    upsertFn: async () => ({ data: [], error: null }),
    writeCache: () => { calls.push('write'); },
    snapshot: { version: 1, updatedAt: 1, answers: {} },
    setFlushing: (v) => { calls.push(v ? 'start' : 'end'); },
  });
  assert.equal(queue.size, 0);
  assert.deepEqual(calls, ['start', 'write', 'end']);
  assert.deepEqual(result.data, []);
  assert.equal(result.error, null);
});

test('runFlush resets flushing on error', async () => {
  const { runFlush } = await loadModule();
  const queue = new Map([
    ['q1', { questionId: 'q1', choice: 'A', isDoubt: false }],
  ]);
  const calls = [];
  const result = await runFlush({
    sessionId: 'sess-1',
    isLocked: false,
    queue,
    upsertFn: async () => { throw new Error('fail'); },
    writeCache: () => { calls.push('write'); },
    snapshot: { version: 1, updatedAt: 1, answers: {} },
    setFlushing: (v) => { calls.push(v ? 'start' : 'end'); },
  });
  assert.equal(queue.size, 1);
  assert.deepEqual(calls, ['start', 'end']);
  assert.equal(result.data, null);
  assert.equal(result?.error?.message, 'fail');
});

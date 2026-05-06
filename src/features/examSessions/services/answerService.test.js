import test from 'node:test';
import assert from 'node:assert/strict';

process.env.VITE_SUPABASE_URL = 'http://localhost:54321';
process.env.VITE_SUPABASE_ANON_KEY = 'test-key';

test('answerService exports expected functions', async () => {
  const mod = await import('./answerService.js');
  assert.equal(typeof mod.fetchSessionAnswers, 'function');
  assert.equal(typeof mod.upsertSessionAnswers, 'function');
});

test('fetchSessionAnswers returns error when sessionId missing', async () => {
  const mod = await import('./answerService.js');
  const { supabase } = await import('../../../supabaseClient.js');
  const originalFrom = supabase.from;
  let called = false;
  supabase.from = () => { called = true; throw new Error('should not call'); };
  const result = await mod.fetchSessionAnswers('');
  assert.equal(called, false);
  assert.equal(result?.error?.message, 'sessionId required');
  supabase.from = originalFrom;
});

test('fetchSessionAnswers returns error when sessionId blank', async () => {
  const mod = await import('./answerService.js');
  const { supabase } = await import('../../../supabaseClient.js');
  const originalFrom = supabase.from;
  let called = false;
  supabase.from = () => { called = true; throw new Error('should not call'); };
  const result = await mod.fetchSessionAnswers('   ');
  assert.equal(called, false);
  assert.equal(result?.error?.message, 'sessionId required');
  supabase.from = originalFrom;
});

test('upsertSessionAnswers ignores invalid rows', async () => {
  const mod = await import('./answerService.js');
  const { supabase } = await import('../../../supabaseClient.js');
  const originalFrom = supabase.from;
  let called = false;
  supabase.from = () => { called = true; throw new Error('should not call'); };
  const result = await mod.upsertSessionAnswers('sess-1', [{}, null]);
  assert.equal(called, false);
  assert.deepEqual(result, { data: [], error: null });
  supabase.from = originalFrom;
});

test('upsertSessionAnswers ignores blank questionId or choice', async () => {
  const mod = await import('./answerService.js');
  const { supabase } = await import('../../../supabaseClient.js');
  const originalFrom = supabase.from;
  let called = false;
  supabase.from = () => { called = true; throw new Error('should not call'); };
  const result = await mod.upsertSessionAnswers('sess-1', [
    { questionId: '   ', choice: 'A' },
    { questionId: 'q1', choice: '   ' },
  ]);
  assert.equal(called, false);
  assert.deepEqual(result, { data: [], error: null });
  supabase.from = originalFrom;
});

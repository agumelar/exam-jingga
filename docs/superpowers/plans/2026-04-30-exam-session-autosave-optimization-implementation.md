# Exam Session Autosave Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menjamin jawaban ujian tidak hilang saat refresh/reload melalui autosave batch + cache lokal + upsert idempotent di Supabase free tier.

**Architecture:** Gunakan DB sebagai source of truth dengan unique constraint agar upsert stabil. Tambahkan cache lokal untuk menahan jawaban saat refresh/offline, lalu gunakan hook autosave yang melakukan batch flush + retry. Integrasi di `ExamInterface` tanpa mengubah alur ujian/anti-cheat.

**Tech Stack:** React 19, Supabase JS 2, localStorage, Node built-in test runner (`node:test`).

---

## Target Struktur File

### Create
- `src/features/examSessions/services/answerService.js`
- `src/features/examSessions/services/answerService.test.js`
- `src/features/examSessions/utils/answerCache.js`
- `src/features/examSessions/hooks/useExamAnswerSync.js`
- `src/features/examSessions/index.js`
- `src/features/examSessions/utils/answerCache.test.js`
- `src/features/examSessions/hooks/useExamAnswerSync.test.js`
- `src/supabaseClient.test.js`

### Modify
- `src/pages/ExamInterface.jsx`
- `src/supabaseClient.js`
- `DB.md` (document constraint/index yang dibutuhkan)

### Database (manual SQL)
- `ALTER TABLE public.student_answers ADD CONSTRAINT student_answers_session_question_unique UNIQUE (session_id, question_id);`
- `CREATE INDEX IF NOT EXISTS student_answers_session_id_idx ON public.student_answers (session_id);`

---

### Task 1: Cache Lokal untuk Jawaban

**Files:**
- Create: `src/features/examSessions/utils/answerCache.js`
- Create: `src/features/examSessions/utils/answerCache.test.js`

- [ ] **Step 1: Write failing tests for cache read/write/clear**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { readLocal, writeLocal, clearLocal } from './answerCache.js';

const store = new Map();
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => { store.set(k, String(v)); },
  removeItem: (k) => { store.delete(k); },
  clear: () => { store.clear(); },
};

test('writeLocal then readLocal returns persisted payload', () => {
  localStorage.clear();
  const sessionId = 'sess-1';
  const payload = {
    version: 1,
    updatedAt: 1710000000000,
    answers: {
      q1: { choice: 'A', isDoubt: false, updatedAt: 1710000000000 }
    }
  };
  writeLocal(sessionId, payload);
  assert.deepEqual(readLocal(sessionId), payload);
});

test('clearLocal removes payload', () => {
  localStorage.clear();
  const sessionId = 'sess-2';
  writeLocal(sessionId, { version: 1, updatedAt: 1, answers: {} });
  clearLocal(sessionId);
  assert.equal(readLocal(sessionId), null);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test src/features/examSessions/utils/answerCache.test.js`

Expected: FAIL with module not found.

- [ ] **Step 3: Implement cache utility**

```js
const PREFIX = 'exam_answers_cache:';

const safeParse = (value) => {
  if (!value) return null;
  try { return JSON.parse(value); } catch { return null; }
};

export function readLocal(sessionId) {
  if (!sessionId) return null;
  const raw = localStorage.getItem(`${PREFIX}${sessionId}`);
  return safeParse(raw);
}

export function writeLocal(sessionId, payload) {
  if (!sessionId) return;
  localStorage.setItem(`${PREFIX}${sessionId}`, JSON.stringify(payload));
}

export function clearLocal(sessionId) {
  if (!sessionId) return;
  localStorage.removeItem(`${PREFIX}${sessionId}`);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test src/features/examSessions/utils/answerCache.test.js`

Expected: PASS all tests.

- [ ] **Step 5: Commit**

```bash
git add src/features/examSessions/utils/answerCache.js src/features/examSessions/utils/answerCache.test.js
git commit -m "feat(exam-session): add local answer cache utilities"
```

---

### Task 2: Service Layer untuk Jawaban

**Files:**
- Create: `src/features/examSessions/services/answerService.js`
- Create: `src/features/examSessions/services/answerService.test.js`
- Modify: `src/supabaseClient.js`

- [ ] **Step 1: Write failing test for module exports**

```js
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test src/features/examSessions/services/answerService.test.js`

Expected: FAIL with module not found.

- [ ] **Step 3: Make supabaseClient safe for Node tests**
- [ ] **Step 3: Make supabaseClient safe for Node tests + missing env guard**

```js
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env?.VITE_SUPABASE_URL ?? process.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env?.VITE_SUPABASE_ANON_KEY ?? process.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing Supabase env: VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY')
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

- [ ] **Step 4: Implement service functions**

```js
import { supabase } from '../../../supabaseClient.js';

export async function fetchSessionAnswers(sessionId) {
  if (typeof sessionId !== 'string' || sessionId.trim() === '') {
    return { data: null, error: new Error('sessionId required') };
  }
  return supabase
    .from('student_answers')
    .select('question_id, chosen_answer, is_doubt, created_at')
    .eq('session_id', sessionId);
}

export async function upsertSessionAnswers(sessionId, rows) {
  if (typeof sessionId !== 'string' || sessionId.trim() === '') {
    return { data: null, error: new Error('sessionId required') };
  }
  const safeRows = (rows || []).filter(r => (
    r &&
    typeof r.questionId === 'string' &&
    r.questionId.trim() !== '' &&
    typeof r.choice === 'string' &&
    r.choice.trim() !== ''
  ));
  if (!safeRows || safeRows.length === 0) return { data: [], error: null };
  return supabase
    .from('student_answers')
    .upsert(
      safeRows.map(r => ({
        session_id: sessionId,
        question_id: r.questionId,
        chosen_answer: r.choice,
        is_doubt: r.isDoubt,
      })),
      { onConflict: 'session_id, question_id' }
    );
}
```

- [ ] **Step 5: Add test for missing env in supabaseClient**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';

test('supabaseClient throws when env missing', () => {
  const result = spawnSync(process.execPath, ['-e', "import('./src/supabaseClient.js')"], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      VITE_SUPABASE_URL: '',
      VITE_SUPABASE_ANON_KEY: '',
    },
    encoding: 'utf-8',
  });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Missing Supabase env/);
});
```

- [ ] **Step 6: Run tests to verify they pass**

Run:
- `node --test src/features/examSessions/services/answerService.test.js`
- `node --test src/supabaseClient.test.js`

Expected: PASS all tests.

- [ ] **Step 7: Commit**

```bash
git add src/features/examSessions/services/answerService.js
git commit -m "feat(exam-session): add answer service for fetch and batch upsert"
```

---

### Task 3: Hook Autosave + Rehydrate

**Files:**
- Create: `src/features/examSessions/hooks/useExamAnswerSync.js`
- Create: `src/features/examSessions/hooks/useExamAnswerSync.test.js`
- Create: `src/features/examSessions/index.js`

- [ ] **Step 1: Write failing tests for merge + helpers**

```js
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
  const db = [{ question_id: 'q2', chosen_answer: 0, is_doubt: false }];
  const result = mergeAnswers(db, null);
  assert.deepEqual(result.answers, { q2: '0' });
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test src/features/examSessions/hooks/useExamAnswerSync.test.js`

Expected: FAIL with module not found.

- [ ] **Step 3: Implement hook with merge + queue + flush**

```js
import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchSessionAnswers, upsertSessionAnswers } from '../services/answerService.js';
import { readLocal, writeLocal, clearLocal } from '../utils/answerCache.js';

const normalizeId = (value) => (value === null || value === undefined ? '' : String(value));

export function mergeAnswers(dbRows, cache) {
  const answers = {};
  const doubts = [];
  (dbRows || []).forEach(r => {
    const qid = normalizeId(r.question_id);
    if (qid) {
      const dbChoice = r.chosen_answer;
      answers[qid] = dbChoice === null || dbChoice === undefined
        ? null
        : String(dbChoice).trim().toUpperCase();
      if (r.is_doubt && !doubts.includes(qid)) doubts.push(qid);
    }
  });
  if (cache?.answers) {
    Object.entries(cache.answers).forEach(([qid, v]) => {
      const normalized = normalizeId(qid);
      const cacheChoice = v.choice;
      answers[normalized] = cacheChoice === null || cacheChoice === undefined
        ? null
        : String(cacheChoice).trim().toUpperCase();
      if (v.isDoubt && !doubts.includes(normalized)) doubts.push(normalized);
    });
  }
  return { answers, doubts };
}

export async function loadMergedAnswers({ sessionId, fetchFn, readCache }) {
  if (!sessionId) return { answers: {}, doubts: [] };
  const cache = readCache(sessionId);
  try {
    const { data } = await fetchFn(sessionId);
    return mergeAnswers(data || [], cache);
  } catch {
    return mergeAnswers([], cache);
  }
}

export function buildCachePayload({ answers, doubts, now }) {
  const payload = { version: 1, updatedAt: now, answers: {} };
  Object.entries(answers || {}).forEach(([qid, choice]) => {
    const normalized = normalizeId(qid);
    payload.answers[normalized] = {
      choice,
      isDoubt: Array.isArray(doubts) && doubts.includes(normalized),
      updatedAt: now,
    };
  });
  return payload;
}

export async function runFlush({ sessionId, isLocked, queue, upsertFn, writeCache, snapshot, setFlushing }) {
  if (!sessionId || isLocked || !queue || queue.size === 0) return { data: [], error: null };
  setFlushing(true);
  try {
    const rows = Array.from(queue.values());
    const result = await upsertFn(sessionId, rows);
    if (!result?.error) {
      queue.clear();
      if (writeCache && snapshot) writeCache(sessionId, snapshot);
    }
    return result;
  } catch (error) {
    return { data: null, error };
  } finally {
    setFlushing(false);
  }
}

export function useExamAnswerSync({ sessionId, isLocked }) {
  const [answers, setAnswers] = useState({});
  const [doubts, setDoubts] = useState([]);
  const queueRef = useRef(new Map());
  const flushingRef = useRef(false);
  const answersRef = useRef(answers);
  const doubtsRef = useRef(doubts);

  const hydrate = useCallback(async () => {
    if (!sessionId) return;
    const merged = await loadMergedAnswers({
      sessionId,
      fetchFn: fetchSessionAnswers,
      readCache: readLocal,
    });
    setAnswers(merged.answers);
    setDoubts(merged.doubts);
  }, [sessionId]);

  const enqueue = useCallback((questionId, choice, isDoubt) => {
    if (!sessionId) return;
    const normalizedId = normalizeId(questionId);
    if (!normalizedId) return;
    const now = Date.now();
    queueRef.current.set(normalizedId, { questionId: normalizedId, choice, isDoubt, updatedAt: now });
    const payload = {
      version: 1,
      updatedAt: now,
      answers: {
        ...(readLocal(sessionId)?.answers || {}),
        [normalizedId]: { choice, isDoubt, updatedAt: now },
      },
    };
    writeLocal(sessionId, payload);
  }, [sessionId]);

  const flush = useCallback(async () => {
    if (flushingRef.current) return;
    const snapshot = buildCachePayload({
      answers: answersRef.current,
      doubts: doubtsRef.current,
      now: Date.now(),
    });
    await runFlush({
      sessionId,
      isLocked,
      queue: queueRef.current,
      upsertFn: upsertSessionAnswers,
      writeCache: writeLocal,
      snapshot,
      setFlushing: (value) => { flushingRef.current = value; },
    });
  }, [sessionId, isLocked]);

  const clearCache = useCallback(() => {
    if (!sessionId) return;
    clearLocal(sessionId);
    queueRef.current.clear();
  }, [sessionId]);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    answersRef.current = answers;
  }, [answers]);

  useEffect(() => {
    doubtsRef.current = doubts;
  }, [doubts]);

  useEffect(() => {
    if (!sessionId || isLocked) return;
    const timer = setInterval(() => { flush(); }, 1200);
    return () => clearInterval(timer);
  }, [sessionId, isLocked, flush]);

  return { answers, doubts, setAnswers, setDoubts, enqueue, flush, hydrate, clearCache };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test src/features/examSessions/hooks/useExamAnswerSync.test.js`

Expected: PASS all tests.

- [ ] **Step 5: Export from feature index**

```js
export { useExamAnswerSync } from './hooks/useExamAnswerSync.js';
```

- [ ] **Step 6: Commit**

```bash
git add src/features/examSessions/hooks/useExamAnswerSync.js src/features/examSessions/hooks/useExamAnswerSync.test.js src/features/examSessions/index.js
git commit -m "feat(exam-session): add autosave hook with merge and batch flush"
```

---

### Task 4: Integrasi di ExamInterface

**Files:**
- Modify: `src/pages/ExamInterface.jsx`

- [ ] **Step 1: Replace local answer state with hook**

```js
import { useExamAnswerSync } from '../features/examSessions';

const {
  answers,
  doubts: doubtfulQuestions,
  setAnswers,
  setDoubts: setDoubtfulQuestions,
  enqueue,
  flush,
  clearCache,
} = useExamAnswerSync({ sessionId, isLocked });
```

- [ ] **Step 2: Update handlers to use enqueue + state**

```js
const handleSelectOption = (questionId, option) => {
  if (isLocked) return;
  const cleanOption = String(option).trim().toUpperCase();
  setAnswers(prev => ({ ...prev, [questionId]: cleanOption }));
  const normalizedId = String(questionId);
  enqueue(normalizedId, cleanOption, doubtfulQuestions.includes(normalizedId));
};

const toggleDoubt = (questionId) => {
  const normalizedId = String(questionId);
  const newDoubts = doubtfulQuestions.includes(normalizedId)
    ? doubtfulQuestions.filter(id => id !== normalizedId)
    : [...doubtfulQuestions, normalizedId];
  setDoubtfulQuestions(newDoubts);
  if (answers[questionId]) {
    enqueue(normalizedId, answers[questionId], newDoubts.includes(normalizedId));
  }
};
```

- [ ] **Step 2b: Normalize questionId for UI doubt checks**

```js
const currentQId = String(currentQ.id);

const isDoubt = doubtfulQuestions.includes(String(q.id));
const isAnswered = !!answers[q.id];

// button
className={doubtfulQuestions.includes(currentQId) ? '...' : '...'}
```

- [ ] **Step 2c: Filter displayOptions to existing choices**

```js
const options = ['a', 'b', 'c', 'd', 'e'].filter((opt) => item.questions?.[`option_${opt}`]);

displayOptions: shuffleArray(options.length ? options : ['a', 'b', 'c', 'd', 'e'])
```

- [ ] **Step 3: Remove old rehydrate + saveToDB block**

Delete the manual fetch + `saveToDB` functions in `ExamInterface`:

```js
// remove this block
const { data: savedAns } = await supabase.from('student_answers').select('*').eq('session_id', currentSession.id);
// ... setAnswers/setDoubtfulQuestions

// remove saveToDB and its usage
const saveToDB = async (...) => { ... }
```

- [ ] **Step 4: Trigger flush on unload/visibility**

```js
useEffect(() => {
  const onHide = () => { flush(); };
  window.addEventListener('beforeunload', onHide);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) onHide();
  });
  return () => {
    window.removeEventListener('beforeunload', onHide);
    document.removeEventListener('visibilitychange', onHide);
  };
}, [flush]);
```

- [ ] **Step 4b: Guard async handlers when sessionId missing and cleanup unmount**

```js
useEffect(() => {
  let cancelled = false;
  const user = JSON.parse(localStorage.getItem('user_session'));
  if (!user || user.role !== 'siswa') {
    navigate('/login');
    return () => { cancelled = true; };
  }
  startExam(user.id, () => cancelled);
  return () => { cancelled = true; };
}, [examId]);

const handleCheatDetection = async () => {
  if (!sessionId) return;
  // ...existing logic
};
```

- [ ] **Step 5: Clear cache after submit**

```js
await flush();
await supabase.from('exam_sessions').update({ status: 'finished', finished_at: new Date().toISOString(), score }).eq('id', sessionId);
clearCache();
```

- [ ] **Step 5b: Remove early-return guard in submitExam**

```js
// remove
if (!isAuto && timeLeft > 60) return;
```

- [ ] **Step 6: Run manual refresh test**

Run: `npm run dev`

Expected:
- jawab beberapa soal,
- refresh page,
- jawaban tetap tampil,
- tidak ada error di console.

- [ ] **Step 7: Commit**

```bash
git add src/pages/ExamInterface.jsx
git commit -m "refactor(exam-session): integrate autosave hook for answer persistence"
```

---

### Task 5: Dokumentasi Constraint DB

**Files:**
- Modify: `DB.md`

- [ ] **Step 1: Add constraint/index notes**

```sql
-- Required for stable upsert
ALTER TABLE public.student_answers
ADD CONSTRAINT student_answers_session_question_unique
UNIQUE (session_id, question_id);

-- Optional index for faster rehydrate
CREATE INDEX IF NOT EXISTS student_answers_session_id_idx
ON public.student_answers (session_id);
```

- [ ] **Step 2: Commit**

```bash
git add DB.md
git commit -m "docs(db): document student_answers unique constraint for autosave"
```

---

## Definition of Done
- Refresh/reload tidak menghapus jawaban di UI.
- Tidak ada duplikasi jawaban di `student_answers`.
- Autosave melakukan batch flush tanpa spam query.
- Workflow ujian & anti-cheat tidak berubah.

## Spec Coverage Check
- DB constraint + index: Task 5.
- Cache lokal: Task 1.
- Service fetch/upsert: Task 2.
- Hook autosave + batch flush: Task 3.
- Integrasi ExamInterface: Task 4.

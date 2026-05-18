# Anti-Cheat Mobile Detection (Web-Only) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Strengthen anti-cheat detection on mobile by adding multi-signal client checks (visibility, blur, pagehide, timer drift, focus polling) while keeping existing PAS/PAT/SAJ and UH/PTS rules unchanged.

**Architecture:** Add a small anti-cheat signal helper for drift detection and constants. Update `ExamInterface` to route all signals through a single `reportViolation` function with cooldown, and register additional lifecycle listeners plus drift/focus polling.

**Tech Stack:** React, Supabase JS, Node.js test runner (`node:test`)

---

## File Map (Responsibilities)
- Create: `src/features/examSessions/utils/antiCheatSignals.js` — drift detection helper and timing constants.
- Create: `src/features/examSessions/utils/antiCheatSignals.test.js` — unit tests for drift helper.
- Modify: `src/pages/ExamInterface.jsx` — register multi-signal listeners and route to `reportViolation`.

---

### Task 1: Add anti-cheat drift helper (TDD)

**Files:**
- Create: `src/features/examSessions/utils/antiCheatSignals.test.js`
- Create: `src/features/examSessions/utils/antiCheatSignals.js`

- [ ] **Step 1: Write the failing tests**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_DRIFT_THRESHOLD_MS, isDrift } from './antiCheatSignals.js';

test('isDrift returns true when delta exceeds threshold', () => {
  assert.equal(
    isDrift(DEFAULT_DRIFT_THRESHOLD_MS + 1, DEFAULT_DRIFT_THRESHOLD_MS),
    true
  );
});

test('isDrift returns false for small or invalid deltas', () => {
  assert.equal(
    isDrift(DEFAULT_DRIFT_THRESHOLD_MS - 1, DEFAULT_DRIFT_THRESHOLD_MS),
    false
  );
  assert.equal(isDrift(Number.NaN, DEFAULT_DRIFT_THRESHOLD_MS), false);
});

test('isDrift uses default threshold when not provided', () => {
  assert.equal(isDrift(DEFAULT_DRIFT_THRESHOLD_MS + 100), true);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test src/features/examSessions/utils/antiCheatSignals.test.js`

Expected: FAIL with module not found.

- [ ] **Step 3: Write the minimal implementation**

```js
export const DEFAULT_DRIFT_THRESHOLD_MS = 3500;
export const DEFAULT_DRIFT_TICK_MS = 1000;
export const DEFAULT_FOCUS_POLL_MS = 1500;

export function isDrift(deltaMs, thresholdMs = DEFAULT_DRIFT_THRESHOLD_MS) {
  if (!Number.isFinite(deltaMs) || !Number.isFinite(thresholdMs)) return false;
  return deltaMs > thresholdMs;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test src/features/examSessions/utils/antiCheatSignals.test.js`

Expected: PASS

---

### Task 2: Strengthen anti-cheat signals in ExamInterface

**Files:**
- Modify: `src/pages/ExamInterface.jsx`

- [ ] **Step 1: Add anti-cheat helper imports**

```js
import {
  DEFAULT_DRIFT_THRESHOLD_MS,
  DEFAULT_DRIFT_TICK_MS,
  DEFAULT_FOCUS_POLL_MS,
  isDrift
} from '../features/examSessions/utils/antiCheatSignals.js';
```

- [ ] **Step 2: Add a drift tick ref near other refs**

```js
const lastCheatTime = useRef(0);
const lastTickRef = useRef(0);
```

- [ ] **Step 3: Replace the existing anti-cheat effect with multi-signal detection**

Replace the current anti-cheat `useEffect` (the block starting with `// --- LOGIKA ANTI CHEAT`) with:

```js
useEffect(() => {
  if (loading || isLocked || !sessionId || !schedule) return;

  const reportViolation = async (source) => {
    if (!sessionId) return;
    const now = Date.now();
    if (now - lastCheatTime.current < 2000) return;
    lastCheatTime.current = now;

    const newCount = violationCount + 1;
    setViolationCount(newCount);

    const examType = schedule.exams?.type;
    const isStrictExam = !['UH', 'PTS'].includes(examType);
    const isNowLocked = isStrictExam && newCount >= 2;

    await supabase
      .from('exam_sessions')
      .update({
        violation_count: newCount,
        status: isNowLocked ? 'locked' : 'active'
      })
      .eq('id', sessionId);

    if (!isStrictExam) {
      Swal.fire('Peringatan!', 'Tetap fokus pada lembar ujian!', 'warning');
      return;
    }

    if (newCount === 1) {
      Swal.fire({
        title: 'PERINGATAN!',
        text: 'Dilarang keluar halaman ujian atau akun Anda akan TERKUNCI!',
        icon: 'warning'
      });
      return;
    }

    if (isNowLocked) setIsLocked(true);
  };

  const onVisibility = () => {
    if (document.hidden) reportViolation('visibility');
  };
  const onBlur = () => reportViolation('blur');
  const onPageHide = () => reportViolation('pagehide');
  const onFreeze = () => reportViolation('freeze');

  document.addEventListener('visibilitychange', onVisibility);
  window.addEventListener('blur', onBlur);
  window.addEventListener('pagehide', onPageHide);
  document.addEventListener('freeze', onFreeze);

  const driftTimer = setInterval(() => {
    const now = performance.now();
    if (lastTickRef.current) {
      const delta = now - lastTickRef.current;
      if (isDrift(delta, DEFAULT_DRIFT_THRESHOLD_MS)) {
        reportViolation('drift');
      }
    }
    lastTickRef.current = now;
  }, DEFAULT_DRIFT_TICK_MS);

  const focusTimer = setInterval(() => {
    if (!document.hidden && typeof document.hasFocus === 'function' && !document.hasFocus()) {
      reportViolation('focus');
    }
  }, DEFAULT_FOCUS_POLL_MS);

  return () => {
    document.removeEventListener('visibilitychange', onVisibility);
    window.removeEventListener('blur', onBlur);
    window.removeEventListener('pagehide', onPageHide);
    document.removeEventListener('freeze', onFreeze);
    clearInterval(driftTimer);
    clearInterval(focusTimer);
  };
}, [loading, isLocked, sessionId, schedule, violationCount]);
```

- [ ] **Step 4: Run unit tests (sanity)**

Run: `node --test src/features/examSessions/utils/antiCheatSignals.test.js`

Expected: PASS

- [ ] **Step 5: Manual smoke check (mobile)**

Steps:
1. Start exam on a phone.
2. Trigger overlay/floating menu, return to app; verify `violation_count` increments.
3. Repeat once more on PAS/PAT/SAJ; verify session locks at 2nd violation.
4. Repeat on UH/PTS; verify warning only and no lock.

---

## Plan Self-Review
- **Spec coverage:** Added multi-signal detection, drift check, focus polling, and kept existing rules unchanged. No DB changes.
- **Placeholder scan:** No TODO/TBD or vague steps; concrete code and commands provided.
- **Type consistency:** Helper exports and usage in `ExamInterface` match.

---

## Execution Notes
- User requested inline work (no worktree).
- User will handle commits; plan omits commit steps.

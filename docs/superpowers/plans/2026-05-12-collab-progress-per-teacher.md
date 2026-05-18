# Collab Progress Per Teacher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show collaborator progress on each admin schedule card while keeping one card per teacher.

**Architecture:** Keep the existing schedule data pipeline. Compute collaborator lists from `teacher_progress_list` on the card, and render a separate "Rekan Colab" panel that excludes the card's teacher.

**Tech Stack:** React 19, node:test, Supabase JS, Vite.

---

## File Structure
- Modify: `src/features/schedules/utils/scheduleProgress.js` (add helper to filter collaborator list)
- Modify: `src/features/schedules/utils/index.js` (export helper)
- Modify: `src/features/schedules/utils/scheduleProgress.test.js` (unit test for helper)
- Modify: `src/features/schedules/components/ScheduleCard.jsx` (render collaborator panel)
- Modify: `log.md` (progress entry)

### Task 1: Add collaborator list helper + tests

**Files:**
- Modify: `src/features/schedules/utils/scheduleProgress.js`
- Modify: `src/features/schedules/utils/index.js`
- Test: `src/features/schedules/utils/scheduleProgress.test.js`

- [ ] **Step 1: Write the failing test**

Update the import in `src/features/schedules/utils/scheduleProgress.test.js`:

```js
import { attachTeacherProgress, getCollabProgressList } from './scheduleProgress.js';
```

Add this test after the existing one:

```js
test('getCollabProgressList excludes current teacher', () => {
  const progressList = [
    { teacher_id: 't-1', name: 'A', filled: 2, quota: 2 },
    { teacher_id: 't-2', name: 'B', filled: 0, quota: 2 },
  ];

  const result = getCollabProgressList(progressList, 't-1');

  assert.equal(result.length, 1);
  assert.equal(result[0].teacher_id, 't-2');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test src/features/schedules/utils/scheduleProgress.test.js`

Expected: FAIL with error about `getCollabProgressList` not defined.

- [ ] **Step 3: Write minimal implementation**

Add this helper to `src/features/schedules/utils/scheduleProgress.js`:

```js
export function getCollabProgressList(progressList = [], teacherId) {
  if (!teacherId) return progressList;
  return progressList.filter((item) => item.teacher_id !== teacherId);
}
```

Export it from `src/features/schedules/utils/index.js` (already re-exports everything from `./scheduleProgress` so no change needed unless file differs):

```js
export * from './scheduleProgress';
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test src/features/schedules/utils/scheduleProgress.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/features/schedules/utils/scheduleProgress.js src/features/schedules/utils/scheduleProgress.test.js
git commit -m "feat: add collab progress helper"
```

### Task 2: Render collaborator progress in admin cards

**Files:**
- Modify: `src/features/schedules/components/ScheduleCard.jsx`

- [ ] **Step 1: Wire helper and derive collaborator list**

Update imports and compute collaborator list:

```jsx
import { isExamReadyForStudent } from '../constants';
import { getCollabProgressList } from '../utils';
```

```jsx
const progressList = exam.teacher_progress_list || [];
const showProgress =
  userRole === 'admin' &&
  exam.exams?.status === 'pending_selection' &&
  progressList.length > 0;
const collabProgressList = getCollabProgressList(
  progressList,
  exam.teacher_id
);
const showCollabProgress = showProgress && collabProgressList.length > 0;
```

- [ ] **Step 2: Replace the progress list panel with a "Rekan Colab" panel**

Replace the existing `showProgress` block with this:

```jsx
{showCollabProgress && (
  <div className="w-full rounded-xl border border-slate-200 dark:border-zinc-800 bg-slate-50 dark:bg-zinc-900/40 px-4 py-3 text-[10px] font-bold uppercase">
    <div className="mb-2 text-slate-500 dark:text-zinc-400">Rekan Colab</div>
    <div className="space-y-1">
      {collabProgressList.map((teacher) => (
        <div
          key={teacher.teacher_id || teacher.id || teacher.name}
          className="flex justify-between"
        >
          <span className="truncate">{teacher.name}</span>
          <span className="text-slate-600 dark:text-zinc-300">
            {(teacher.filled ?? 0)}/{(teacher.quota ?? 0)}
          </span>
        </div>
      ))}
    </div>
  </div>
)}
```

- [ ] **Step 3: Run lint**

Run: `npm run lint`

Expected: exits with code 0, no new lint errors.

- [ ] **Step 4: Manual check (admin UI)**

Verify in Schedules:
- Card for Devia shows self progress 2/2 and "Rekan Colab" listing Diki 0/2.
- Card for Diki shows self progress 0/2 and "Rekan Colab" listing Devia 2/2.

- [ ] **Step 5: Commit**

```bash
git add src/features/schedules/components/ScheduleCard.jsx
git commit -m "feat: show collab progress on admin cards"
```

### Task 3: Update log

**Files:**
- Modify: `log.md`

- [ ] **Step 1: Add progress entry**

Run this to capture the timestamp:

```bash
TZ=Asia/Jakarta date '+%Y-%m-%d %H:%M WIB'
```

Add a new line under **Progress Tracking**:

```md
- [x] <TIMESTAMP_FROM_COMMAND> - Update admin schedule cards: show collaborator progress per teacher.
```

- [ ] **Step 2: Commit**

```bash
git add log.md
git commit -m "chore: log collab progress update"
```

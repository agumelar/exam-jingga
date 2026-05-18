# Collab Question Progress Indicator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Menampilkan indikator progres pengumpulan soal per guru (format `terkumpul/kuota`) pada halaman Schedules untuk admin, khusus ujian kolaborasi (PAS/PAT/SAJ).

**Architecture:** Hitung progres dari data schedules yang sudah ada (tanpa query baru) dengan mengelompokkan per `exam_id`, lalu injeksikan `teacher_progress_list` ke setiap schedule. `ScheduleCard` hanya merender daftar progres untuk admin saat status `pending_selection`.

**Tech Stack:** React 19, Supabase JS 2, node:test.

---

## Target Struktur File

### Create
- `src/features/schedules/utils/scheduleProgress.js`
- `src/features/schedules/utils/scheduleProgress.test.js`

### Modify
- `src/features/schedules/utils/index.js`
- `src/features/schedules/hooks/useSchedulesData.js`
- `src/features/schedules/components/ScheduleCard.jsx`
- `log.md`

---

### Task 1: Helper Progress per Exam + Unit Test

**Files:**
- Create: `src/features/schedules/utils/scheduleProgress.js`
- Create: `src/features/schedules/utils/scheduleProgress.test.js`

- [ ] **Step 1: Write failing test**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { attachTeacherProgress } from './scheduleProgress.js';

test('attachTeacherProgress builds progress list per exam', () => {
  const schedules = [
    {
      exam_id: 'exam-1',
      teacher_id: 't-1',
      teachers: { full_name: 'Beni' },
      my_question_count: 10,
      teacher_quota: 20,
      exams: { target_question_count: 40 },
    },
    {
      exam_id: 'exam-1',
      teacher_id: 't-2',
      teachers: { full_name: 'Cece' },
      my_question_count: 15,
      teacher_quota: 20,
      exams: { target_question_count: 40 },
    },
    {
      exam_id: 'exam-2',
      teacher_id: 't-3',
      teachers: { full_name: 'Dodi' },
      my_question_count: 5,
      teacher_quota: 10,
      exams: { target_question_count: 10 },
    },
  ];

  const result = attachTeacherProgress(schedules);
  const exam1 = result.find((item) => item.exam_id === 'exam-1');
  const exam2 = result.find((item) => item.exam_id === 'exam-2');

  assert.equal(exam1.teacher_progress_list.length, 2);
  assert.ok(
    exam1.teacher_progress_list.some(
      (t) => t.teacher_id === 't-1' && t.filled === 10 && t.quota === 20
    )
  );
  assert.ok(
    exam1.teacher_progress_list.some(
      (t) => t.teacher_id === 't-2' && t.filled === 15 && t.quota === 20
    )
  );

  assert.equal(exam2.teacher_progress_list.length, 1);
  assert.equal(exam2.teacher_progress_list[0].name, 'Dodi');
  assert.equal(exam2.teacher_progress_list[0].filled, 5);
  assert.equal(exam2.teacher_progress_list[0].quota, 10);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test src/features/schedules/utils/scheduleProgress.test.js`

Expected: FAIL with module not found.

- [ ] **Step 3: Implement helper**

```js
export function attachTeacherProgress(schedules = []) {
  const byExam = new Map();

  schedules.forEach((schedule) => {
    const examId = schedule.exam_id;
    if (!examId) return;
    if (!byExam.has(examId)) byExam.set(examId, []);

    const quota =
      schedule.teacher_quota ?? schedule.exams?.target_question_count ?? 0;
    const filled = schedule.my_question_count ?? 0;

    byExam.get(examId).push({
      teacher_id: schedule.teacher_id,
      name: schedule.teachers?.full_name || 'Guru',
      filled,
      quota,
    });
  });

  return schedules.map((schedule) => ({
    ...schedule,
    teacher_progress_list: byExam.get(schedule.exam_id) || [],
  }));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test src/features/schedules/utils/scheduleProgress.test.js`

Expected: PASS.

- [ ] **Step 5: Commit (user-run)**

```bash
git add src/features/schedules/utils/scheduleProgress.*
git commit -m "feat(schedules): add teacher progress list helper"
```

---

### Task 2: Inject Progress List in useSchedulesData

**Files:**
- Modify: `src/features/schedules/hooks/useSchedulesData.js`
- Modify: `src/features/schedules/utils/index.js`

- [ ] **Step 1: Export helper in utils index**

```js
export { attachTeacherProgress } from './scheduleProgress';
```

- [ ] **Step 2: Use helper in useSchedulesData**

```js
import { attachTeacherProgress } from '../utils';

const cleaned = mapScheduleCards(schedules, allQuestions);
const withProgress = attachTeacherProgress(cleaned);

const filteredByRole =
  String(sessionData.role || '').toLowerCase() === 'guru'
    ? withProgress.filter((item) => item.teacher_id === sessionData.id)
    : withProgress;
```

- [ ] **Step 3: Manual check**

Run: `npm run dev`

Expected: Schedules tetap muncul tanpa error.

- [ ] **Step 4: Commit (user-run)**

```bash
git add src/features/schedules/hooks/useSchedulesData.js src/features/schedules/utils/index.js
git commit -m "feat(schedules): inject collab teacher progress list"
```

---

### Task 3: Render Progress List on ScheduleCard (Admin)

**Files:**
- Modify: `src/features/schedules/components/ScheduleCard.jsx`

- [ ] **Step 1: Add admin progress block**

```js
const progressList = exam.teacher_progress_list || [];
const showProgress =
  userRole === 'admin' &&
  exam.exams?.status === 'pending_selection' &&
  progressList.length > 0;

{showProgress && (
  <div className="w-full rounded-xl border border-slate-200 dark:border-zinc-800 bg-slate-50 dark:bg-zinc-900/40 px-4 py-3 text-[10px] font-bold uppercase">
    <div className="mb-2 text-slate-500 dark:text-zinc-400">Progres Soal</div>
    <div className="space-y-1">
      {progressList.map((teacher) => (
        <div key={teacher.teacher_id} className="flex justify-between">
          <span className="truncate">{teacher.name}</span>
          <span className="text-slate-600 dark:text-zinc-300">
            {teacher.filled}/{teacher.quota}
          </span>
        </div>
      ))}
    </div>
  </div>
)}
```

- [ ] **Step 2: Manual check**

Run: `npm run dev`

Expected:
- Admin melihat list progres pada PAS/PAT/SAJ.
- Non-kolaborasi tampil 1 guru saja.

- [ ] **Step 3: Commit (user-run)**

```bash
git add src/features/schedules/components/ScheduleCard.jsx
git commit -m "feat(schedules): show teacher progress list for collab exams"
```

---

### Task 4: Update Log (Perencanaan + Progress)

**Files:**
- Modify: `log.md`

- [ ] **Step 1: Add log entry with current WIB timestamp**

```md
- [x] 2026-05-06 14:30 WIB - Added collab teacher progress indicator (plan + implementation).
```

- [ ] **Step 2: Commit (user-run)**

```bash
git add log.md
git commit -m "docs: log collab progress indicator work"
```

---

## Definition of Done
- Admin melihat daftar guru + progres `terkumpul/kuota` di Schedules untuk PAS/PAT/SAJ.
- Non-kolaborasi menampilkan satu guru dengan format yang sama.
- Tidak ada query baru ke Supabase.
- Log pengerjaan tercatat di `log.md`.

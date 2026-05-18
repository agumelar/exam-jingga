# Collab Quota Per Teacher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compute PAS/PAT/SAJ per-teacher quotas based on the max number of teachers in any class they teach, while keeping the global question pool per exam.

**Architecture:** Add a pure quota utility that derives per-teacher quota from `teacher_assignments`, then wire it into schedule creation/edit flows. Collab remains determined by `exams.type`, and no schema changes are required.

**Tech Stack:** React, Supabase JS, Node.js test runner (`node:test`)

---

## File Map (Responsibilities)
- Create: `src/features/schedules/utils/scheduleQuota.js` — pure functions to compute per-teacher quotas.
- Create: `src/features/schedules/utils/scheduleQuota.test.js` — unit tests for quota calculation.
- Modify: `src/features/schedules/utils/index.js` — export quota helpers.
- Modify: `src/features/schedules/hooks/useScheduleActions.js` — use per-teacher quota map for collab create/edit.

---

### Task 1: Add per-teacher quota utility (TDD)

**Files:**
- Create: `src/features/schedules/utils/scheduleQuota.test.js`
- Create: `src/features/schedules/utils/scheduleQuota.js`

- [ ] **Step 1: Write the failing tests**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { buildTeacherQuotaMap } from './scheduleQuota.js';

test('buildTeacherQuotaMap uses max teacher count per class with deterministic remainder', () => {
  const assignments = [
    { teacher_id: 't1', classes: { id: 'c-a', name: '10 RPL 1' } },
    { teacher_id: 't2', classes: { id: 'c-a', name: '10 RPL 1' } },
    { teacher_id: 't3', classes: { id: 'c-a', name: '10 RPL 1' } },
    { teacher_id: 't1', classes: { id: 'c-b', name: '10 RPL 2' } },
    { teacher_id: 't9', classes: { id: 'c-c', name: '10 TSM 1' } },
  ];

  const result = buildTeacherQuotaMap(assignments, 10);

  assert.equal(result.t1, 4);
  assert.equal(result.t2, 3);
  assert.equal(result.t3, 3);
  assert.equal(result.t9, 10);
});

test('buildTeacherQuotaMap returns empty map for empty input', () => {
  assert.deepEqual(buildTeacherQuotaMap([], 10), {});
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test src/features/schedules/utils/scheduleQuota.test.js`

Expected: FAIL with module not found or `buildTeacherQuotaMap` missing.

- [ ] **Step 3: Write the minimal implementation**

```js
export function buildTeacherQuotaMap(assignments = [], totalTarget = 0) {
  if (!Array.isArray(assignments) || assignments.length === 0) {
    return {};
  }

  const classTeachers = new Map();
  const teacherClasses = new Map();

  assignments.forEach((assignment) => {
    const classId = assignment.classes?.id ?? assignment.class_id;
    const teacherId = assignment.teacher_id;
    if (!classId || !teacherId) return;

    if (!classTeachers.has(classId)) classTeachers.set(classId, new Set());
    classTeachers.get(classId).add(teacherId);

    if (!teacherClasses.has(teacherId)) teacherClasses.set(teacherId, new Set());
    teacherClasses.get(teacherId).add(classId);
  });

  const teacherMaxCount = new Map();
  teacherClasses.forEach((classSet, teacherId) => {
    let maxCount = 1;
    classSet.forEach((classId) => {
      const count = classTeachers.get(classId)?.size ?? 1;
      if (count > maxCount) maxCount = count;
    });
    teacherMaxCount.set(teacherId, maxCount);
  });

  const quotaMap = {};
  const grouped = new Map();
  teacherMaxCount.forEach((maxCount, teacherId) => {
    if (!grouped.has(maxCount)) grouped.set(maxCount, []);
    grouped.get(maxCount).push(teacherId);
  });

  grouped.forEach((teacherIds, maxCount) => {
    const baseQuota = Math.floor(Number(totalTarget) / maxCount);
    const remainder = Number(totalTarget) % maxCount;
    teacherIds
      .slice()
      .sort()
      .forEach((teacherId, index) => {
        quotaMap[teacherId] = baseQuota + (index < remainder ? 1 : 0);
      });
  });

  return quotaMap;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test src/features/schedules/utils/scheduleQuota.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/features/schedules/utils/scheduleQuota.js src/features/schedules/utils/scheduleQuota.test.js
git commit -m "feat(schedules): add per-teacher quota calculator"
```

---

### Task 2: Wire per-teacher quota into collab schedule flows

**Files:**
- Modify: `src/features/schedules/utils/index.js`
- Modify: `src/features/schedules/hooks/useScheduleActions.js`

- [ ] **Step 1: Export the quota helper**

```js
export * from './scheduleMappers.js';
export * from './scheduleProgress.js';
export * from './scheduleQuota.js';
```

- [ ] **Step 2: Update collab schedule creation and edit logic**

Update imports and replace the old shared quota logic with a per-teacher map.

```js
import { useMemo } from 'react';
import Swal from 'sweetalert2';
import {
  EXAM_STATUS,
  canTransitionStatus,
  canCreateScheduleType,
  canEditSchedule,
  canUnlockUh,
  canVerifySchedule,
} from '../constants';
import { buildScheduleDateRange, buildTeacherQuotaMap } from '../utils';
import { buildExamPayload } from '../utils/payloadBuilders';
```

Remove the old helpers:

```js
// delete: computeMaxTeachersPerClass
// delete: computeQuotaPieces
```

Replace the collab update block in `updateExistingSchedule`:

```js
if (['PAS/PAT', 'SAJ'].includes(formData.type)) {
  const matchedAssignments = assignmentByLevelSubject(
    formData.level,
    formData.subject_id
  );
  if (matchedAssignments.length === 0) {
    throw new Error('Tidak ada guru yang ditugaskan untuk mapel dan jenjang ini.');
  }

  const quotaMap = buildTeacherQuotaMap(matchedAssignments, totalTarget);

  for (let index = 0; index < (existingSchedules || []).length; index += 1) {
    const schedule = existingSchedules[index];
    const quota = quotaMap[schedule.teacher_id] ?? 0;

    await updateScheduleById(supabase, schedule.id, {
      start_time: finalStart,
      end_time: finalEnd,
      token: formData.token,
      session_no: formData.session_no === 'Semua Sesi' ? 0 : Number(formData.session_no),
      teacher_quota: quota,
    });
  }

  return;
}
```

Replace the collab create block in `createCollabSchedule`:

```js
const matchedAssignments = assignmentByLevelSubject(
  formData.level,
  formData.subject_id
);
if (matchedAssignments.length === 0) {
  throw new Error('Tidak ada guru yang ditugaskan untuk mapel dan jenjang ini.');
}

const uniqueTeachers = Array.from(
  new Set(matchedAssignments.map((item) => item.teacher_id))
).sort();

const examPayload = buildExamPayload({
  type: formData.type,
  title: formData.title,
  subType: formData.sub_type,
  duration: formData.duration,
  targetQuestionCount: totalTarget,
  level: formData.level,
  subjectId: formData.subject_id,
  teacherId: myTeacherId,
  token: formData.token,
});

const { data: examData, error } = await createExam(supabase, examPayload);
if (error) throw error;

const quotaMap = buildTeacherQuotaMap(matchedAssignments, totalTarget);

const scheduleRows = uniqueTeachers.map((teacherId) => ({
  exam_id: examData.id,
  class_id: null,
  teacher_id: teacherId,
  start_time: finalStart,
  end_time: finalEnd,
  token: formData.token,
  session_no: formData.session_no === 'Semua Sesi' ? 0 : Number(formData.session_no),
  status: 'active',
  teacher_quota: quotaMap[teacherId] ?? 0,
}));

await insertSchedules(supabase, scheduleRows);
```

- [ ] **Step 3: Run tests**

Run: `node --test src/features/schedules/utils/scheduleQuota.test.js`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/features/schedules/utils/index.js src/features/schedules/hooks/useScheduleActions.js
git commit -m "feat(schedules): compute collab quota per teacher"
```

---

## Plan Self-Review
- **Spec coverage:** Collab vs non-collab rule, per-teacher quota based on max class teacher count, deterministic remainder, no schema changes, no backfill — all covered in Task 1 and Task 2.
- **Placeholder scan:** No TODO/TBD or vague steps; code included in each step.
- **Type consistency:** Function name `buildTeacherQuotaMap` used consistently in tests, exports, and hook wiring.

---

## Execution Notes
- User preference: no worktree; commits handled manually by the user.

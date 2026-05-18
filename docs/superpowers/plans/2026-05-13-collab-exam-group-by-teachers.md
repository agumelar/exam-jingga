# Collab Exam Grouping by Teacher Set Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split PAS/PAT/SAJ exams by exact teacher-set per class so status changes only affect the correct teachers and classes.

**Architecture:** Add grouping helpers that build teacher sets per class and create one exam per teacher-set group. Wire schedule creation/editing to use those groups and reuse the per-teacher quota map. No schema changes.

**Tech Stack:** React, Supabase JS, Node.js test runner (`node:test`)

---

## File Map (Responsibilities)
- Create: `src/features/schedules/utils/scheduleGrouping.js` — build teacher-set groups and stable keys.
- Create: `src/features/schedules/utils/scheduleGrouping.test.js` — unit tests for grouping.
- Modify: `src/features/schedules/utils/index.js` — export grouping helpers.
- Modify: `src/features/schedules/hooks/useScheduleActions.js` — use grouping in collab creation/edit.

---

### Task 1: Add teacher-set grouping helpers (TDD)

**Files:**
- Create: `src/features/schedules/utils/scheduleGrouping.test.js`
- Create: `src/features/schedules/utils/scheduleGrouping.js`

- [ ] **Step 1: Write the failing tests**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { buildTeacherSetGroups } from './scheduleGrouping.js';

test('buildTeacherSetGroups groups classes by sorted teacher set', () => {
  const assignments = [
    { teacher_id: 't1', class_id: 'c-a' },
    { teacher_id: 't1', class_id: 'c-b' },
    { teacher_id: 't2', class_id: 'c-b' },
    { teacher_id: 't3', class_id: 'c-c' },
    { teacher_id: 't2', class_id: 'c-c' },
    { teacher_id: 't3', class_id: 'c-c' },
  ];

  const groups = buildTeacherSetGroups(assignments);

  assert.equal(groups.length, 3);

  const solo = groups.find((g) => g.teacherSet.join(',') === 't1');
  assert.deepEqual(solo.classIds.sort(), ['c-a']);

  const pair = groups.find((g) => g.teacherSet.join(',') === 't1,t2');
  assert.deepEqual(pair.classIds.sort(), ['c-b']);

  const triple = groups.find((g) => g.teacherSet.join(',') === 't2,t3');
  assert.deepEqual(triple.classIds.sort(), ['c-c']);
});

test('buildTeacherSetGroups returns empty array for empty input', () => {
  assert.deepEqual(buildTeacherSetGroups([]), []);
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test src/features/schedules/utils/scheduleGrouping.test.js`

Expected: FAIL with module not found or `buildTeacherSetGroups` missing.

- [ ] **Step 3: Write the minimal implementation**

```js
export function buildTeacherSetGroups(assignments = []) {
  if (!Array.isArray(assignments) || assignments.length === 0) {
    return [];
  }

  const teachersByClass = new Map();
  assignments.forEach((assignment) => {
    const classId = assignment.classes?.id ?? assignment.class_id;
    const teacherId = assignment.teacher_id;
    if (!classId || !teacherId) return;

    if (!teachersByClass.has(classId)) teachersByClass.set(classId, new Set());
    teachersByClass.get(classId).add(teacherId);
  });

  const groupMap = new Map();
  teachersByClass.forEach((teacherSet, classId) => {
    const sortedTeachers = Array.from(teacherSet).sort();
    const key = sortedTeachers.join('|');
    if (!groupMap.has(key)) {
      groupMap.set(key, { teacherSet: sortedTeachers, classIds: [] });
    }
    groupMap.get(key).classIds.push(classId);
  });

  return Array.from(groupMap.values());
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test src/features/schedules/utils/scheduleGrouping.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/features/schedules/utils/scheduleGrouping.js src/features/schedules/utils/scheduleGrouping.test.js
git commit -m "feat(schedules): add teacher-set grouping helpers"
```

---

### Task 2: Wire grouping into collab schedule creation/edit

**Files:**
- Modify: `src/features/schedules/utils/index.js`
- Modify: `src/features/schedules/hooks/useScheduleActions.js`

- [ ] **Step 1: Export grouping helpers**

```js
export * from './dateTime.js';
export * from './scheduleMappers.js';
export * from './payloadBuilders.js';
export * from './scheduleProgress.js';
export * from './scheduleQuota.js';
export * from './scheduleGrouping.js';
```

- [ ] **Step 2: Update collab create logic to split exams by teacher-set**

Update imports:

```js
import { buildScheduleDateRange, buildTeacherQuotaMap, buildTeacherSetGroups } from '../utils';
```

Replace `createCollabSchedule` contents with group-aware logic:

```js
const matchedAssignments = assignmentByLevelSubject(
  formData.level,
  formData.subject_id
);
if (matchedAssignments.length === 0) {
  throw new Error('Tidak ada guru yang ditugaskan untuk mapel dan jenjang ini.');
}

const teacherSetGroups = buildTeacherSetGroups(matchedAssignments);
if (teacherSetGroups.length === 0) {
  throw new Error('Tidak ada grup guru yang valid untuk mapel dan jenjang ini.');
}

for (const group of teacherSetGroups) {
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

  const groupAssignments = matchedAssignments.filter((assignment) =>
    group.classIds.includes(assignment.classes?.id ?? assignment.class_id)
  );
  const quotaMap = buildTeacherQuotaMap(groupAssignments, totalTarget);

  const scheduleRows = group.teacherSet.map((teacherId) => ({
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
}
```

- [ ] **Step 3: Update collab edit logic to stay within group**

Replace the collab block in `updateExistingSchedule` with group-aware logic:

```js
if (['PAS/PAT', 'SAJ'].includes(formData.type)) {
  const matchedAssignments = assignmentByLevelSubject(
    formData.level,
    formData.subject_id
  );
  if (matchedAssignments.length === 0) {
    throw new Error('Tidak ada guru yang ditugaskan untuk mapel dan jenjang ini.');
  }

  const currentTeacherIds = new Set((existingSchedules || []).map((s) => s.teacher_id));
  const groupAssignments = matchedAssignments.filter((assignment) =>
    currentTeacherIds.has(assignment.teacher_id)
  );

  const quotaMap = buildTeacherQuotaMap(groupAssignments, totalTarget);

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

- [ ] **Step 4: Run tests**

Run: `node --test src/features/schedules/utils/scheduleGrouping.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/features/schedules/utils/index.js src/features/schedules/hooks/useScheduleActions.js
git commit -m "feat(schedules): split collab exams by teacher set"
```

---

## Plan Self-Review
- **Spec coverage:** teacher-set grouping, separate exams, per-teacher quotas per group, no schema change, no backfill — all covered in Task 1 and Task 2.
- **Placeholder scan:** no TODO/TBD or vague steps; code included per step.
- **Type consistency:** `buildTeacherSetGroups` used in tests, exports, and hook wiring consistently.

---

## Execution Notes
- User preference: no worktree; commits handled manually by the user.

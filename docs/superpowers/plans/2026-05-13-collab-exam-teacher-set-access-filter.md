# Collab Exam Teacher-Set Access Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restrict PAS/PAT/SAJ access to only the exam group whose teacher-set exactly matches the class teacher-set in StudentDashboard, ExamParticipants, and ExamResults.

**Architecture:** Add a small teacher-set key helper to build stable keys from teacher IDs. Use those keys to filter collab exam groups by matching class teacher-set with exam teacher-set, while keeping UH/PTS logic unchanged. No schema changes.

**Tech Stack:** React, Supabase JS, Node.js test runner (`node:test`)

---

## File Map (Responsibilities)
- Create: `src/features/schedules/utils/teacherSetKey.js` — build stable teacher-set keys.
- Create: `src/features/schedules/utils/teacherSetKey.test.js` — unit tests for key creation.
- Modify: `src/features/schedules/utils/index.js` — export teacher-set helper.
- Modify: `src/pages/StudentDashboard.jsx` — filter collab exams by teacher-set.
- Modify: `src/pages/ExamParticipants.jsx` — filter participants by teacher-set.
- Modify: `src/pages/ExamResults.jsx` — filter results by teacher-set.

---

### Task 1: Add teacher-set key helper (TDD)

**Files:**
- Create: `src/features/schedules/utils/teacherSetKey.test.js`
- Create: `src/features/schedules/utils/teacherSetKey.js`
- Modify: `src/features/schedules/utils/index.js`

- [ ] **Step 1: Write the failing tests**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { buildTeacherSetKey } from './teacherSetKey.js';

test('buildTeacherSetKey sorts and de-duplicates teacher ids', () => {
  const result = buildTeacherSetKey(['t2', 't1', 't1', 't3']);
  assert.equal(result, 't1|t2|t3');
});

test('buildTeacherSetKey returns empty string for empty input', () => {
  assert.equal(buildTeacherSetKey([]), '');
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node --test src/features/schedules/utils/teacherSetKey.test.js`

Expected: FAIL with module not found or `buildTeacherSetKey` missing.

- [ ] **Step 3: Write the minimal implementation**

```js
export function buildTeacherSetKey(teacherIds = []) {
  if (!Array.isArray(teacherIds) || teacherIds.length === 0) return '';
  const unique = Array.from(
    new Set(teacherIds.filter(Boolean).map((id) => String(id)))
  ).sort();
  return unique.join('|');
}
```

- [ ] **Step 4: Export the helper**

```js
export * from './dateTime.js';
export * from './scheduleMappers.js';
export * from './payloadBuilders.js';
export * from './scheduleProgress.js';
export * from './scheduleQuota.js';
export * from './teacherSetKey.js';
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `node --test src/features/schedules/utils/teacherSetKey.test.js`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/features/schedules/utils/teacherSetKey.js src/features/schedules/utils/teacherSetKey.test.js src/features/schedules/utils/index.js
git commit -m "feat(schedules): add teacher-set key helper"
```

---

### Task 2: Apply teacher-set filter in StudentDashboard

**Files:**
- Modify: `src/pages/StudentDashboard.jsx`

- [ ] **Step 1: Add teacher-set helper import**

```js
import { isExamReadyForStudent } from '../features/schedules/constants';
import { buildTeacherSetKey } from '../features/schedules/utils';
```

- [ ] **Step 2: Replace the collab eligibility block with group-based filtering**

Replace the block that builds `validExamsAll` with:

```js
const collabGroups = new Map();
const nonCollabSchedules = [];
let hasInvalidTeacherSet = false;

(schData || []).forEach((sch) => {
  const isToday = sch.start_time ? formatLocalDate(sch.start_time) === todayStr : false;
  const isReady = isExamReadyForStudent(sch.exams?.status);
  if (!isToday || !isReady) return;

  if (['UH', 'PTS'].includes(sch.exams?.type)) {
    if (sch.class_id === stuData.class_id) nonCollabSchedules.push(sch);
    return;
  }

  const isLevelOk = parseInt(sch.exams?.level) === level;
  const studentSessionNo = parseSessionNumber(logData?.session_name);
  const isSessionOk = sch.session_no === 0 || sch.session_no === studentSessionNo;
  if (!isLevelOk || !isSessionOk) return;

  if (!collabGroups.has(sch.exam_id)) collabGroups.set(sch.exam_id, []);
  collabGroups.get(sch.exam_id).push(sch);
});

const collabSchedules = [];
collabGroups.forEach((groupSchedules) => {
  const subjectId = groupSchedules[0]?.exams?.subject_id;
  const classTeacherSetKey = buildTeacherSetKey(myTeachersBySubject[subjectId] || []);
  const examTeacherSetKey = buildTeacherSetKey(groupSchedules.map((s) => s.teacher_id));

  if (!examTeacherSetKey) {
    hasInvalidTeacherSet = true;
    return;
  }
  if (!classTeacherSetKey || classTeacherSetKey !== examTeacherSetKey) return;

  collabSchedules.push(...groupSchedules);
});

if (hasInvalidTeacherSet) {
  Swal.fire('Error', 'Grup guru tidak valid untuk ujian ini.', 'error');
}

const validExamsAll = [...nonCollabSchedules, ...collabSchedules];
```

- [ ] **Step 3: Run unit tests (sanity)**

Run: `node --test src/features/schedules/utils/teacherSetKey.test.js`

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/pages/StudentDashboard.jsx
git commit -m "fix(student): filter collab exams by teacher set"
```

---

### Task 3: Apply teacher-set filter in ExamParticipants

**Files:**
- Modify: `src/pages/ExamParticipants.jsx`

- [ ] **Step 1: Add teacher-set helper import**

```js
import { supabase } from '../supabaseClient';
import { buildTeacherSetKey } from '../features/schedules/utils';
```

- [ ] **Step 2: Include teacher_id when fetching related schedules and compute examTeacherSetKey**

```js
const { data: allRelatedSch } = await supabase
  .from('schedules')
  .select('id, teacher_id')
  .eq('exam_id', schData.exam_id);

const allSchIds = allRelatedSch?.map((s) => s.id) || [examId];
const examTeacherSetKey = buildTeacherSetKey(
  (allRelatedSch || []).map((s) => s.teacher_id)
);

if (['PAS/PAT', 'SAJ'].includes(schData.exams.type) && !examTeacherSetKey) {
  Swal.fire('Error', 'Grup guru tidak valid untuk ujian ini.', 'error');
  setParticipants([]);
  setLoading(false);
  return;
}
```

- [ ] **Step 3: Replace collab class filtering with teacher-set matching**

Replace the collab branch that builds `ids` with:

```js
const { data: allClasses } = await supabase
  .from('classes')
  .select('id, name')
  .like('name', `${schData.exams.level} %`);

const classIdsForLevel = allClasses?.map((c) => c.id) || [];
const { data: subjectAssignments } = await supabase
  .from('teacher_assignments')
  .select('class_id, teacher_id')
  .eq('subject_id', schData.exams.subject_id)
  .in('class_id', classIdsForLevel);

const teacherIdsByClass = new Map();
subjectAssignments?.forEach((assignment) => {
  if (!teacherIdsByClass.has(assignment.class_id)) {
    teacherIdsByClass.set(assignment.class_id, []);
  }
  teacherIdsByClass.get(assignment.class_id).push(assignment.teacher_id);
});

let ids = classIdsForLevel.filter((classId) =>
  buildTeacherSetKey(teacherIdsByClass.get(classId) || []) === examTeacherSetKey
);

if (role === 'guru') {
  const teacherClassIds = assignments?.map((a) => a.class_id) || [];
  ids = ids.filter((id) => teacherClassIds.includes(id));
}
```

- [ ] **Step 4: Run unit tests (sanity)**

Run: `node --test src/features/schedules/utils/teacherSetKey.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pages/ExamParticipants.jsx
git commit -m "fix(participants): restrict collab classes by teacher set"
```

---

### Task 4: Apply teacher-set filter in ExamResults

**Files:**
- Modify: `src/pages/ExamResults.jsx`

- [ ] **Step 1: Add teacher-set helper import**

```js
import { supabase } from '../supabaseClient';
import { buildTeacherSetKey } from '../features/schedules/utils';
```

- [ ] **Step 2: Include teacher_id when fetching related schedules and compute examTeacherSetKey**

```js
const { data: allRelatedSch } = await supabase
  .from('schedules')
  .select('id, teacher_id')
  .eq('exam_id', schData.exam_id);
const allSchIds = allRelatedSch?.map((s) => s.id) || [examId];
const examTeacherSetKey = buildTeacherSetKey(
  (allRelatedSch || []).map((s) => s.teacher_id)
);

if (['PAS/PAT', 'SAJ'].includes(schData.exams.type) && !examTeacherSetKey) {
  Swal.fire('Error', 'Grup guru tidak valid untuk ujian ini.', 'error');
  setParticipants([]);
  setAnalysisData([]);
  setLoading(false);
  return;
}
```

- [ ] **Step 3: Replace collab class filtering with teacher-set matching**

Replace the collab branch that builds `idsToFetch` with:

```js
const { data: allClasses } = await supabase
  .from('classes')
  .select('id, name');
const classIdsForLevel = allClasses
  ?.filter((c) => c.name.startsWith(schData.exams.level.toString()))
  .map((c) => c.id) || [];

const { data: subjectAssignments } = await supabase
  .from('teacher_assignments')
  .select('class_id, teacher_id')
  .eq('subject_id', schData.exams.subject_id)
  .in('class_id', classIdsForLevel);

const teacherIdsByClass = new Map();
subjectAssignments?.forEach((assignment) => {
  if (!teacherIdsByClass.has(assignment.class_id)) {
    teacherIdsByClass.set(assignment.class_id, []);
  }
  teacherIdsByClass.get(assignment.class_id).push(assignment.teacher_id);
});

let idsToFetch = classIdsForLevel.filter((classId) =>
  buildTeacherSetKey(teacherIdsByClass.get(classId) || []) === examTeacherSetKey
);

if (role === 'guru' && allowedClassIds) {
  idsToFetch = idsToFetch.filter((id) => allowedClassIds.includes(id));
}
```

- [ ] **Step 4: Run unit tests (sanity)**

Run: `node --test src/features/schedules/utils/teacherSetKey.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/pages/ExamResults.jsx
git commit -m "fix(results): restrict collab classes by teacher set"
```

---

## Plan Self-Review
- **Spec coverage:** Teacher-set key creation, StudentDashboard filtering, ExamParticipants filtering, ExamResults filtering, error handling, and UH/PTS unchanged are covered in Tasks 1–4.
- **Placeholder scan:** No TODO/TBD or vague steps; code and commands are concrete.
- **Type consistency:** `buildTeacherSetKey` signature is used consistently across tasks.

---

## Execution Notes
- User preference: no worktree; commits handled manually by the user.

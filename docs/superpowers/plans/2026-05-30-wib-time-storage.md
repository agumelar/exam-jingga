# WIB Time Storage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Simpan semua waktu ujian sebagai WIB literal agar jam/tanggal di DB sama dengan input dan jadwal siswa tidak bergeser.

**Architecture:** Tambahkan util date/time yang selalu mem-parsing string waktu sebagai lokal (WIB), gunakan util ini untuk pembuatan jadwal, filter siswa/admin, serta penulisan sesi ujian. Lakukan migrasi DB dari timestamptz ke timestamp tanpa timezone menggunakan konversi ke WIB.

**Tech Stack:** React, Supabase, Vite, Node `test` (node:test)

---

## File Structure

**Modify:**
- `src/features/schedules/utils/dateTime.js` — tambah helper parsing & perbandingan lokal.
- `src/features/schedules/utils/dateTime.test.js` — uji helper baru.
- `src/features/schedules/utils/scheduleMappers.js` — normalisasi tanggal & hitung end_time berbasis helper lokal.
- `src/features/schedules/utils/scheduleMappers.test.js` — uji buildScheduleDateRange.
- `src/pages/StudentDashboard.jsx` — filter jadwal memakai rentang waktu.
- `src/pages/Schedules.jsx` — filter “Hari Ini” memakai tanggal lokal dari string.
- `src/pages/ExamInterface.jsx` — simpan started_at/finished_at sebagai WIB literal.

**Add (DB migration SQL run manually):**
- SQL untuk ALTER COLUMN ke `timestamp without time zone` + konversi WIB.

---

### Task 1: Tambah helper waktu lokal + unit test

**Files:**
- Modify: `src/features/schedules/utils/dateTime.js`
- Modify: `src/features/schedules/utils/dateTime.test.js`

- [ ] **Step 1: Write failing tests for helper lokal**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  formatWIB,
  toSQLDateTime,
  parseLocalDateTime,
  normalizeLocalDateTime,
  addMinutesToLocalDateTime,
  toLocalDateKey,
  isWithinLocalRange,
} from './dateTime.js';

test('parseLocalDateTime parses datetime-local string', () => {
  const parsed = parseLocalDateTime('2026-05-30T08:15');
  assert.equal(parsed.getFullYear(), 2026);
  assert.equal(parsed.getMonth(), 4);
  assert.equal(parsed.getDate(), 30);
  assert.equal(parsed.getHours(), 8);
  assert.equal(parsed.getMinutes(), 15);
});

test('normalizeLocalDateTime outputs SQL format', () => {
  assert.equal(
    normalizeLocalDateTime('2026-05-30T08:15'),
    '2026-05-30 08:15:00'
  );
});

test('addMinutesToLocalDateTime adds duration in minutes', () => {
  assert.equal(
    addMinutesToLocalDateTime('2026-05-30T08:15', 45),
    '2026-05-30 09:00:00'
  );
});

test('toLocalDateKey formats date key', () => {
  const date = new Date(2026, 4, 30, 8, 15, 0);
  assert.equal(toLocalDateKey(date), '2026-05-30');
});

test('isWithinLocalRange checks now within start/end', () => {
  const now = new Date(2026, 4, 30, 8, 30, 0);
  assert.equal(
    isWithinLocalRange({
      now,
      startTime: '2026-05-30 08:00:00',
      endTime: '2026-05-30 09:00:00',
    }),
    true
  );
  assert.equal(
    isWithinLocalRange({
      now,
      startTime: '2026-05-30 08:00:00',
      endTime: '2026-05-30 09:00:00',
    }),
    true
  );
  assert.equal(
    isWithinLocalRange({
      now: new Date(2026, 4, 30, 9, 1, 0),
      startTime: '2026-05-30 08:00:00',
      endTime: '2026-05-30 09:00:00',
    }),
    false
  );
});
```

- [ ] **Step 2: Run tests to verify failure**

Run: `node --test src/features/schedules/utils/dateTime.test.js`

Expected: FAIL with missing exports (parseLocalDateTime, normalizeLocalDateTime, etc.).

- [ ] **Step 3: Implement helper functions in dateTime.js**

```js
const MONTHS_ID = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'Mei',
  'Jun',
  'Jul',
  'Agu',
  'Sep',
  'Okt',
  'Nov',
  'Des',
];

function pad(value) {
  return String(value).padStart(2, '0');
}

function parseParts(value) {
  const match = String(value || '').match(
    /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?/
  );
  if (!match) return null;
  const [, year, month, day, hour, minute, second] = match;
  return {
    year: Number(year),
    month: Number(month),
    day: Number(day),
    hour: Number(hour),
    minute: Number(minute),
    second: Number(second || '0'),
  };
}

export function formatWIB(value) {
  if (!value) return '-';

  const parts = String(value).split(/[- :T]/);
  const [year, month, day, hour, minute] = parts;

  if (!year || !month || !day || !hour || !minute) {
    return '-';
  }

  const monthName = MONTHS_ID[Number(month) - 1];
  if (!monthName) return '-';

  return `${day} ${monthName} ${year}, ${hour}:${minute}`;
}

export function toSQLDateTime(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate()
  )} ${pad(date.getHours())}:${pad(date.getMinutes())}:00`;
}

export function parseLocalDateTime(value) {
  const parts = parseParts(value);
  if (!parts) return null;
  return new Date(
    parts.year,
    parts.month - 1,
    parts.day,
    parts.hour,
    parts.minute,
    parts.second
  );
}

export function normalizeLocalDateTime(value) {
  const parsed = parseLocalDateTime(value);
  if (!parsed) return null;
  return toSQLDateTime(parsed);
}

export function addMinutesToLocalDateTime(value, minutes) {
  const parsed = parseLocalDateTime(value);
  if (!parsed) return null;
  parsed.setMinutes(parsed.getMinutes() + Number(minutes));
  return toSQLDateTime(parsed);
}

export function toLocalDateKey(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
    date.getDate()
  )}`;
}

export function isWithinLocalRange({ now, startTime, endTime, durationMinutes }) {
  const start = parseLocalDateTime(startTime);
  if (!start) return false;
  const end = endTime
    ? parseLocalDateTime(endTime)
    : durationMinutes
      ? new Date(start.getTime() + Number(durationMinutes) * 60000)
      : null;
  if (!end) return false;

  return now >= start && now <= end;
}
```

- [ ] **Step 4: Run tests to verify pass**

Run: `node --test src/features/schedules/utils/dateTime.test.js`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/features/schedules/utils/dateTime.js src/features/schedules/utils/dateTime.test.js
git commit -m "feat: add local WIB datetime helpers"
```

---

### Task 2: Normalisasi jadwal & hitung end_time berbasis WIB

**Files:**
- Modify: `src/features/schedules/utils/scheduleMappers.js`
- Create: `src/features/schedules/utils/scheduleMappers.test.js`

- [ ] **Step 1: Write failing tests for buildScheduleDateRange**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { buildScheduleDateRange } from './scheduleMappers.js';

test('buildScheduleDateRange returns SQL start/end', () => {
  const { finalStart, finalEnd } = buildScheduleDateRange({
    startTime: '2026-05-30T08:15',
    duration: 45,
  });

  assert.equal(finalStart, '2026-05-30 08:15:00');
  assert.equal(finalEnd, '2026-05-30 09:00:00');
});
```

- [ ] **Step 2: Run test to verify failure**

Run: `node --test src/features/schedules/utils/scheduleMappers.test.js`

Expected: FAIL because current buildScheduleDateRange uses Date parsing with timezone and returns different output.

- [ ] **Step 3: Update scheduleMappers to use local helpers**

```js
import { addMinutesToLocalDateTime, normalizeLocalDateTime } from './dateTime.js';

export function mapScheduleCardItem(schedule, allQuestions = []) {
  const teacherQuestionCount =
    allQuestions?.filter(
      (item) =>
        item.exam_id === schedule.exam_id &&
        item.questions?.created_by === schedule.teacher_id
    ).length || 0;

  return {
    ...schedule,
    start_time: normalizeLocalDateTime(schedule.start_time),
    end_time: normalizeLocalDateTime(schedule.end_time),
    my_question_count: teacherQuestionCount,
    cluster_classes_text: `GABUNGAN KELAS ${schedule.exams?.level}`,
  };
}

export function buildScheduleDateRange({ startTime, duration }) {
  return {
    finalStart: normalizeLocalDateTime(startTime),
    finalEnd: addMinutesToLocalDateTime(startTime, duration),
  };
}
```

- [ ] **Step 4: Run test to verify pass**

Run: `node --test src/features/schedules/utils/scheduleMappers.test.js`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/features/schedules/utils/scheduleMappers.js src/features/schedules/utils/scheduleMappers.test.js
git commit -m "feat: normalize schedule datetime in WIB"
```

---

### Task 3: Terapkan filter WIB di siswa/admin + simpan session timestamp WIB

**Files:**
- Modify: `src/pages/StudentDashboard.jsx`
- Modify: `src/pages/Schedules.jsx`
- Modify: `src/pages/ExamInterface.jsx`

- [ ] **Step 1: Update StudentDashboard filter to use time range**

```js
import { isWithinLocalRange } from '../features/schedules/utils';

// ...inside fetchStudentData
const now = new Date();

(schData || []).forEach((sch) => {
  const isReady = isExamReadyForStudent(sch.exams?.status);
  const isInWindow = isWithinLocalRange({
    now,
    startTime: sch.start_time,
    endTime: sch.end_time,
    durationMinutes: sch.exams?.duration,
  });
  if (!isInWindow || !isReady) return;
  // ...rest unchanged
});
```

- [ ] **Step 2: Update Schedules “Hari Ini” filter to use local date key**

```js
import { formatWIB, parseLocalDateTime, toLocalDateKey } from '../features/schedules/utils';

// ...inside displayedExams filter
if (dateFilter === 'Hari Ini') {
  const todayStr = toLocalDateKey(new Date());
  const parsed = parseLocalDateTime(ex.start_time);
  dateMatch = parsed ? toLocalDateKey(parsed) === todayStr : false;
}
```

- [ ] **Step 3: Update ExamInterface to store WIB literal timestamps**

```js
import { toSQLDateTime } from '../features/schedules/utils';

// replace new Date().toISOString() for DB writes
const nowSql = toSQLDateTime(new Date());

// examples
const resetStart = toSQLDateTime(new Date());

await supabase.from('exam_sessions').update({
  status: 'finished',
  finished_at: toSQLDateTime(new Date()),
  score,
}).eq('id', sessionId);
```

- [ ] **Step 4: Commit**

```bash
git add src/pages/StudentDashboard.jsx src/pages/Schedules.jsx src/pages/ExamInterface.jsx
git commit -m "fix: use WIB-local time for filters and sessions"
```

---

### Task 4: Migrasi database ke WIB literal

**Files:**
- Manual SQL migration (Supabase SQL Editor)

- [ ] **Step 1: Run migration SQL**

```sql
alter table schedules
  alter column start_time type timestamp without time zone
  using start_time at time zone 'Asia/Jakarta',
  alter column end_time type timestamp without time zone
  using end_time at time zone 'Asia/Jakarta';

alter table exams
  alter column start_time type timestamp without time zone
  using start_time at time zone 'Asia/Jakarta';

alter table exam_sessions
  alter column started_at type timestamp without time zone
  using started_at at time zone 'Asia/Jakarta',
  alter column finished_at type timestamp without time zone
  using finished_at at time zone 'Asia/Jakarta';
```

- [ ] **Step 2: Verify sample data**

Run:
```sql
select id, start_time from schedules order by created_at desc limit 5;
```

Expected: waktu tampil sesuai WIB literal (tidak ada suffix `+00`).

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-05-30-wib-time-storage-design.md
git commit -m "docs: add WIB literal time storage spec"
```

---

## Plan Self-Review

- Spec coverage: skema, input, filter siswa, migrasi sudah punya task.
- Placeholder scan: tidak ada TBD/TODO.
- Type consistency: helper lokal dipakai di scheduleMappers, StudentDashboard, Schedules.

---

Plan complete and saved to `docs/superpowers/plans/2026-05-30-wib-time-storage.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?

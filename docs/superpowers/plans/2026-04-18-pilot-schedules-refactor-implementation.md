# Pilot Refactor Schedules Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Memecah modul `Schedules` menjadi struktur `page + hooks + services + utils + constants`, sambil menjaga workflow ujian tetap kompatibel (admin jadwalkan -> guru pilih soal -> admin verifikasi -> ujian dimulai) tanpa perubahan schema database.

**Architecture:** Pendekatan vertical slice pada domain `schedules`. Seluruh aturan status/transisi dipusatkan di constants, query Supabase dipusatkan di services, orchestration state dan action dipindah ke hooks, lalu halaman menjadi tipis sebagai composition UI. Refactor dilakukan bertahap agar aman untuk aplikasi live.

**Tech Stack:** React 19, React Router 7, Supabase JS 2, Tailwind CSS, SweetAlert2, Node built-in test runner (`node:test`) untuk unit test helper murni.

---

## Scope

### In Scope (Phase 1 / Pilot)
- Refactor `src/pages/Schedules.jsx` (file pilot).
- Konsolidasi workflow status di `Schedules`, `SelectQuestions`, `StudentDashboard`.
- Guard role dan guard transisi di layer action/service.
- Penambahan unit test untuk helper murni (tanpa ubah DB).

### Out of Scope
- Migrasi schema database.
- Perubahan auth/session global.
- Refactor modul selain domain jadwal (kecuali penyesuaian import helper status).

## Target Struktur File

### Create
- `src/features/schedules/constants/examWorkflow.js` - status enum, map label, guard transisi.
- `src/features/schedules/constants/rolePolicies.js` - capability per role untuk aksi jadwal.
- `src/features/schedules/constants/index.js` - barrel export constants.
- `src/features/schedules/utils/dateTime.js` - formatter WIB + parser datetime SQL.
- `src/features/schedules/utils/scheduleMappers.js` - mapper record Supabase ke kebutuhan UI card.
- `src/features/schedules/utils/payloadBuilders.js` - pure payload builder insert/update.
- `src/features/schedules/utils/index.js` - barrel export utils.
- `src/features/schedules/services/scheduleService.js` - seluruh query Supabase untuk domain jadwal.
- `src/features/schedules/hooks/useSchedulesData.js` - load session, assignments, list schedule.
- `src/features/schedules/hooks/useScheduleActions.js` - save/edit/verify/unlock/delete dengan guard.
- `src/features/schedules/components/ScheduleFilters.jsx` - toolbar search + date filter.
- `src/features/schedules/components/ScheduleCard.jsx` - card jadwal.
- `src/features/schedules/components/ScheduleFormModal.jsx` - modal form create/edit.
- `src/features/schedules/index.js` - export terpusat fitur schedules.
- `src/features/schedules/constants/examWorkflow.test.js`
- `src/features/schedules/utils/dateTime.test.js`
- `src/features/schedules/utils/payloadBuilders.test.js`

### Modify
- `src/pages/Schedules.jsx`
- `src/pages/SelectQuestions.jsx`
- `src/pages/StudentDashboard.jsx`
- `package.json` (opsional: script unit test)

---

### Task 1: Standarisasi Workflow Status

**Files:**
- Create: `src/features/schedules/constants/examWorkflow.js`
- Create: `src/features/schedules/constants/examWorkflow.test.js`
- Create: `src/features/schedules/constants/index.js`

- [ ] **Step 1: Write failing test for status transition and readiness rules**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  EXAM_STATUS,
  isExamReadyForStudent,
  resolveStatusAfterQuestionSave,
  canTransitionStatus,
} from './examWorkflow.js';

test('UH full question set goes to validated', () => {
  assert.equal(resolveStatusAfterQuestionSave({ examType: 'UH', isFull: true }), EXAM_STATUS.VALIDATED);
});

test('PTS full question set goes to waiting_validation', () => {
  assert.equal(resolveStatusAfterQuestionSave({ examType: 'PTS', isFull: true }), EXAM_STATUS.WAITING_VALIDATION);
});

test('student readiness accepts validated and ready/live compatibility', () => {
  assert.equal(isExamReadyForStudent('validated'), true);
  assert.equal(isExamReadyForStudent('ready'), true);
  assert.equal(isExamReadyForStudent('live'), true);
  assert.equal(isExamReadyForStudent('pending_selection'), false);
});

test('guru can unlock only UH from validated/ready', () => {
  assert.equal(canTransitionStatus({ role: 'guru', examType: 'UH', from: 'validated', to: 'pending_selection' }), true);
  assert.equal(canTransitionStatus({ role: 'guru', examType: 'PTS', from: 'validated', to: 'pending_selection' }), false);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test src/features/schedules/constants/examWorkflow.test.js`

Expected: FAIL with error module `examWorkflow.js` not found.

- [ ] **Step 3: Write minimal implementation for workflow helpers**

```js
export const EXAM_STATUS = {
  PENDING_SELECTION: 'pending_selection',
  WAITING_VALIDATION: 'waiting_validation',
  VALIDATED: 'validated',
  READY: 'ready',
  LIVE: 'live',
};

const STUDENT_READY = new Set([EXAM_STATUS.VALIDATED, EXAM_STATUS.READY, EXAM_STATUS.LIVE]);

export function isExamReadyForStudent(status) {
  return STUDENT_READY.has(String(status || '').toLowerCase());
}

export function resolveStatusAfterQuestionSave({ examType, isFull }) {
  if (!isFull) return null;
  return examType === 'UH' ? EXAM_STATUS.VALIDATED : EXAM_STATUS.WAITING_VALIDATION;
}

export function canTransitionStatus({ role, examType, from, to }) {
  if (role === 'admin' && from === EXAM_STATUS.WAITING_VALIDATION && to === EXAM_STATUS.VALIDATED) return true;
  if (role === 'guru' && examType === 'UH' && [EXAM_STATUS.VALIDATED, EXAM_STATUS.READY].includes(from) && to === EXAM_STATUS.PENDING_SELECTION) return true;
  return false;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test src/features/schedules/constants/examWorkflow.test.js`

Expected: PASS all tests.

- [ ] **Step 5: Commit**

```bash
git add src/features/schedules/constants
git commit -m "refactor(schedules): centralize exam workflow status rules"
```

### Task 2: Ekstrak Utils Date/Mapper

**Files:**
- Create: `src/features/schedules/utils/dateTime.js`
- Create: `src/features/schedules/utils/scheduleMappers.js`
- Create: `src/features/schedules/utils/dateTime.test.js`
- Create: `src/features/schedules/utils/index.js`

- [ ] **Step 1: Write failing test for `formatWIB` and SQL datetime conversion**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { formatWIB, toSQLDateTime } from './dateTime.js';

test('formatWIB returns short Indonesian date', () => {
  assert.equal(formatWIB('2026-05-01 07:30:00'), '01 Mei 2026, 07:30');
});

test('toSQLDateTime converts Date object to SQL text', () => {
  const d = new Date('2026-05-01T07:30:00');
  assert.match(toSQLDateTime(d), /^2026-05-01 07:30:00$/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test src/features/schedules/utils/dateTime.test.js`

Expected: FAIL with missing module/function.

- [ ] **Step 3: Implement utility module**

```js
const MONTHS_ID = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];

export function formatWIB(value) {
  if (!value) return '-';
  const [y, m, d, h, min] = String(value).split(/[- :T]/);
  return `${d} ${MONTHS_ID[Number(m) - 1]} ${y}, ${h}:${min}`;
}

export function toSQLDateTime(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:00`;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test src/features/schedules/utils/dateTime.test.js`

Expected: PASS all tests.

- [ ] **Step 5: Commit**

```bash
git add src/features/schedules/utils
git commit -m "refactor(schedules): extract datetime and mapping utilities"
```

### Task 3: Payload Builder Murni untuk Create/Edit Jadwal

**Files:**
- Create: `src/features/schedules/utils/payloadBuilders.js`
- Create: `src/features/schedules/utils/payloadBuilders.test.js`

- [ ] **Step 1: Write failing tests for payload build rules**

```js
import test from 'node:test';
import assert from 'node:assert/strict';
import { buildExamPayload } from './payloadBuilders.js';

test('SAJ title forced to Asesmen Sumatif Akhir Jenjang', () => {
  const payload = buildExamPayload({ type: 'SAJ', title: 'x', subType: '', duration: 90, targetQuestionCount: 40, level: 12, subjectId: 9, teacherId: 1 });
  assert.equal(payload.title, 'Asesmen Sumatif Akhir Jenjang');
});

test('PTS title uses selected semester subtype', () => {
  const payload = buildExamPayload({ type: 'PTS', title: '', subType: 'PTS Ganjil', duration: 90, targetQuestionCount: 40, level: 11, subjectId: 9, teacherId: 1 });
  assert.equal(payload.title, 'PTS Ganjil');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test src/features/schedules/utils/payloadBuilders.test.js`

Expected: FAIL because function not found.

- [ ] **Step 3: Implement pure payload builder**

```js
export function resolveExamTitle({ type, title, subType }) {
  if (type === 'SAJ') return 'Asesmen Sumatif Akhir Jenjang';
  if (type === 'PTS' || type === 'PAS/PAT') return subType;
  return title;
}

export function buildExamPayload({ type, title, subType, duration, targetQuestionCount, level, subjectId, teacherId, token }) {
  return {
    title: resolveExamTitle({ type, title, subType }),
    subject_id: subjectId,
    type,
    level: Number(level),
    teacher_id: teacherId,
    duration: Number(duration),
    target_question_count: Number(targetQuestionCount),
    token,
    status: 'pending_selection',
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test src/features/schedules/utils/payloadBuilders.test.js`

Expected: PASS all tests.

- [ ] **Step 5: Commit**

```bash
git add src/features/schedules/utils/payloadBuilders.*
git commit -m "refactor(schedules): add tested payload builders for schedule lifecycle"
```

### Task 4: Service Layer Supabase untuk Domain Schedules

**Files:**
- Create: `src/features/schedules/services/scheduleService.js`
- Modify: `src/pages/Schedules.jsx`

- [ ] **Step 1: Extract query read ke service**

```js
// scheduleService.js
export async function fetchSchedulesWithRelations(supabase) {
  return supabase
    .from('schedules')
    .select('*, exams(*, subjects(name)), teachers(full_name), classes(name)')
    .order('created_at', { ascending: false });
}
```

- [ ] **Step 2: Extract query mutate ke service**

```js
export async function verifyExamStatus(supabase, examId) {
  return supabase.from('exams').update({ status: 'validated' }).eq('id', examId);
}

export async function unlockUHExam(supabase, examId) {
  return supabase.from('exams').update({ status: 'pending_selection' }).eq('id', examId);
}
```

- [ ] **Step 3: Wire page sementara ke service (no behavior change)**

```js
const { data } = await fetchSchedulesWithRelations(supabase);
```

- [ ] **Step 4: Verify page behavior manually**

Run: `npm run dev`

Expected:
- list jadwal tetap muncul,
- tombol verify/unlock tetap berfungsi,
- tidak ada perubahan perilaku UI.

- [ ] **Step 5: Commit**

```bash
git add src/features/schedules/services src/pages/Schedules.jsx
git commit -m "refactor(schedules): move supabase queries into schedule service"
```

### Task 5: Hook `useSchedulesData` untuk Orkestrasi Read

**Files:**
- Create: `src/features/schedules/hooks/useSchedulesData.js`
- Modify: `src/pages/Schedules.jsx`

- [ ] **Step 1: Create hook skeleton for loading state + fetch data**

```js
export function useSchedulesData({ supabase, navigate }) {
  const [loading, setLoading] = useState(false);
  const [userRole, setUserRole] = useState('');
  const [myTeacherId, setMyTeacherId] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [schedules, setSchedules] = useState([]);
  // ... loadInitial() and refreshSchedules()
}
```

- [ ] **Step 2: Move session and assignment logic from page to hook**

Expected output state parity:
- `userRole`, `myTeacherId`, `allAssignments`, `exams` identik dengan sebelum refactor.

- [ ] **Step 3: Replace local state in `Schedules.jsx` with hook output**

```js
const {
  loading,
  userRole,
  myTeacherId,
  assignments,
  schedules,
  refreshSchedules,
} = useSchedulesData({ supabase, navigate });
```

- [ ] **Step 4: Run manual smoke for list/filter/search**

Run: `npm run dev`

Expected:
- role admin/guru tetap terfilter benar,
- search dan filter tanggal tetap jalan,
- refresh button tetap berfungsi.

- [ ] **Step 5: Commit**

```bash
git add src/features/schedules/hooks/useSchedulesData.js src/pages/Schedules.jsx
git commit -m "refactor(schedules): move schedule data orchestration to custom hook"
```

### Task 6: Hook `useScheduleActions` untuk Save/Edit/Verify/Unlock/Delete

**Files:**
- Create: `src/features/schedules/hooks/useScheduleActions.js`
- Modify: `src/pages/Schedules.jsx`
- Modify: `src/features/schedules/services/scheduleService.js`

- [ ] **Step 1: Implement action hook with role guard + transition guard**

```js
if (!canTransitionStatus({ role, examType, from, to })) {
  throw new Error('Aksi tidak diizinkan untuk role/status ini');
}
```

- [ ] **Step 2: Move handleSaveSchedule/handleVerify/handleUnlockUH to hook**

Target: `Schedules.jsx` hanya panggil handler dari hook.

- [ ] **Step 3: Keep payload build via tested helper**

```js
const examPayload = buildExamPayload({ ... });
```

- [ ] **Step 4: Manual verify all actions by role**

Run: `npm run dev`

Expected:
- admin bisa verify,
- guru hanya bisa unlock UH,
- role terlarang tidak bisa eksekusi action.

- [ ] **Step 5: Commit**

```bash
git add src/features/schedules/hooks/useScheduleActions.js src/features/schedules/services/scheduleService.js src/pages/Schedules.jsx
git commit -m "refactor(schedules): centralize schedule actions with role and transition guards"
```

### Task 7: Pecah UI Schedules Menjadi Komponen Kecil

**Files:**
- Create: `src/features/schedules/components/ScheduleFilters.jsx`
- Create: `src/features/schedules/components/ScheduleCard.jsx`
- Create: `src/features/schedules/components/ScheduleFormModal.jsx`
- Modify: `src/pages/Schedules.jsx`

- [ ] **Step 1: Extract search/date toolbar to `ScheduleFilters`**
- [ ] **Step 2: Extract card render to `ScheduleCard`**
- [ ] **Step 3: Extract modal form to `ScheduleFormModal`**
- [ ] **Step 4: Keep class names and visual behavior unchanged**

Run: `npm run dev`

Expected:
- tampilan tidak berubah,
- file `Schedules.jsx` turun signifikan (target < 220 lines),
- tidak ada runtime error.

- [ ] **Step 5: Commit**

```bash
git add src/features/schedules/components src/pages/Schedules.jsx
git commit -m "refactor(schedules): split page UI into focused components"
```

### Task 8: Sinkronisasi Workflow di `SelectQuestions` dan `StudentDashboard`

**Files:**
- Modify: `src/pages/SelectQuestions.jsx`
- Modify: `src/pages/StudentDashboard.jsx`
- Modify: `src/features/schedules/constants/examWorkflow.js`

- [ ] **Step 1: Replace hardcoded status assignment in `SelectQuestions`**

```js
const nextStatus = resolveStatusAfterQuestionSave({
  examType: examInfo.exams.type,
  isFull: totalNow === examInfo.exams.target_question_count,
});
```

- [ ] **Step 2: Replace hardcoded readiness list in `StudentDashboard`**

```js
const isReady = isExamReadyForStudent(sch.exams?.status);
```

- [ ] **Step 3: Add token activation helper usage in schedule card label**

```js
const tokenActive = isExamReadyForStudent(ex.exams?.status);
```

- [ ] **Step 4: Manual workflow E2E check**

Expected:
- UH full -> validated,
- PTS/PAS/PAT/SAJ full -> waiting_validation,
- setelah verify -> siswa bisa mulai ujian.

- [ ] **Step 5: Commit**

```bash
git add src/pages/SelectQuestions.jsx src/pages/StudentDashboard.jsx src/features/schedules/constants/examWorkflow.js
git commit -m "refactor(workflow): reuse centralized exam status rules across schedule flow"
```

### Task 9: Verifikasi Akhir + Dokumentasi Tracking

**Files:**
- Modify: `log.md`
- Modify: `plan.md` (checklist progress jika perlu)

- [ ] **Step 1: Run lint and build**

Run:
- `npm run lint`
- `npm run build`

Expected:
- lint lulus,
- build sukses tanpa error.

- [ ] **Step 2: Run unit tests for helper modules**

Run: `node --test src/features/schedules/**/*.test.js`

Expected: PASS all tests.

- [ ] **Step 3: Run manual regression matrix**

Checklist minimum:
- UH create -> select -> validated -> start exam.
- UH unlock by guru -> back to pending_selection.
- PTS full -> waiting_validation -> admin verify -> validated.
- PAS/PAT kolaborasi kuota per guru.
- Direct URL access tetap sesuai role.

- [ ] **Step 4: Update `log.md` with evidence and timestamp**

```md
- [x] 2026-04-18 22:10 WIB - Task 4 completed, `npm run build` pass.
```

- [ ] **Step 5: Commit**

```bash
git add log.md plan.md
git commit -m "docs: track pilot schedules refactor progress and verification"
```

---

## Definition of Done
- Semua string status kritikal dipusatkan di constants.
- Query Supabase untuk domain schedules tidak lagi tersebar di `Schedules.jsx`.
- `Schedules.jsx` menjadi container tipis (UI composition).
- Workflow admin/guru/verifikasi/siswa tetap kompatibel dengan behavior saat ini.
- Unit test helper murni + lint + build + smoke matrix berjalan.

## Catatan Implementasi Operasional
- Eksekusi merge/deploy hanya di luar jam aktif sekolah (22.00-04.00 WIB).
- Tidak ada migration schema pada pilot ini.
- Jika ada bug blocking, rollback cepat dengan mengembalikan page lama dari commit sebelumnya.

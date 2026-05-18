# Schedules Bulk Select + Default Today Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bulk selection + deletion for schedule cards and default the filter to today's exams.

**Architecture:** Keep Schedules page as the source of selection state. Add a small service helper to fetch all schedule IDs for global select. Use existing delete flow with a new bulk delete action.

**Tech Stack:** React 19, Supabase JS, node:test.

---

## File Structure
- Modify: `src/pages/Schedules.jsx` (selection state, bulk controls, default filter)
- Modify: `src/features/schedules/components/ScheduleCard.jsx` (checkbox UI)
- Modify: `src/features/schedules/services/scheduleService.js` (fetch all schedule IDs helper)
- Test: `src/features/schedules/services/scheduleService.test.js`
- Modify: `log.md` (progress entry)

### Task 1: Add service helper to fetch all schedule IDs

**Files:**
- Modify: `src/features/schedules/services/scheduleService.js`
- Test: `src/features/schedules/services/scheduleService.test.js`

- [ ] **Step 1: Write the failing test**

Update the import in `src/features/schedules/services/scheduleService.test.js`:

```js
import { fetchAllScheduleIds, fetchExamQuestionsWithAuthor } from './scheduleService.js';
```

Add this test to `src/features/schedules/services/scheduleService.test.js`:

```js
test('fetchAllScheduleIds selects schedule ids only', async () => {
  const calls = [];
  const supabase = {
    from(table) {
      calls.push({ table });
      return {
        select(fields) {
          calls.push({ fields });
          return { data: [{ id: 's-1' }, { id: 's-2' }], error: null };
        },
      };
    },
  };

  const result = await fetchAllScheduleIds(supabase);

  assert.equal(calls[0].table, 'schedules');
  assert.equal(calls[1].fields, 'id');
  assert.deepEqual(result, { data: ['s-1', 's-2'] });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test src/features/schedules/services/scheduleService.test.js`

Expected: FAIL with `fetchAllScheduleIds` not defined.

- [ ] **Step 3: Write minimal implementation**

Add this function to `src/features/schedules/services/scheduleService.js`:

```js
export async function fetchAllScheduleIds(supabase) {
  const { data, error } = await supabase.from('schedules').select('id');
  if (error) return { data: [], error };
  return { data: (data || []).map((row) => row.id) };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test src/features/schedules/services/scheduleService.test.js`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/features/schedules/services/scheduleService.js src/features/schedules/services/scheduleService.test.js
git commit -m "feat: add bulk schedule id fetch"
```

### Task 2: Add bulk select controls and default filter

**Files:**
- Modify: `src/pages/Schedules.jsx`

- [ ] **Step 1: Add selection state + default filter**

Add state near existing filters and update the service import:

```jsx
import {
  deleteScheduleById,
  fetchAllScheduleIds,
} from '../features/schedules/services/scheduleService';
```

```jsx
const [selectedScheduleIds, setSelectedScheduleIds] = useState([]);
const [dateFilter, setDateFilter] = useState('Hari Ini');
```

- [ ] **Step 2: Add handlers for select all / clear / toggle**

Add these helpers inside `Schedules`:

```jsx
const handleToggleSchedule = (scheduleId) => {
  setSelectedScheduleIds((prev) =>
    prev.includes(scheduleId)
      ? prev.filter((id) => id !== scheduleId)
      : [...prev, scheduleId]
  );
};

const handleClearSelection = () => setSelectedScheduleIds([]);

const handleSelectAll = async () => {
  const { data, error } = await fetchAllScheduleIds(supabase);
  if (error) {
    await Swal.fire('Gagal!', error.message, 'error');
    return;
  }
  setSelectedScheduleIds(data || []);
};
```

- [ ] **Step 3: Add bulk delete handler**

Add this handler:

```jsx
const handleBulkDelete = async () => {
  if (selectedScheduleIds.length === 0) return;

  const { isConfirmed } = await Swal.fire({
    title: 'Hapus semua terpilih?',
    text: `Total ${selectedScheduleIds.length} jadwal akan dihapus.`,
    icon: 'warning',
    showCancelButton: true,
  });

  if (!isConfirmed) return;

  const failedIds = [];
  let lastError = null;

  for (const scheduleId of selectedScheduleIds) {
    const { error } = await deleteScheduleById(supabase, scheduleId);
    if (error) {
      failedIds.push(scheduleId);
      lastError = error;
    }
  }

  await refreshSchedules();

  if (failedIds.length > 0) {
    setSelectedScheduleIds(failedIds);
    await Swal.fire(
      'Gagal!',
      lastError?.message || `${failedIds.length} jadwal gagal dihapus.`,
      'error'
    );
    return;
  }

  setSelectedScheduleIds([]);
};
```

- [ ] **Step 4: Wire controls into UI**

Add buttons above `ScheduleFilters` (after header) for admins only:

```jsx
{userRole === 'admin' && (
  <div className="mb-4 flex flex-wrap gap-2">
    <button onClick={handleSelectAll} className="bg-white border border-slate-200 px-4 py-2 rounded-xl text-xs font-black uppercase">
      Select All
    </button>
    <button onClick={handleClearSelection} className="bg-white border border-slate-200 px-4 py-2 rounded-xl text-xs font-black uppercase">
      Clear
    </button>
    <button
      onClick={handleBulkDelete}
      disabled={selectedScheduleIds.length === 0}
      className="bg-red-600 text-white px-4 py-2 rounded-xl text-xs font-black uppercase disabled:opacity-50"
    >
      Hapus Terpilih
    </button>
  </div>
)}
```

- [ ] **Step 5: Pass selection props into ScheduleCard**

Update card render:

```jsx
<ScheduleCard
  ...
  isSelected={selectedScheduleIds.includes(ex.id)}
  onToggleSelected={() => handleToggleSchedule(ex.id)}
/>
```

- [ ] **Step 6: Commit**

```bash
git add src/pages/Schedules.jsx
git commit -m "feat: add bulk schedule selection controls"
```

### Task 3: Add checkbox UI to ScheduleCard

**Files:**
- Modify: `src/features/schedules/components/ScheduleCard.jsx`

- [ ] **Step 1: Add props and checkbox**

Update props:

```jsx
export function ScheduleCard({
  exam,
  userRole,
  formatWIB,
  onEdit,
  onDelete,
  onOpenSelectQuestions,
  onVerify,
  onUnlockUH,
  onOpenParticipants,
  onOpenResults,
  isSelected,
  onToggleSelected,
}) {
```

Add checkbox in card header area:

```jsx
{userRole === 'admin' && (
  <button
    type="button"
    onClick={onToggleSelected}
    className={`absolute top-4 left-4 w-7 h-7 rounded-full border flex items-center justify-center ${
      isSelected ? 'bg-emerald-500 border-emerald-500 text-white' : 'bg-white border-slate-200'
    }`}
    title="Pilih Jadwal"
  >
    {isSelected ? '✓' : ''}
  </button>
)}
```

- [ ] **Step 2: Commit**

```bash
git add src/features/schedules/components/ScheduleCard.jsx
git commit -m "feat: add schedule card selection checkbox"
```

### Task 4: Update log

**Files:**
- Modify: `log.md`

- [ ] **Step 1: Add progress entry**

Run:

```bash
TZ=Asia/Jakarta date '+%Y-%m-%d %H:%M WIB'
```

Add line under **Progress Tracking**:

```md
- [x] <TIMESTAMP> - Add bulk select/delete for schedules + default filter to today.
```

- [ ] **Step 2: Commit**

```bash
git add log.md
git commit -m "chore: log schedule bulk selection"
```

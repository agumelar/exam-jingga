# Collab Exam Grouping by Teacher Set (PAS/PAT/SAJ)

## Summary
Fix the “all teachers finish together” issue by splitting PAS/PAT/SAJ exams into groups based on the exact set of teachers that teach each class. Each teacher-set group gets its own `exam_id`, so status changes only affect the right teachers and classes.

## Goals
- Prevent non-collab teachers from being marked finished when another teacher completes the exam.
- Preserve true collaboration for co-teaching classes (shared question pool).
- Keep UH/PTS behavior unchanged (one exam per teacher/class).
- Reuse existing data model (no schema changes).

## Non-Goals
- No automatic backfill for existing schedules unless edited.
- No per-student exam split.
- No changes to student auth or token logic.

## Core Rules
### Collab vs Non-Collab
- Collab: `PAS/PAT`, `SAJ`
- Non-collab: `UH`, `PTS`

### Grouping Rule (Collab)
- Build teacher sets per class using `teacher_assignments` for `subject_id` + `level`.
- Group classes by **exact teacher set** (sorted list of `teacher_id`).
- Create a separate `exam` for each teacher-set group.

Example:
- Kelas A: {Intan}
- Kelas B: {Intan}
- Kelas C: {Intan, Zul}

Result:
- Group {Intan} → 1 exam shared by classes A & B
- Group {Intan, Zul} → 1 exam shared by class C only

### Question Pool
- Each group has its own `exam_id` and its own global question pool.
- Status updates affect only that group’s teachers.

## Data Flow Impact
### Create Schedule (Collab)
1) Filter `teacher_assignments` by `subject_id` + `level`.
2) Build `teacherSet` for each class.
3) Group classes by teacherSet.
4) For each group:
   - Create one `exam`.
   - Insert one `schedule` per teacher in teacherSet (class_id: null).

### Update Schedule (Collab)
- Editing one schedule updates its own exam group only.
- Recompute quotas for the teachers in that group.

### Unchanged
- `SelectQuestions` status updates (now scoped to the correct exam group).
- Student access logic based on `teacher_assignments`.
- UH/PTS flow.

## Quota Rule (Collab)
- Per-teacher quota computed using max teacher count across the classes that teacher teaches (existing rule).
- Applied within each exam group.

## Edge Cases
- If no assignments found, show error “Tidak ada guru yang ditugaskan...”.
- Teacher-set group with only one teacher behaves like non-collab, but still uses PAS/PAT/SAJ flow.
- A teacher teaching multiple groups will get separate schedules per group (expected).

## Testing
- Create PAS/PAT/SAJ with mixed teacher sets and verify:
  - Separate exams are created for distinct teacher sets.
  - Completing one group does not mark other teachers as finished.
  - Co-teaching group still shares question pool.

## Rollout Notes
- Applies to new schedules and edits only.
- No DB migrations or backfills.

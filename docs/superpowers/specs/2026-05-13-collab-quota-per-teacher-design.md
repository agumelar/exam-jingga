# Collab Quota Per Teacher (PAS/PAT/SAJ)

## Summary
Adjust quota calculation for collaborative exams so each teacher gets a quota based on the classes they actually teach. Collab is determined by `exams.type` (PAS/PAT, SAJ). The question pool remains global per `exam_id`.

## Goals
- Keep collab rules tied to `exams.type`:
  - `UH`, `PTS` = non-collab
  - `PAS/PAT`, `SAJ` = collab
- For collab exams, compute `teacher_quota` per teacher using assignments by class and subject.
- Preserve global question pool per exam (no per-class duplication).
- Avoid schema changes and keep Supabase queries minimal.

## Non-Goals
- No changes to existing schedules unless they are edited.
- No new admin batch tools to recalc legacy schedules.
- No per-class exam separation.

## Rules
### Collab vs Non-Collab
- Collab: `PAS/PAT`, `SAJ`
- Non-collab: `UH`, `PTS`

### Question Pool
- `exam_questions` remains global per `exam_id`.
- Total selected questions must not exceed `exams.target_question_count`.

### Teacher Quota (Collab)
For a given collab exam:
1) Filter `teacher_assignments` by `subject_id` and `level` (derived from class name).
2) Build a list of classes each teacher teaches for that subject + level.
3) For each teacher, calculate:
   - `maxTeacherCount` = max number of teachers in any class they teach.
4) Quota for the teacher:
   - `baseQuota = floor(totalTarget / maxTeacherCount)`
   - `remainder = totalTarget % maxTeacherCount`
   - Remainder distributed deterministically by sorted `teacher_id` within the same `maxTeacherCount` group.

### Non-Collab Quota
- `teacher_quota = totalTarget` (no change)

## Data Flow Impact
### Create Schedule (Collab)
- `createCollabSchedule` computes a per-teacher quota map and inserts schedule rows with:
  - `class_id: null`
  - `teacher_quota: quotaMap[teacher_id]`

### Update Schedule (Collab)
- `updateExistingSchedule` recomputes quotas using the same rules and updates all schedules for the exam.

### Unchanged
- `SelectQuestions` and global question limit behavior.
- Student access logic based on `teacher_assignments`.

## Edge Cases
- No assignments found: surface error "Tidak ada guru yang ditugaskan...".
- If a teacher only teaches classes with 1 teacher, they get full quota.
- Mixed classes (some with 1 teacher, some with 2+): quota uses the max teacher count across that teacher's classes.
- Small `target_question_count` with large `maxTeacherCount` can yield zero quota for some teachers (acceptable under current rules).

## Testing
- Unit test for per-teacher quota calculation.
- Smoke test:
  - Create PAS/PAT/SAJ with mixed classes (1-teacher and 2-teacher).
  - Verify `teacher_quota` per schedule row matches rule.
  - Confirm global question limit is enforced.

## Rollout Notes
- Applies to new schedules and edits only.
- No DB migrations or backfills.

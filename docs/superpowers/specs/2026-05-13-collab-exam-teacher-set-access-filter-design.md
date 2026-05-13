# Collab Exam Teacher-Set Access Filter

## Summary
Restrict PAS/PAT/SAJ access to only the exam group whose teacher-set exactly matches the class teacher-set, so classes taught by a single teacher do not see collaborative exam groups for other teacher combinations.

## Goals
- Enforce teacher-set matching for collab exams in StudentDashboard, ExamParticipants, and ExamResults.
- Keep UH/PTS behavior unchanged.
- Align filtering with existing collab exam grouping (per teacher-set group).

## Non-Goals
- No schema changes or backfills.
- No change to exam creation or quota rules.
- No changes to exam session status transitions.

## Core Rules
- Collab: `PAS/PAT`, `SAJ`.
- Non-collab: `UH`, `PTS`.
- A collab exam is visible only if `classTeacherSetKey === examTeacherSetKey`.

## Key Definitions
- `classTeacherSetKey`: sorted unique `teacher_id` from `teacher_assignments` for a specific `class_id` + `subject_id`, joined with `|`.
- `examTeacherSetKey`: sorted unique `teacher_id` from all `schedules` with the same `exam_id`, joined with `|`.

## Data Flow Impact
### StudentDashboard
1) Load active schedules for today as usual.
2) Group schedules by `exam_id`.
3) For each exam group (collab only), compute `examTeacherSetKey` from its schedules.
4) Compute `classTeacherSetKey` for the student class using assignments for `subject_id`.
5) Keep the exam group only when keys match.
6) Deduplicate per `exam_id` and preserve session prioritization.

### ExamParticipants
1) Fetch schedule + related schedules (same `exam_id`).
2) Compute `examTeacherSetKey` from related schedules.
3) For collab:
   - Enumerate classes at the same level.
   - Compute `classTeacherSetKey` per class using assignments for `subject_id`.
   - Keep only classes matching `examTeacherSetKey`.
   - If role is `guru`, intersect with classes they teach (existing rule).
4) Non-collab remains class_id based.

### ExamResults
Same filtering as ExamParticipants for participants and analysis data.

## Error Handling
- If `examTeacherSetKey` is empty for collab, show an error and return empty data.
- If no classes match the teacher-set, show empty state (existing UI behavior).

## Testing
- PAS/PAT/SAJ with mixed teacher-set groups:
  - Class set {Intan} sees only {Intan} group.
  - Class set {Intan, Zul} sees only {Intan, Zul} group.
- UH/PTS unchanged.

## Rollout Notes
- Applies to new and existing data without migration.
- No backfill; logic is computed at query time.

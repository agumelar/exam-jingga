# Collab Progress Per Teacher (Admin Cards)

## Summary
Admins need to see per-teacher progress for collaborative exams while keeping one card per teacher. Each admin card should show the current teacher's progress and a list of collaborator progress for the same exam.

## Goals
- Keep two cards (one per teacher schedule) as-is.
- Show each teacher's own progress on their card.
- Show collaborator progress (other teachers on the same exam_id) on the same card.
- No new Supabase queries or schema changes.

## Non-Goals
- No aggregation into a single exam card.
- No changes to how quotas are calculated or stored.
- No new admin actions or notifications.

## Current Behavior
- Each schedule card calculates `my_question_count` using `exam_questions` filtered by `exam_id` and `questions.created_by`.
- Admin cards show a single progress line for the card's teacher.
- A global progress list exists (`teacher_progress_list`) but is not separated into "self" vs "collab" groups.

## Proposed Behavior
For admin users, when exam status is `pending_selection`:
- Keep the existing "Progres" line for the card teacher.
- Add a "Rekan Colab" panel that lists other teachers from the same `exam_id` with their `filled/quota` values.
- Hide the "Rekan Colab" panel when there are no other teachers.

## Data Flow
1. `fetchExamQuestionsWithAuthor` continues to return `exam_questions` with `exam_id` and `questions.created_by`.
2. `mapScheduleCardItem` continues to compute `my_question_count` per schedule.
3. `attachTeacherProgress` continues to build `teacher_progress_list` per `exam_id`.
4. `ScheduleCard` derives:
   - `selfProgress` from the card's `my_question_count` and quota.
   - `collabProgressList` by filtering `teacher_progress_list` where `teacher_id !== exam.teacher_id`.
5. Render `collabProgressList` in a new panel under the existing progress line.

## UI Details
- Show only for admin and only when `exams.status === 'pending_selection'`.
- Panel label: "Rekan Colab".
- Each row: teacher name + `filled/quota`.
- Use the existing visual style (small, uppercase labels and subtle card background).

## Edge Cases
- If `teacher_progress_list` is empty or only includes the current teacher, the "Rekan Colab" panel is hidden.
- If teacher name missing, fall back to "Guru" (existing behavior).

## Testing
- Unit test not required (UI-only change).
- Manual check: admin view shows both self progress and collaborator progress per card for the same exam.

## Rollout Notes
- No migrations.
- No config changes.
- Low risk; uses existing data already fetched for schedules.

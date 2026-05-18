# Schedules Bulk Select + Default Today Filter

## Summary
Admins need a global "Select All" to delete all schedule cards at once, and the default filter should show only today's exams instead of all time.

## Goals
- Add a global "Select All" that targets all schedule records in the database (not just visible cards).
- Allow admins to delete selected schedules in bulk with confirmation.
- Change default date filter to "Hari Ini".

## Non-Goals
- No role changes or permissions beyond admin actions already allowed.
- No new database schema or Supabase policies.
- No UI redesign beyond the selection controls.

## Current Behavior
- Filters default to "Semua Ujian" (all time).
- Deletion is per-card only.
- No selection state or bulk actions.

## Proposed Behavior
### Bulk Selection
- Add selection controls on Schedules page:
  - "Select All": fetches all schedule IDs from Supabase and selects them.
  - "Clear": clears selection.
  - "Hapus Terpilih": deletes all selected schedule IDs (with confirmation).
- Each ScheduleCard gets a checkbox for individual selection.

### Default Filter
- Default `dateFilter` state becomes "Hari Ini".
- The filter dropdown still allows switching back to "Semua Waktu".

## Data Flow
1. Schedules page maintains `selectedScheduleIds` state.
2. "Select All" uses a service call to fetch all schedule IDs (no filters), then sets `selectedScheduleIds`.
3. "Hapus Terpilih" confirms and deletes each schedule ID in `selectedScheduleIds`.
4. After deletion, refresh schedules and clear selection.

## UI Details
- Controls live near the filter/search area for visibility.
- Bulk controls only show for admin users.
- Checkbox on each card reflects selection state.
- "Hapus Terpilih" is disabled when no selection.

## Edge Cases
- Empty schedules → "Select All" results in empty selection.
- Large schedule list → selection only stores IDs (no large objects).
- If deletion fails for any ID, surface error and keep failed IDs selected.

## Testing
- Add unit test for service fetching all schedule IDs.
- Manual: select all, delete, and verify schedules refresh and selection cleared.

## Rollout Notes
- No migrations.
- Low risk; uses existing schedule delete flow.

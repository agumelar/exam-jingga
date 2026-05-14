import test from 'node:test';
import assert from 'node:assert/strict';
import {
  fetchAllScheduleIds,
  fetchExamQuestionsWithAuthor,
} from './scheduleService.js';

test('fetchExamQuestionsWithAuthor returns empty when no exam ids', async () => {
  const supabase = {
    from() {
      throw new Error('should not call');
    },
  };

  const result = await fetchExamQuestionsWithAuthor(supabase, []);

  assert.deepEqual(result, { data: [] });
});

test('fetchExamQuestionsWithAuthor filters by exam ids', async () => {
  const calls = [];
  const supabase = {
    from(table) {
      calls.push({ table });
      return {
        select(fields) {
          calls.push({ fields });
          return {
            in(column, values) {
              calls.push({ column, values });
              return {
                order(orderColumn, orderOptions) {
                  calls.push({ orderColumn, orderOptions });
                  return {
                    range(from, to) {
                      calls.push({ from, to });
                      return { data: [], error: null };
                    },
                  };
                },
              };
            },
          };
        },
      };
    },
  };

  const result = await fetchExamQuestionsWithAuthor(supabase, ['e-1', 'e-2']);

  assert.equal(calls[0].table, 'exam_questions');
  assert.equal(calls[1].fields, 'exam_id, questions!inner(created_by)');
  assert.equal(calls[2].column, 'exam_id');
  assert.deepEqual(calls[2].values, ['e-1', 'e-2']);
  assert.equal(calls[3].orderColumn, 'id');
  assert.deepEqual(calls[3].orderOptions, { ascending: true });
  assert.deepEqual(calls[4], { from: 0, to: 999 });
  assert.deepEqual(result, { data: [] });
});

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

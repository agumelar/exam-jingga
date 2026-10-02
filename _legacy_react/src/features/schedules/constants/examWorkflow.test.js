import test from 'node:test';
import assert from 'node:assert/strict';
import {
  EXAM_STATUS,
  isExamReadyForStudent,
  resolveStatusAfterQuestionSave,
  canTransitionStatus,
} from './examWorkflow.js';

test('UH full question set goes to validated', () => {
  assert.equal(
    resolveStatusAfterQuestionSave({ examType: 'UH', isFull: true }),
    EXAM_STATUS.VALIDATED
  );
});

test('PTS full question set goes to waiting_validation', () => {
  assert.equal(
    resolveStatusAfterQuestionSave({ examType: 'PTS', isFull: true }),
    EXAM_STATUS.WAITING_VALIDATION
  );
});

test('student readiness accepts validated and ready/live compatibility', () => {
  assert.equal(isExamReadyForStudent('validated'), true);
  assert.equal(isExamReadyForStudent('ready'), true);
  assert.equal(isExamReadyForStudent('live'), true);
  assert.equal(isExamReadyForStudent('pending_selection'), false);
});

test('guru can unlock only UH from validated/ready', () => {
  assert.equal(
    canTransitionStatus({
      role: 'guru',
      examType: 'UH',
      from: 'validated',
      to: 'pending_selection',
    }),
    true
  );
  assert.equal(
    canTransitionStatus({
      role: 'guru',
      examType: 'PTS',
      from: 'validated',
      to: 'pending_selection',
    }),
    false
  );
});

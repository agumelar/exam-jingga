export const EXAM_STATUS = {
  PENDING_SELECTION: 'pending_selection',
  WAITING_VALIDATION: 'waiting_validation',
  VALIDATED: 'validated',
  READY: 'ready',
  LIVE: 'live',
};

const STUDENT_READY_STATUS = new Set([
  EXAM_STATUS.VALIDATED,
  EXAM_STATUS.READY,
  EXAM_STATUS.LIVE,
]);

function normalize(value) {
  return String(value || '').trim().toLowerCase();
}

export function isExamReadyForStudent(status) {
  return STUDENT_READY_STATUS.has(normalize(status));
}

export function resolveStatusAfterQuestionSave({ examType, isFull }) {
  if (!isFull) return null;
  return normalize(examType) === 'uh'
    ? EXAM_STATUS.VALIDATED
    : EXAM_STATUS.WAITING_VALIDATION;
}

export function canTransitionStatus({ role, examType, from, to }) {
  const normalizedRole = normalize(role);
  const normalizedType = normalize(examType);
  const normalizedFrom = normalize(from);
  const normalizedTo = normalize(to);

  const adminCanVerify =
    normalizedRole === 'admin' &&
    normalizedFrom === EXAM_STATUS.WAITING_VALIDATION &&
    normalizedTo === EXAM_STATUS.VALIDATED;

  const guruCanUnlockUh =
    normalizedRole === 'guru' &&
    normalizedType === 'uh' &&
    (normalizedFrom === EXAM_STATUS.VALIDATED ||
      normalizedFrom === EXAM_STATUS.READY) &&
    normalizedTo === EXAM_STATUS.PENDING_SELECTION;

  return adminCanVerify || guruCanUnlockUh;
}

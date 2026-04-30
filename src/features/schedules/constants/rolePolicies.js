const GURU_ALLOWED_CREATE_TYPES = new Set(['UH']);
const ADMIN_ALLOWED_CREATE_TYPES = new Set(['PTS', 'PAS/PAT', 'SAJ']);

function normalize(value) {
  return String(value || '').trim().toLowerCase();
}

export function canCreateScheduleType(role, examType) {
  const normalizedRole = normalize(role);
  const normalizedType = String(examType || '').trim().toUpperCase();

  if (normalizedRole === 'guru') {
    return GURU_ALLOWED_CREATE_TYPES.has(normalizedType);
  }

  if (normalizedRole === 'admin') {
    return ADMIN_ALLOWED_CREATE_TYPES.has(normalizedType);
  }

  return false;
}

export function canEditSchedule({ role, examType }) {
  const normalizedRole = normalize(role);
  const normalizedType = String(examType || '').trim().toUpperCase();

  if (normalizedRole === 'admin') return true;
  if (normalizedRole === 'guru') return normalizedType === 'UH';

  return false;
}

export function canVerifySchedule(role) {
  return normalize(role) === 'admin';
}

export function canUnlockUh(role) {
  return normalize(role) === 'guru';
}

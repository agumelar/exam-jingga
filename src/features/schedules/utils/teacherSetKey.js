export function buildTeacherSetKey(teacherIds = []) {
  if (!Array.isArray(teacherIds) || teacherIds.length === 0) return '';
  const unique = Array.from(
    new Set(teacherIds.filter(Boolean).map((id) => String(id)))
  ).sort();
  return unique.join('|');
}

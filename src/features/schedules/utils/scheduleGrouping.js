export function buildTeacherSetGroups(assignments = []) {
  if (!Array.isArray(assignments) || assignments.length === 0) {
    return [];
  }

  const teachersByClass = new Map();
  assignments.forEach((assignment) => {
    const classId = assignment.classes?.id ?? assignment.class_id;
    const teacherId = assignment.teacher_id;
    if (!classId || !teacherId) return;

    if (!teachersByClass.has(classId)) teachersByClass.set(classId, new Set());
    teachersByClass.get(classId).add(teacherId);
  });

  const groupMap = new Map();
  teachersByClass.forEach((teacherSet, classId) => {
    const sortedTeachers = Array.from(teacherSet).sort();
    const key = sortedTeachers.join('|');
    if (!groupMap.has(key)) {
      groupMap.set(key, { teacherSet: sortedTeachers, classIds: [] });
    }
    groupMap.get(key).classIds.push(classId);
  });

  return Array.from(groupMap.values());
}

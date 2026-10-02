export function buildTeacherQuotaMap(assignments = [], totalTarget = 0) {
  if (!Array.isArray(assignments) || assignments.length === 0) {
    return {};
  }

  const classTeachers = new Map();
  const teacherClasses = new Map();

  assignments.forEach((assignment) => {
    const classId = assignment.classes?.id ?? assignment.class_id;
    const teacherId = assignment.teacher_id;
    if (!classId || !teacherId) return;

    if (!classTeachers.has(classId)) classTeachers.set(classId, new Set());
    classTeachers.get(classId).add(teacherId);

    if (!teacherClasses.has(teacherId)) teacherClasses.set(teacherId, new Set());
    teacherClasses.get(teacherId).add(classId);
  });

  const teacherMaxCount = new Map();
  teacherClasses.forEach((classSet, teacherId) => {
    let maxCount = 1;
    classSet.forEach((classId) => {
      const count = classTeachers.get(classId)?.size ?? 1;
      if (count > maxCount) maxCount = count;
    });
    teacherMaxCount.set(teacherId, maxCount);
  });

  const quotaMap = {};
  const grouped = new Map();
  teacherMaxCount.forEach((maxCount, teacherId) => {
    if (!grouped.has(maxCount)) grouped.set(maxCount, []);
    grouped.get(maxCount).push(teacherId);
  });

  grouped.forEach((teacherIds, maxCount) => {
    const baseQuota = Math.floor(Number(totalTarget) / maxCount);
    const remainder = Number(totalTarget) % maxCount;
    teacherIds
      .slice()
      .sort()
      .forEach((teacherId, index) => {
        quotaMap[teacherId] = baseQuota + (index < remainder ? 1 : 0);
      });
  });

  return quotaMap;
}

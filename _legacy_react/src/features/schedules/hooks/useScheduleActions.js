import { useMemo } from 'react';
import Swal from 'sweetalert2';
import {
  EXAM_STATUS,
  canTransitionStatus,
  canCreateScheduleType,
  canEditSchedule,
  canUnlockUh,
  canVerifySchedule,
} from '../constants';
import {
  buildScheduleDateRange,
  buildTeacherQuotaMap,
  buildTeacherSetGroups,
} from '../utils';
import { buildExamPayload } from '../utils/payloadBuilders';
import {
  createExam,
  getSchedulesByExamId,
  insertSchedules,
  updateExamById,
  updateScheduleById,
  verifyExamStatus,
  unlockUHExam,
} from '../services/scheduleService';

function parseLevelFromClassName(className) {
  return parseInt(String(className || '').split(' ')[0], 10);
}


export function useScheduleActions({
  supabase,
  userRole,
  myTeacherId,
  allAssignments,
  exams,
  refreshSchedules,
  setShowModal,
  setEditingId,
  setFormData,
  initialForm,
  setSaving,
}) {
  const assignmentByLevelSubject = useMemo(
    () => (level, subjectId) =>
      allAssignments.filter(
        (item) =>
          parseLevelFromClassName(item.classes?.name) === Number(level) &&
          item.subject_id === subjectId
      ),
    [allAssignments]
  );

  const handleVerify = async (examId) => {
    if (!canVerifySchedule(userRole)) {
      throw new Error('Role ini tidak boleh verifikasi ujian.');
    }

    const { isConfirmed } = await Swal.fire({
      title: 'Verifikasi Ujian?',
      text: 'Setelah diverifikasi, soal siap diakses oleh siswa.',
      icon: 'info',
      showCancelButton: true,
      confirmButtonText: 'Ya, Verifikasi!',
    });

    if (!isConfirmed) return;

    await verifyExamStatus(supabase, examId);
    await refreshSchedules();
    await Swal.fire('Terverifikasi!', 'Ujian siap dilaksanakan.', 'success');
  };

  const handleUnlockUH = async ({ examId, examType, currentStatus }) => {
    if (!canUnlockUh(userRole)) {
      throw new Error('Role ini tidak boleh membuka kunci ujian.');
    }

    if (
      !canTransitionStatus({
        role: userRole,
        examType,
        from: currentStatus,
        to: EXAM_STATUS.PENDING_SELECTION,
      })
    ) {
      throw new Error('Transisi status tidak diizinkan.');
    }

    const { isConfirmed } = await Swal.fire({
      title: 'Buka Kunci Ujian?',
      text: "Status ujian akan kembali jadi 'Tunggu Soal'. Siswa tidak bisa mengakses ujian ini sampai Anda menyimpan soal kembali.",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Ya, Buka Kunci!',
    });

    if (!isConfirmed) return;

    await unlockUHExam(supabase, examId);
    await refreshSchedules();
    await Swal.fire('Terbuka!', 'Silakan pilih atau revisi ulang soal Anda.', 'success');
  };

  const updateExistingSchedule = async ({
    editingId,
    formData,
    finalStart,
    finalEnd,
    totalTarget,
  }) => {
    const scheduleData = exams.find((item) => item.id === editingId);
    if (!scheduleData) {
      throw new Error('Data jadwal tidak ditemukan. Coba refresh halaman.');
    }

    if (!canEditSchedule({ role: userRole, examType: scheduleData.exams?.type })) {
      throw new Error('Role ini tidak boleh edit jadwal ini.');
    }

    await updateExamById(supabase, scheduleData.exam_id, {
      title: buildExamPayload({
        type: formData.type,
        title: formData.title,
        subType: formData.sub_type,
        duration: formData.duration,
        targetQuestionCount: totalTarget,
        level: formData.level,
        subjectId: formData.subject_id,
        teacherId: scheduleData.teacher_id,
        token: formData.token,
      }).title,
      duration: Number(formData.duration),
      target_question_count: totalTarget,
      type: formData.type,
    });

    const { data: existingSchedules } = await getSchedulesByExamId(
      supabase,
      scheduleData.exam_id
    );

    if (['PAS/PAT', 'SAJ'].includes(formData.type)) {
      const matchedAssignments = assignmentByLevelSubject(
        formData.level,
        formData.subject_id
      );
      if (matchedAssignments.length === 0) {
        throw new Error('Tidak ada guru yang ditugaskan untuk mapel dan jenjang ini.');
      }

      const currentTeacherIds = new Set(
        (existingSchedules || []).map((s) => s.teacher_id)
      );
      const groupAssignments = matchedAssignments.filter((assignment) =>
        currentTeacherIds.has(assignment.teacher_id)
      );

      const quotaMap = buildTeacherQuotaMap(groupAssignments, totalTarget);

      for (let index = 0; index < (existingSchedules || []).length; index += 1) {
        const schedule = existingSchedules[index];
        const quota = quotaMap[schedule.teacher_id] ?? 0;

        await updateScheduleById(supabase, schedule.id, {
          start_time: finalStart,
          end_time: finalEnd,
          token: formData.token,
          session_no: formData.session_no === 'Semua Sesi' ? 0 : Number(formData.session_no),
          teacher_quota: quota,
        });
      }

      return;
    }

    await updateScheduleById(supabase, editingId, {
      start_time: finalStart,
      end_time: finalEnd,
      token: formData.token,
      session_no: formData.session_no === 'Semua Sesi' ? 0 : Number(formData.session_no),
      teacher_quota: totalTarget,
    });
  };

  const createSingleTeacherSchedule = async ({
    formData,
    finalStart,
    finalEnd,
    totalTarget,
  }) => {
    const selectedTeacherId =
      userRole === 'guru' ? myTeacherId : formData.teacher_id;
    if (!selectedTeacherId) {
      throw new Error('Guru pengampu wajib dipilih.');
    }

    const payload = buildExamPayload({
      type: formData.type,
      title: formData.title,
      subType: formData.sub_type,
      duration: formData.duration,
      targetQuestionCount: totalTarget,
      level: formData.level,
      subjectId: formData.subject_id,
      teacherId: selectedTeacherId,
      token: formData.token,
    });

    const { data: examData, error } = await createExam(supabase, payload);
    if (error) throw error;

    await insertSchedules(supabase, [
      {
        exam_id: examData.id,
        class_id: formData.class_id,
        teacher_id: selectedTeacherId,
        start_time: finalStart,
        end_time: finalEnd,
        token: formData.token,
        session_no: formData.session_no === 'Semua Sesi' ? 0 : Number(formData.session_no),
        status: 'active',
        teacher_quota: totalTarget,
      },
    ]);
  };

  const createCollabSchedule = async ({
    formData,
    finalStart,
    finalEnd,
    totalTarget,
  }) => {
    const matchedAssignments = assignmentByLevelSubject(
      formData.level,
      formData.subject_id
    );
    if (matchedAssignments.length === 0) {
      throw new Error('Tidak ada guru yang ditugaskan untuk mapel dan jenjang ini.');
    }

    const teacherSetGroups = buildTeacherSetGroups(matchedAssignments);
    if (teacherSetGroups.length === 0) {
      throw new Error('Tidak ada grup guru yang valid untuk mapel dan jenjang ini.');
    }

    for (const group of teacherSetGroups) {
      const examPayload = buildExamPayload({
        type: formData.type,
        title: formData.title,
        subType: formData.sub_type,
        duration: formData.duration,
        targetQuestionCount: totalTarget,
        level: formData.level,
        subjectId: formData.subject_id,
        teacherId: myTeacherId,
        token: formData.token,
      });

      const { data: examData, error } = await createExam(supabase, examPayload);
      if (error) throw error;

      const groupAssignments = matchedAssignments.filter((assignment) =>
        group.classIds.includes(assignment.classes?.id ?? assignment.class_id)
      );
      const quotaMap = buildTeacherQuotaMap(groupAssignments, totalTarget);

      const scheduleRows = group.teacherSet.map((teacherId) => ({
        exam_id: examData.id,
        class_id: null,
        teacher_id: teacherId,
        start_time: finalStart,
        end_time: finalEnd,
        token: formData.token,
        session_no: formData.session_no === 'Semua Sesi' ? 0 : Number(formData.session_no),
        status: 'active',
        teacher_quota: quotaMap[teacherId] ?? 0,
      }));

      await insertSchedules(supabase, scheduleRows);
    }
  };

  const handleSaveSchedule = async ({ editingId, formData }) => {
    setSaving(true);
    try {
      if (!formData.subject_id) {
        throw new Error('Mapel wajib dipilih!');
      }

      if (!canCreateScheduleType(userRole, formData.type) && !editingId) {
        throw new Error('Role ini tidak boleh membuat tipe jadwal tersebut.');
      }

      const { finalStart, finalEnd } = buildScheduleDateRange({
        startTime: formData.start_time,
        duration: formData.duration,
      });
      const totalTarget = Number(formData.target_question_count);

      if (editingId) {
        await updateExistingSchedule({
          editingId,
          formData,
          finalStart,
          finalEnd,
          totalTarget,
        });
      } else if (formData.type === 'UH' || formData.type === 'PTS') {
        await createSingleTeacherSchedule({
          formData,
          finalStart,
          finalEnd,
          totalTarget,
        });
      } else {
        await createCollabSchedule({
          formData,
          finalStart,
          finalEnd,
          totalTarget,
        });
      }

      await refreshSchedules();
      setShowModal(false);
      setEditingId(null);
      setFormData(initialForm);
      await Swal.fire('Berhasil!', 'Jadwal tersimpan.', 'success');
    } finally {
      setSaving(false);
    }
  };

  return {
    handleVerify,
    handleUnlockUH,
    handleSaveSchedule,
  };
}

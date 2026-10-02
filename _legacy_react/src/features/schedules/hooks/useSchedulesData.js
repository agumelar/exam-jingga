import { useCallback, useEffect, useState } from 'react';
import {
  fetchAssignments,
  fetchExamQuestionsWithAuthor,
  fetchSchedulesWithRelations,
  mapScheduleCards,
} from '../services/scheduleService';
import { attachTeacherProgress } from '../utils';

function parseSession() {
  const raw = localStorage.getItem('user_session');
  if (!raw) return null;

  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

export function useSchedulesData({ supabase, navigate }) {
  const [loading, setLoading] = useState(false);
  const [userRole, setUserRole] = useState('');
  const [myTeacherId, setMyTeacherId] = useState(null);
  const [allAssignments, setAllAssignments] = useState([]);
  const [exams, setExams] = useState([]);

  const refreshSchedules = useCallback(
    async (sessionData = parseSession()) => {
      if (!sessionData) return;

      setLoading(true);
      try {
        const { data: schedules } = await fetchSchedulesWithRelations(supabase);

        if (schedules) {
          const examIds = schedules
            .map((schedule) => schedule.exam_id)
            .filter(Boolean);
          const uniqueExamIds = Array.from(new Set(examIds));
          const { data: allQuestions } = await fetchExamQuestionsWithAuthor(
            supabase,
            uniqueExamIds
          );
          const cleaned = mapScheduleCards(schedules, allQuestions);
          const withProgress = attachTeacherProgress(cleaned);

          const filteredByRole =
            String(sessionData.role || '').toLowerCase() === 'guru'
              ? withProgress.filter((item) => item.teacher_id === sessionData.id)
              : withProgress;

          setExams(filteredByRole);
        } else {
          setExams([]);
        }
      } finally {
        setLoading(false);
      }
    },
    [supabase]
  );

  useEffect(() => {
    let isMounted = true;

    const loadInitialData = async () => {
      const userData = parseSession();
      if (!userData) {
        navigate('/login');
        return;
      }

      if (!isMounted) return;
      setMyTeacherId(userData.id);
      setUserRole(String(userData.role || '').toLowerCase());

      const { data: assignData } = await fetchAssignments(supabase);
      if (isMounted) {
        setAllAssignments(assignData || []);
      }

      await refreshSchedules(userData);
    };

    void loadInitialData();

    return () => {
      isMounted = false;
    };
  }, [navigate, refreshSchedules, supabase]);

  return {
    loading,
    userRole,
    myTeacherId,
    allAssignments,
    exams,
    refreshSchedules,
  };
}

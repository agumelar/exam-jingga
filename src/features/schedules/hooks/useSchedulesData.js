import { useCallback, useEffect, useState } from 'react';
import {
  fetchAssignments,
  fetchExamQuestionsWithAuthor,
  fetchSchedulesWithRelations,
  mapScheduleCards,
} from '../services/scheduleService';

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
          const { data: allQuestions } = await fetchExamQuestionsWithAuthor(supabase);
          const cleaned = mapScheduleCards(schedules, allQuestions);

          const filteredByRole =
            String(sessionData.role || '').toLowerCase() === 'guru'
              ? cleaned.filter((item) => item.teacher_id === sessionData.id)
              : cleaned;

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

# Exam Interface Quality Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix exam interface quality issues around option filtering, unmount safety, cheat detection guards, and submit gating.

**Architecture:** Keep all changes scoped to the existing `ExamInterface` component. Adjust data shaping for options, add cancellation checks around async start flow, and remove an early submit guard. No new modules or restructuring.

**Tech Stack:** React, Supabase, SweetAlert2.

---

## File Structure

- Modify: `src/pages/ExamInterface.jsx` (startExam flow, question shaping, cheat detection guard, submitExam gating)

### Task 1: Add startExam unmount/cancel guard

**Files:**
- Modify: `src/pages/ExamInterface.jsx`
- Test: none (per instruction)

- [ ] **Step 1: Add a cancel flag in the startExam caller**

```jsx
useEffect(() => {
  let cancelled = false;
  const user = JSON.parse(localStorage.getItem('user_session'));
  if (!user || user.role !== 'siswa') {
    navigate('/login');
  } else {
    startExam(user.id, () => cancelled);
  }
  return () => { cancelled = true; };
}, [examId]);
```

- [ ] **Step 2: Accept isCancelled in startExam and guard after awaits**

```jsx
const startExam = async (studentId, isCancelled = () => false) => {
  try {
    const { data: schData } = await supabase
      .from('schedules')
      .select(`*, exams(*, subjects(name))`)
      .eq('id', examId)
      .single();

    if (isCancelled()) return;
    if (!schData) throw new Error("Ujian tidak ditemukan");
    setSchedule(schData);

    let currentSession;
    const { data: existingSessions } = await supabase
      .from('exam_sessions')
      .select('*')
      .eq('student_id', studentId)
      .eq('schedule_id', examId)
      .order('started_at', { ascending: false })
      .limit(1);

    if (isCancelled()) return;
    // ...keep existing logic...

    setSessionId(currentSession.id);

    if (isCancelled()) return;
    // ...timer logic...

    setTimeLeft(remaining);

    if (isCancelled()) return;
    // ...fetch questions and set state...

    setQuestions(fetchedQuestions);
    setLoading(false);
  } catch (error) {
    if (isCancelled()) return;
    Swal.fire('Akses Ditolak', error.message, 'error');
    navigate('/student-dashboard');
  }
};
```

### Task 2: Filter display options to existing choices

**Files:**
- Modify: `src/pages/ExamInterface.jsx`
- Test: none (per instruction)

- [ ] **Step 1: Replace displayOptions building with filtered options**

```jsx
const qData = await fetchExamQuestionsWithFallback(schData.exam_id, allowedTeacherIdsNormal);

let fetchedQuestions = shuffleArray((qData || []).map(item => {
  const options = ['a', 'b', 'c', 'd', 'e'].filter((opt) => item.questions?.[`option_${opt}`]);
  const displayOptions = shuffleArray(options.length ? options : ['a', 'b', 'c', 'd', 'e']);
  return {
    ...item.questions,
    displayOptions,
  };
}).filter(Boolean));
```

### Task 3: Guard cheat detection with missing sessionId

**Files:**
- Modify: `src/pages/ExamInterface.jsx`
- Test: none (per instruction)

- [ ] **Step 1: Add early return in handleCheatDetection**

```jsx
const handleCheatDetection = async () => {
  if (!sessionId) return;
  const now = Date.now();
  if (now - lastCheatTime.current < 2000) return;
  lastCheatTime.current = now;
  // ...rest of logic...
};
```

### Task 4: Remove submitExam early-return guard

**Files:**
- Modify: `src/pages/ExamInterface.jsx`
- Test: none (per instruction)

- [ ] **Step 1: Remove the timeLeft guard in submitExam**

```jsx
const submitExam = async (isAuto = false) => {
  let correct = 0;
  questions.forEach(q => {
    const kunci = q.correct_answer || q.answer_key || q.answer;
    if (answers[q.id]?.toUpperCase() === kunci?.toUpperCase()) correct++;
  });
  // ...rest of submit flow...
};
```

---

## Self-Review Checklist

1. Spec coverage: Task 1 covers unmount guard; Task 2 covers options filtering; Task 3 adds session guard; Task 4 removes submit guard.
2. Placeholder scan: no TODO/TBD or vague steps.
3. Type consistency: function signatures and variable names align with existing code.

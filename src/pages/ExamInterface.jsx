import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { ChevronLeft, ChevronRight, AlertTriangle, LayoutGrid, CheckCircle2, RefreshCw, Clock, HelpCircle } from 'lucide-react';
import Swal from 'sweetalert2';
import { useExamAnswerSync } from '../features/examSessions';
import { toSQLDateTime } from '../features/schedules/utils';
import {
  DEFAULT_DRIFT_THRESHOLD_MS,
  DEFAULT_DRIFT_TICK_MS,
  DEFAULT_FOCUS_POLL_MS,
  isDrift
} from '../features/examSessions/utils/antiCheatSignals.js';

const ExamInterface = () => {
  const { examId } = useParams(); 
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [timeLeft, setTimeLeft] = useState(0);
  const [loading, setLoading] = useState(true);
  
  const [sessionId, setSessionId] = useState(null);
  const [isLocked, setIsLocked] = useState(false);
  const [violationCount, setViolationCount] = useState(0);
  const [debugLogs, setDebugLogs] = useState([]);
  const [debugStatus, setDebugStatus] = useState({
    hidden: false,
    hasFocus: null,
    lastDelta: null
  });
  const [debugCopied, setDebugCopied] = useState(false);
  const [debugAntiCheat] = useState(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const param = params.get('debug');
      return param === '1' || param === 'true' || localStorage.getItem('anticheat_debug') === '1';
    } catch (err) {
      return false;
    }
  });

  const {
    answers,
    doubts: doubtfulQuestions,
    setAnswers,
    setDoubts: setDoubtfulQuestions,
    enqueue,
    flush,
    clearCache,
  } = useExamAnswerSync({ sessionId, isLocked });
  
  const lastCheatTime = useRef(0);
  const lastTickRef = useRef(0);

  const pushDebugLog = (payload) => {
    if (!debugAntiCheat) return;
    const entry = {
      t: toSQLDateTime(new Date()).slice(11, 19),
      ...payload
    };
    setDebugLogs((prev) => [...prev, entry].slice(-40));
  };

  const buildDebugText = () => {
    const lines = [
      `time=${toSQLDateTime(new Date())}`,
      `url=${window.location.href}`,
      `hidden=${String(debugStatus.hidden)}`,
      `focus=${debugStatus.hasFocus === null ? 'n/a' : String(debugStatus.hasFocus)}`,
      `delta=${debugStatus.lastDelta === null ? '-' : `${debugStatus.lastDelta}ms`}`,
      `violationCount=${violationCount}`,
      `userAgent=${navigator.userAgent}`,
      'events:'
    ];
    const events = [...debugLogs]
      .reverse()
      .map((log) => {
        const delta = typeof log.delta === 'number' ? `${log.delta}ms` : '-';
        const focus = log.focus === null ? 'n/a' : String(log.focus);
        return `${log.t} ${log.event} hidden=${String(log.hidden)} focus=${focus} cooldown=${String(log.cooldown)} delta=${delta}`;
      });
    return [...lines, ...events].join('\n');
  };

  const handleCopyDebug = async () => {
    const text = buildDebugText();
    try {
      await navigator.clipboard.writeText(text);
      setDebugCopied(true);
      setTimeout(() => setDebugCopied(false), 1500);
    } catch (err) {
      window.prompt('Salin log di bawah ini:', text);
    }
  };

  const shuffleArray = (array) => {
    let newArr = [...array];
    for (let i = newArr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [newArr[i], newArr[j]] = [newArr[j], newArr[i]];
    }
    return newArr;
  };

  useEffect(() => {
    let cancelled = false;
    const user = JSON.parse(localStorage.getItem('user_session'));
    if (!user || user.role !== 'siswa') {
      navigate('/login');
      return () => { cancelled = true; };
    }
    startExam(user.id, () => cancelled);
    return () => { cancelled = true; };
  }, [examId]);

  const fetchExamQuestionsWithFallback = async (examIdValue, allowedTeacherIds = []) => {
    const shouldFilterByTeacher = Array.isArray(allowedTeacherIds) && allowedTeacherIds.length > 0;

    let filteredData = [];
    if (shouldFilterByTeacher) {
      const { data, error } = await supabase
        .from('exam_questions')
        .select('question_id, questions!inner(*)')
        .eq('exam_id', examIdValue)
        .in('questions.created_by', allowedTeacherIds)
        .order('order_number', { ascending: true });

      if (error) throw error;
      filteredData = data || [];
    }

    if (!shouldFilterByTeacher || filteredData.length === 0) {
      const { data: fallbackData, error: fallbackErr } = await supabase
        .from('exam_questions')
        .select('question_id, questions!inner(*)')
        .eq('exam_id', examIdValue)
        .order('order_number', { ascending: true });

      if (fallbackErr) throw fallbackErr;
      return fallbackData || [];
    }

    return filteredData;
  };

  const startExam = async (studentId, isCancelled = () => false) => {
    const shouldCancel = () => (typeof isCancelled === 'function' ? isCancelled() : false);
    try {
      const { data: schData } = await supabase
        .from('schedules')
        .select(`*, exams(*, subjects(name))`)
        .eq('id', examId)
        .single();

      if (shouldCancel()) return;
      
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

      const existingSession = existingSessions?.[0];

      if (existingSession) {
        let normalizedSession = existingSession;

        if (normalizedSession.status === 'finished') {
          const { data: existingAnswer } = await supabase
            .from('student_answers')
            .select('id')
            .eq('session_id', normalizedSession.id)
            .limit(1)
            .maybeSingle();

          if (!existingAnswer) {
            const resetStart = toSQLDateTime(new Date());
            await supabase
              .from('exam_sessions')
              .update({
                status: 'active',
                started_at: resetStart,
                finished_at: null,
                score: 0,
                violation_count: 0,
              })
              .eq('id', normalizedSession.id);

            normalizedSession = {
              ...normalizedSession,
              status: 'active',
              started_at: resetStart,
              finished_at: null,
              score: 0,
              violation_count: 0,
            };
          } else {
            throw new Error("Ujian ini sudah diselesaikan!");
          }
        }
        if (normalizedSession.status === 'locked') {
          if (shouldCancel()) return;
          setSessionId(normalizedSession.id);
          setIsLocked(true);
          setLoading(false);
          return; 
        }
        setViolationCount(normalizedSession.violation_count || 0);
        currentSession = normalizedSession;
      } else {
        const { data: newSession, error: nsErr } = await supabase
          .from('exam_sessions')
          .insert([{ student_id: studentId, schedule_id: examId, status: 'active' }])
          .select().single();
        if (nsErr) throw nsErr;
        currentSession = newSession;
      }
      if (shouldCancel()) return;
      setSessionId(currentSession.id);

      // --- TIMER LOGIC (DENGAN PERBAIKAN AUTO-SUBMIT ADIL) ---
      // INI BARIS YANG TADI GUE POTONG, SEKARANG GUE BALIKIN UTUH!
      const durationInSeconds = (schData.exams?.duration || 60) * 60;
      const startTime = new Date(currentSession.started_at).getTime();
      const now = new Date().getTime();
      const timePassed = Math.floor((now - startTime) / 1000);
      let remaining = durationInSeconds - timePassed;
      
      if (remaining <= 0) { 
         const { data: anyAnswer } = await supabase
           .from('student_answers')
           .select('id')
           .eq('session_id', currentSession.id)
           .limit(1)
           .maybeSingle();

         if (!anyAnswer) {
            const resetStart = toSQLDateTime(new Date());
           await supabase
             .from('exam_sessions')
             .update({
               status: 'active',
               started_at: resetStart,
               finished_at: null,
               score: 0,
               violation_count: 0,
             })
             .eq('id', currentSession.id);
           remaining = durationInSeconds;
         } else {
           const { data: studentData } = await supabase.from('students').select('class_id').eq('id', studentId).single();
           const { data: myTeachers } = await supabase.from('teacher_assignments').select('teacher_id')
             .eq('class_id', studentData?.class_id).eq('subject_id', schData.exams.subject_id);
           const allowedTeacherIds = myTeachers?.map(t => t.teacher_id) || [];

           const qData = await fetchExamQuestionsWithFallback(schData.exam_id, allowedTeacherIds);
           const { data: aData } = await supabase.from('student_answers').select('question_id, chosen_answer').eq('session_id', currentSession.id);

           let dbCorrect = 0;
           const dbQuestions = qData ? qData.map(q => q.questions).filter(Boolean) : [];

           dbQuestions.forEach(q => {
             const ans = aData?.find(a => String(a.question_id) === String(q.id));
             const kunci = q.correct_answer || q.answer_key || q.kunci_jawaban || q.answer;
             if (ans && ans.chosen_answer && kunci) {
               if (String(ans.chosen_answer).trim().toUpperCase() === String(kunci).trim().toUpperCase()) {
                 dbCorrect++;
               }
             }
           });

           const dbScore = dbQuestions.length > 0 ? Math.round((dbCorrect / dbQuestions.length) * 100) : 0;

            await supabase.from('exam_sessions').update({
              status: 'finished',
              finished_at: toSQLDateTime(new Date()),
              score: dbScore,
            }).eq('id', currentSession.id);

            await Swal.fire({
              title: 'Waktu Habis!',
              html: `Waktu ujian telah berakhir saat sesi Anda tertahan.<br/>Sistem telah menyimpan otomatis sisa jawaban Anda.<br/><br/>Skor Anda: <span style="font-size:36px; font-weight:900; color:#ea580c;">${dbScore}</span>`,
              icon: 'info',
              allowOutsideClick: false,
            });

            navigate('/student-dashboard');
            return;
          }
      }
      if (shouldCancel()) return;
      setTimeLeft(remaining);

      // Fetch Questions (Untuk Ujian Normal)
      const { data: studentDataNormal } = await supabase.from('students').select('class_id').eq('id', studentId).single();
      const { data: myTeachersNormal } = await supabase.from('teacher_assignments').select('teacher_id')
        .eq('class_id', studentDataNormal?.class_id).eq('subject_id', schData.exams.subject_id);
      
      const allowedTeacherIdsNormal = myTeachersNormal?.map(t => t.teacher_id) || [];

      const qData = await fetchExamQuestionsWithFallback(schData.exam_id, allowedTeacherIdsNormal);
      if (shouldCancel()) return;

      let fetchedQuestions = shuffleArray((qData || []).map(item => {
        const options = ['a', 'b', 'c', 'd', 'e'].filter((opt) => item.questions?.[`option_${opt}`]);
        return {
          ...item.questions,
          displayOptions: shuffleArray(options.length ? options : ['a', 'b', 'c', 'd', 'e']),
        };
      }).filter(Boolean));

      setQuestions(fetchedQuestions);
      if (shouldCancel()) return;
      setLoading(false);
    } catch (error) {
      if (shouldCancel()) return;
      Swal.fire('Akses Ditolak', error.message, 'error');
      navigate('/student-dashboard');
    }
  };

  // --- LOGIKA ANTI CHEAT (FIXED UNTUK PTS & UH) ---
  useEffect(() => {
    if (loading || isLocked || !sessionId || !schedule) return;

    const reportViolation = async (source, meta = {}) => {
      if (!sessionId) return;
      const now = Date.now();
      const cooldown = now - lastCheatTime.current < 2000;
      const hasFocus = typeof document.hasFocus === 'function' ? document.hasFocus() : null;
      pushDebugLog({
        event: source,
        hidden: document.hidden,
        focus: hasFocus,
        cooldown,
        ...meta
      });
      if (cooldown) return;
      lastCheatTime.current = now;

      const newCount = violationCount + 1;
      setViolationCount(newCount);

      const examType = schedule.exams?.type;
      const isStrictExam = !['UH', 'PTS'].includes(examType);
      const isNowLocked = isStrictExam && newCount >= 2;

      await supabase
        .from('exam_sessions')
        .update({
          violation_count: newCount,
          status: isNowLocked ? 'locked' : 'active'
        })
        .eq('id', sessionId);

      if (!isStrictExam) {
        Swal.fire('Peringatan!', 'Tetap fokus pada lembar ujian!', 'warning');
        return;
      }

      if (newCount === 1) {
        Swal.fire({
          title: 'PERINGATAN!',
          text: 'Dilarang keluar halaman ujian atau akun Anda akan TERKUNCI!',
          icon: 'warning'
        });
        return;
      }

      if (isNowLocked) setIsLocked(true);
    };

    const onVisibility = () => {
      if (document.hidden) reportViolation('visibility');
    };
    const onBlur = () => reportViolation('blur');
    const onPageHide = () => reportViolation('pagehide');
    const onFreeze = () => reportViolation('freeze');

    document.addEventListener('visibilitychange', onVisibility);
    window.addEventListener('blur', onBlur);
    window.addEventListener('pagehide', onPageHide);
    document.addEventListener('freeze', onFreeze);

    const driftTimer = setInterval(() => {
      const now = performance.now();
      if (lastTickRef.current) {
        const delta = now - lastTickRef.current;
        if (debugAntiCheat) {
          const hasFocus = typeof document.hasFocus === 'function' ? document.hasFocus() : null;
          setDebugStatus({
            hidden: document.hidden,
            hasFocus,
            lastDelta: Math.round(delta)
          });
        }
        if (isDrift(delta, DEFAULT_DRIFT_THRESHOLD_MS)) {
          reportViolation('drift', { delta: Math.round(delta) });
        }
      }
      lastTickRef.current = now;
    }, DEFAULT_DRIFT_TICK_MS);

    const focusTimer = setInterval(() => {
      if (!document.hidden && typeof document.hasFocus === 'function' && !document.hasFocus()) {
        reportViolation('focus');
      }
    }, DEFAULT_FOCUS_POLL_MS);

    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('blur', onBlur);
      window.removeEventListener('pagehide', onPageHide);
      document.removeEventListener('freeze', onFreeze);
      clearInterval(driftTimer);
      clearInterval(focusTimer);
    };
  }, [loading, isLocked, sessionId, schedule, violationCount, debugAntiCheat]);

  // --- RADAR AUTO-UNLOCK ---
  useEffect(() => {
    let interval;
    if (isLocked && sessionId) {
      interval = setInterval(async () => {
        try {
          const { data } = await supabase
            .from('exam_sessions')
            .select('status, violation_count')
            .eq('id', sessionId)
            .single();

          if (data && data.status === 'active') {
            setIsLocked(false);
            setViolationCount(data.violation_count || 0);
            Swal.fire({
              title: 'Akses Dibuka!',
              text: 'Pengawas telah membuka sesi Anda. Silakan lanjutkan ujian.',
              icon: 'success',
              timer: 3000,
              showConfirmButton: false
            });
          }
        } catch (err) {
          console.error("Gagal mengecek status:", err);
        }
      }, 3000); 
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isLocked, sessionId]);

  // --- TIMER ---
  useEffect(() => {
    if (loading || isLocked || timeLeft <= 0) return;
    const timer = setInterval(() => setTimeLeft(prev => {
      if (prev <= 1) { submitExam(true); return 0; }
      return prev - 1;
    }), 1000);
    return () => clearInterval(timer);
  }, [loading, isLocked, timeLeft]);

  useEffect(() => {
    const onHide = () => { flush(); };
    const onVisibility = () => {
      if (document.hidden) onHide();
    };
    window.addEventListener('beforeunload', onHide);
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.removeEventListener('beforeunload', onHide);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [flush]);

  // --- SAVE JAWABAN & RAGU ---
  const handleSelectOption = (questionId, option) => {
    if (isLocked) return;
    const cleanOption = String(option).trim().toUpperCase();
    const normalizedId = String(questionId);
    setAnswers(prev => ({ ...prev, [normalizedId]: cleanOption }));
    enqueue(normalizedId, cleanOption, doubtfulQuestions.includes(normalizedId));
  };

  const toggleDoubt = (questionId) => {
    const normalizedId = String(questionId);
    const newDoubts = doubtfulQuestions.includes(normalizedId)
      ? doubtfulQuestions.filter(id => id !== normalizedId)
      : [...doubtfulQuestions, normalizedId];
    setDoubtfulQuestions(newDoubts);
    if (answers[normalizedId]) {
      enqueue(normalizedId, answers[normalizedId], newDoubts.includes(normalizedId));
    }
  };

  // --- SUBMIT EXAM ---
  const submitExam = async (isAuto = false) => {
    if (!sessionId || questions.length === 0) return;

    let correct = 0;
    questions.forEach(q => {
      const kunci = q.correct_answer || q.answer_key || q.answer;
      const normalizedId = String(q.id);
      if (answers[normalizedId]?.toUpperCase() === kunci?.toUpperCase()) correct++;
    });

    const score = questions.length > 0 ? Math.round((correct / questions.length) * 100) : 0;
    
    await flush();
    await supabase.from('exam_sessions').update({
      status: 'finished',
      finished_at: toSQLDateTime(new Date()),
      score,
    }).eq('id', sessionId);
    clearCache();
    
    await Swal.fire({
      title: isAuto ? 'Waktu Habis!' : 'Selesai!',
      html: `Ujian berakhir. Skor Anda: <br/><span style="font-size:48px; font-weight:900; color:#ea580c;">${score}</span>`,
      icon: 'success',
      allowOutsideClick: false
    });
    navigate('/student-dashboard');
  };

  const formatTime = (s) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return `${h > 0 ? h + ':' : ''}${m < 10 ? '0' + m : m}:${sec < 10 ? '0' + sec : sec}`;
  };

  if (isLocked) return (
    <div className="h-screen w-screen bg-red-600 flex flex-col items-center justify-center text-white p-6 fixed inset-0 z-50 text-center font-sans">
      <AlertTriangle size={80} className="mb-6 animate-bounce" />
      <h1 className="text-4xl font-black uppercase italic mb-4">Ujian Terkunci!</h1>
      <p className="max-w-md font-bold opacity-90">Sistem mendeteksi aktivitas mencurigakan. Silakan lapor ke pengawas untuk membuka kembali sesi Anda.</p>
      <div className="mt-8 px-6 py-3 bg-black/20 rounded-xl flex items-center gap-3 border border-white/10">
        <RefreshCw size={16} className="animate-spin" /> <span className="text-xs uppercase font-black">Menunggu Konfirmasi Admin...</span>
      </div>
    </div>
  );

  if (loading) return <div className="h-screen flex items-center justify-center bg-zinc-950 text-orange-600 font-black animate-pulse uppercase italic">Menyiapkan Ujian...</div>;

  if (!loading && !isLocked && questions.length === 0) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex items-center justify-center p-6 text-center">
        <div className="max-w-lg bg-white dark:bg-zinc-900 border border-slate-100 dark:border-zinc-800 rounded-[2rem] p-8 shadow-sm">
          <h2 className="text-xl font-black uppercase italic text-slate-800 dark:text-white">Soal Belum Siap Ditampilkan</h2>
          <p className="mt-3 text-sm font-bold text-slate-500 dark:text-zinc-400">Silakan hubungi pengawas. Sistem tidak menemukan paket soal yang bisa ditampilkan untuk sesi ini.</p>
          <button
            onClick={() => navigate('/student-dashboard')}
            className="mt-6 bg-orange-600 text-white px-6 py-3 rounded-2xl font-black uppercase text-xs tracking-widest"
          >
            Kembali ke Dashboard
          </button>
        </div>
      </div>
    );
  }

  const currentQ = questions[currentIndex] || null;
  const currentQId = currentQ ? String(currentQ.id) : '';

  if (!loading && !isLocked && !currentQ) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex items-center justify-center p-6 text-center">
        <div className="max-w-lg bg-white dark:bg-zinc-900 border border-slate-100 dark:border-zinc-800 rounded-[2rem] p-8 shadow-sm">
          <h2 className="text-xl font-black uppercase italic text-slate-800 dark:text-white">Sesi Ujian Tidak Stabil</h2>
          <p className="mt-3 text-sm font-bold text-slate-500 dark:text-zinc-400">Data soal gagal dimuat. Silakan kembali dan masuk ulang ke ujian.</p>
          <button
            onClick={() => navigate('/student-dashboard')}
            className="mt-6 bg-orange-600 text-white px-6 py-3 rounded-2xl font-black uppercase text-xs tracking-widest"
          >
            Kembali ke Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div translate="no" className="notranslate min-h-screen bg-slate-50 dark:bg-zinc-950 flex flex-col font-sans text-left transition-colors">
      <header className="bg-white dark:bg-zinc-900 border-b dark:border-zinc-800 p-4 sticky top-0 z-20 shadow-sm">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="text-left">
            <h1 className="text-orange-600 font-black italic text-sm uppercase tracking-tighter leading-none">EXAM JINGGA LIVE</h1>
            <p className="text-[9px] font-bold text-slate-400 uppercase mt-1 truncate max-w-[200px] md:max-w-md">{schedule?.exams?.title}</p>
          </div>
          <div className={`px-6 py-2 rounded-2xl font-black font-mono text-xl transition-all shadow-inner ${timeLeft < 300 ? 'bg-red-500 text-white animate-pulse' : 'bg-slate-900 text-white dark:bg-white dark:text-black'}`}>
            {formatTime(timeLeft)}
          </div>
        </div>
      </header>

      <div className="flex-1 flex flex-col lg:flex-row max-w-7xl mx-auto w-full p-4 lg:p-8 gap-8">
        <main className="flex-1 space-y-6">
          <div className="bg-white dark:bg-zinc-900 p-8 lg:p-12 rounded-[3rem] shadow-sm border border-slate-100 dark:border-zinc-800 relative">
             <div className="flex justify-between items-center mb-8">
               <span className="bg-orange-600 text-white px-5 py-1.5 rounded-full text-[10px] font-black uppercase italic tracking-widest shadow-lg shadow-orange-500/20">Soal {currentIndex + 1} dari {questions.length}</span>
               
                <button 
                 onClick={() => toggleDoubt(currentQ.id)}
                 className={`flex items-center gap-2 px-4 py-2 rounded-xl text-[10px] font-black uppercase transition-all border-2 ${doubtfulQuestions.includes(currentQId) ? 'bg-amber-400 border-amber-400 text-slate-900 shadow-lg shadow-amber-400/20' : 'bg-transparent border-slate-100 dark:border-zinc-800 text-slate-400'}`}
                >
                  <HelpCircle size={14}/> {doubtfulQuestions.includes(currentQId) ? 'Ragu-Ragu Aktif' : 'Tandai Ragu-Ragu'}
                </button>
             </div>
             
             <h2 className="text-xl font-bold dark:text-white leading-relaxed mb-8 whitespace-pre-wrap">{currentQ?.question_text}</h2>
             {currentQ?.question_image && <img src={currentQ.question_image} className="max-h-64 rounded-3xl mb-8 border border-slate-100 dark:border-zinc-800 shadow-sm" alt="img" />}
             
             <div className="grid grid-cols-1 gap-3">
                {currentQ?.displayOptions?.map((opt, idx) => {
                  const letter = String.fromCharCode(65 + idx); 
                  const val = opt.toUpperCase(); 
                  const active = answers[currentQId] === val;
                  return (
                    <button key={val} onClick={() => handleSelectOption(currentQ.id, val)} className={`w-full p-6 rounded-[2rem] border-2 transition-all flex items-center gap-5 text-left ${active ? 'border-orange-600 bg-orange-50 dark:bg-orange-900/10' : 'border-slate-50 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-orange-200'}`}>
                     <span className={`w-10 h-10 rounded-full flex items-center justify-center font-black transition-all shrink-0 ${active ? 'bg-orange-600 text-white scale-110 shadow-lg' : 'bg-slate-100 dark:bg-zinc-800 text-slate-500'}`}>{letter}</span>
                     <div className="flex-1 flex flex-col gap-2">
                        <span className="font-bold dark:text-zinc-200">{currentQ[`option_${opt}`]}</span>
                        {currentQ[`image_${opt}`] && <img src={currentQ[`image_${opt}`]} className="h-20 w-20 object-cover rounded-xl border border-slate-100" alt="opt" />}
                     </div>
                     {active && <CheckCircle2 className="text-orange-600 shrink-0" size={24}/>}
                   </button>
                 );
               })}
             </div>
          </div>

          <div className="flex justify-between items-center pb-10">
            <button disabled={currentIndex === 0} onClick={() => setCurrentIndex(prev => prev - 1)} className="px-6 py-3 font-black text-slate-400 uppercase text-[10px] flex items-center gap-2 hover:text-orange-600 disabled:opacity-20 transition-all"><ChevronLeft size={18}/> Kembali</button>
            
            {currentIndex === questions.length - 1 ? (
              <div className="bg-orange-100 dark:bg-orange-900/30 text-orange-600 px-6 py-3 rounded-2xl border border-orange-200 dark:border-orange-800/50 flex items-center gap-3">
                 <Clock size={16} className="animate-pulse"/>
                 <p className="text-[10px] font-black uppercase tracking-widest">Berakhir Otomatis Saat Waktu Habis</p>
                 <button onClick={() => submitExam()} className="hidden bg-emerald-600 text-white px-8 py-3 rounded-xl font-black uppercase text-xs">Kirim</button>
              </div>
            ) : (
              <button onClick={() => setCurrentIndex(prev => prev + 1)} className="bg-slate-900 dark:bg-white dark:text-black text-white px-10 py-4 rounded-2xl font-black uppercase text-[10px] shadow-lg hover:scale-105 transition-all flex items-center gap-2 tracking-widest">Selanjutnya <ChevronRight size={18}/></button>
            )}
          </div>
        </main>

        <aside className="w-full lg:w-80">
          <div className="bg-white dark:bg-zinc-900 p-8 rounded-[2.5rem] border border-slate-100 dark:border-zinc-800 shadow-sm sticky top-28">
            <h3 className="font-black text-[10px] uppercase text-slate-400 mb-6 flex items-center gap-2 tracking-[0.2em]"><LayoutGrid size={14} className="text-orange-600"/> Navigasi Soal</h3>
            <div className="grid grid-cols-5 gap-3">
              {questions.map((q, idx) => {
                const isAnswered = !!answers[String(q.id)];
                const isDoubt = doubtfulQuestions.includes(String(q.id));
                return (
                  <button key={q.id} onClick={() => setCurrentIndex(idx)} className={`h-11 rounded-xl text-[10px] font-black transition-all ${currentIndex === idx ? 'ring-2 ring-orange-600 ring-offset-2 dark:ring-offset-zinc-950 scale-110 shadow-lg' : ''} ${isDoubt ? 'bg-amber-400 text-slate-900' : isAnswered ? 'bg-emerald-500 text-white' : 'bg-slate-50 dark:bg-zinc-800 text-slate-400'}`}>
                    {idx + 1}
                  </button>
                );
              })}
            </div>
            
            <div className="mt-8 pt-6 border-t dark:border-zinc-800 space-y-4">
               <div className="flex items-center justify-between text-[10px] font-black uppercase text-slate-400 tracking-widest">
                 <span>Progres</span>
                 <span className="text-orange-600">{Object.keys(answers).length} / {questions.length}</span>
               </div>
               <div className="w-full bg-slate-100 dark:bg-zinc-800 h-2.5 rounded-full overflow-hidden shadow-inner">
                  <div className="bg-gradient-to-r from-orange-500 to-orange-600 h-full transition-all duration-700" style={{width: `${(Object.keys(answers).length / questions.length) * 100}%`}}></div>
               </div>
               <div className="flex gap-4 pt-2">
                  <div className="flex items-center gap-1.5"><div className="w-3 h-3 bg-emerald-500 rounded-sm"></div><span className="text-[8px] font-black text-slate-400 uppercase">Isi</span></div>
                  <div className="flex items-center gap-1.5"><div className="w-3 h-3 bg-amber-400 rounded-sm"></div><span className="text-[8px] font-black text-slate-400 uppercase">Ragu</span></div>
                  <div className="flex items-center gap-1.5"><div className="w-3 h-3 bg-slate-100 dark:bg-zinc-800 rounded-sm"></div><span className="text-[8px] font-black text-slate-400 uppercase">Kosong</span></div>
               </div>
            </div>
          </div>
        </aside>
        {debugAntiCheat && (
          <div className="fixed bottom-4 right-4 z-50 w-64 bg-black/80 text-white text-[10px] font-mono rounded-xl p-3 space-y-2">
            <div className="font-bold uppercase tracking-wider">AntiCheat Debug</div>
            <div className="flex justify-between"><span>hidden</span><span>{String(debugStatus.hidden)}</span></div>
            <div className="flex justify-between"><span>focus</span><span>{debugStatus.hasFocus === null ? 'n/a' : String(debugStatus.hasFocus)}</span></div>
            <div className="flex justify-between"><span>delta</span><span>{debugStatus.lastDelta === null ? '-' : `${debugStatus.lastDelta}ms`}</span></div>
            <button
              type="button"
              onClick={handleCopyDebug}
              className="w-full rounded-lg border border-white/30 px-3 py-1 text-[9px] uppercase font-bold tracking-widest hover:bg-white/10 transition"
            >
              {debugCopied ? 'Copied' : 'Copy Logs'}
            </button>
            <div className="border-t border-white/20 pt-2 space-y-1 max-h-40 overflow-auto">
              {debugLogs.length === 0 ? (
                <div className="opacity-70">no events</div>
              ) : (
                [...debugLogs].reverse().map((log, idx) => (
                  <div key={`${log.t}-${idx}`} className="flex justify-between gap-2">
                    <span>{log.t}</span>
                    <span className="flex-1 truncate">{log.event}</span>
                    <span className="opacity-80">{log.hidden ? 'H' : 'V'}{log.focus === null ? '' : log.focus ? 'F' : 'N'}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ExamInterface;

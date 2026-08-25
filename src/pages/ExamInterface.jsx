import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import { ChevronLeft, ChevronRight, AlertTriangle, LayoutGrid, CheckCircle2, RefreshCw, Clock, HelpCircle, ZoomIn, Check, Send } from 'lucide-react';
import Swal from 'sweetalert2';
import { useExamAnswerSync } from '../features/examSessions';
import { toSQLDateTime } from '../features/schedules/utils';
import ImageLightbox from '../components/ImageLightbox';
import ExamQuestionDrawer from '../components/ExamQuestionDrawer';
import M3Button from '../components/ui/M3Button';
import M3Card from '../components/ui/M3Card';
import M3RadioCard from '../components/ui/M3RadioCard';
import M3Badge from '../components/ui/M3Badge';

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

  // Mobile Bottom Sheet Drawer & Lightbox States
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);
  const [lightboxImg, setLightboxImg] = useState(null);

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

    startExamSession(user.id, () => cancelled);
    return () => { cancelled = true; };
  }, [examId]);

  const startExamSession = async (studentId, isCancelled) => {
    try {
      setLoading(true);

      // 1. Cek apakah ada data inisialisasi dari RPC token sebelumnya
      const cachedInitStr = sessionStorage.getItem(`exam_init_${examId}`);
      let initData = cachedInitStr ? JSON.parse(cachedInitStr) : null;

      if (!initData) {
        // Fallback: Panggil RPC fn_start_student_exam jika direct navigation
        const { data: rpcData, error: rpcErr } = await supabase.rpc('fn_start_student_exam', {
          p_schedule_id: examId,
          p_token: '', // default / resume
          p_student_id: studentId
        });

        if (!rpcErr && rpcData?.session_id) {
          initData = rpcData;
        }
      }

      if (isCancelled()) return;

      if (initData) {
        setSessionId(initData.session_id);
        setTimeLeft(initData.remaining_seconds || 3600);
        setIsLocked(initData.is_locked || false);
        setViolationCount(initData.violation_count || 0);

        // Format soal
        let loadedQuestions = (initData.questions || []).map(q => ({
          ...q,
          displayOptions: ['a', 'b', 'c', 'd', 'e']
        }));

        if (initData.shuffle_questions) {
          loadedQuestions = shuffleArray(loadedQuestions);
        }

        setQuestions(loadedQuestions);

        // Muat jawaban yang tersimpan
        if (initData.saved_answers) {
          setAnswers(initData.saved_answers);
        }

        // Ambil info jadwal untuk header
        const { data: sch } = await supabase
          .from('schedules')
          .select('*, exams(title, type, duration)')
          .eq('id', examId)
          .maybeSingle();
        if (sch) setSchedule(sch);

      } else {
        // Fallback Tradisional
        await startExamLegacy(studentId, isCancelled);
      }

    } catch (err) {
      console.error('Error starting exam session:', err);
      if (!isCancelled()) {
        Swal.fire({
          title: 'Gagal Membuka Ujian',
          text: err.message || 'Terjadi gangguan saat memuat sesi ujian.',
          icon: 'error',
          confirmButtonColor: '#ea580c'
        }).then(() => navigate('/student-dashboard'));
      }
    } finally {
      if (!isCancelled()) setLoading(false);
    }
  };

  const startExamLegacy = async (studentId, isCancelled) => {
    const { data: sch, error: schErr } = await supabase
      .from('schedules')
      .select('*, exams(*)')
      .eq('id', examId)
      .single();

    if (schErr || !sch) throw new Error('Jadwal ujian tidak ditemukan.');
    if (isCancelled()) return;
    setSchedule(sch);

    // Ambil atau buat sesi
    let { data: session } = await supabase
      .from('exam_sessions')
      .select('*')
      .eq('schedule_id', examId)
      .eq('student_id', studentId)
      .maybeSingle();

    if (!session) {
      const now = new Date();
      const duration = sch.exams?.duration || 90;
      const endTime = new Date(now.getTime() + duration * 60000);

      const { data: newSession, error: createErr } = await supabase
        .from('exam_sessions')
        .insert({
          schedule_id: examId,
          student_id: studentId,
          started_at: toSQLDateTime(now),
          end_time: toSQLDateTime(endTime),
          status: 'active'
        })
        .select()
        .single();

      if (createErr) throw createErr;
      session = newSession;
    }

    if (isCancelled()) return;
    setSessionId(session.id);
    setIsLocked(session.is_locked || false);

    // Hitung sisa waktu
    const end = new Date(session.end_time).getTime();
    const now = Date.now();
    const rem = Math.max(0, Math.floor((end - now) / 1000));
    setTimeLeft(rem);

    // Ambil soal
    const { data: examQData } = await supabase
      .from('exam_questions')
      .select('question_id, questions(*)')
      .eq('exam_id', sch.exam_id)
      .order('order_number', { ascending: true });

    let loadedQuestions = (examQData || []).map(item => item.questions).filter(Boolean);
    if (sch.exams?.shuffle_questions) {
      loadedQuestions = shuffleArray(loadedQuestions);
    }
    loadedQuestions = loadedQuestions.map(q => ({
      ...q,
      displayOptions: ['a', 'b', 'c', 'd', 'e']
    }));
    setQuestions(loadedQuestions);

    // Ambil jawaban sebelumnya
    const { data: savedAnswers } = await supabase
      .from('student_answers')
      .select('question_id, chosen_answer, is_doubt')
      .eq('session_id', session.id);

    if (savedAnswers) {
      const ansMap = {};
      const doubtList = [];
      savedAnswers.forEach(a => {
        ansMap[String(a.question_id)] = a.chosen_answer;
        if (a.is_doubt) doubtList.push(String(a.question_id));
      });
      setAnswers(ansMap);
      setDoubtfulQuestions(doubtList);
    }
  };

  // --- TIMER HITUNG MUNDUR ---
  useEffect(() => {
    if (loading || isLocked || timeLeft <= 0) return;

    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          submitExam(true);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [loading, isLocked, timeLeft]);

  // --- ANTI-CHEAT PROTECTION (BLUR / VISIBILITY) ---
  useEffect(() => {
    if (loading || isLocked) return;

    const handleVisibilityChange = async () => {
      if (document.hidden) {
        const now = Date.now();
        if (now - lastCheatTime.current > 3000) {
          lastCheatTime.current = now;
          const newViolations = violationCount + 1;
          setViolationCount(newViolations);

          if (sessionId) {
            await supabase.from('exam_sessions').update({
              violation_count: newViolations,
              is_locked: newViolations >= 3
            }).eq('id', sessionId);
          }

          if (newViolations >= 3) {
            setIsLocked(true);
          } else {
            Swal.fire({
              title: 'Peringatan Anti-Cheat!',
              text: `Anda terdeteksi berpindah aplikasi/layar (${newViolations}/3). Ujian akan terkunci jika terulang!`,
              icon: 'warning',
              confirmButtonColor: '#ea580c'
            });
          }
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [loading, isLocked, violationCount, sessionId]);

  // --- PILIH JAWABAN ---
  const handleSelectOption = (questionId, optionLetter) => {
    if (isLocked) return;
    const normalizedId = String(questionId);
    const letter = optionLetter.toUpperCase();

    const newAnswers = { ...answers, [normalizedId]: letter };
    setAnswers(newAnswers);

    const isDoubt = doubtfulQuestions.includes(normalizedId);
    enqueue(normalizedId, letter, isDoubt);
  };

  // --- TANDAI RAGU-RAGU ---
  const toggleDoubt = (questionId) => {
    if (isLocked) return;
    const normalizedId = String(questionId);
    let newDoubts;

    if (doubtfulQuestions.includes(normalizedId)) {
      newDoubts = doubtfulQuestions.filter(id => id !== normalizedId);
    } else {
      newDoubts = [...doubtfulQuestions, normalizedId];
    }
    setDoubtfulQuestions(newDoubts);

    if (answers[normalizedId]) {
      enqueue(normalizedId, answers[normalizedId], newDoubts.includes(normalizedId));
    }
  };

  // --- SUBMIT UJIAN ---
  const submitExam = async (isAuto = false) => {
    if (!sessionId || questions.length === 0) return;

    if (!isAuto) {
      const unansweredCount = questions.length - Object.keys(answers).length;
      const doubtCount = doubtfulQuestions.length;

      let confirmText = 'Apakah Anda yakin ingin menyelesaikan ujian ini?';
      if (unansweredCount > 0) {
        confirmText = `Masih ada ${unansweredCount} soal yang belum dijawab! Yakin ingin menyelesaikan?`;
      } else if (doubtCount > 0) {
        confirmText = `Masih ada ${doubtCount} soal dengan status ragu-ragu! Yakin ingin menyelesaikan?`;
      }

      const result = await Swal.fire({
        title: 'Selesaikan Ujian?',
        text: confirmText,
        icon: unansweredCount > 0 ? 'warning' : 'question',
        showCancelButton: true,
        confirmButtonColor: '#ea580c',
        cancelButtonColor: '#64748b',
        confirmButtonText: 'Ya, Selesaikan!',
        cancelButtonText: 'Batal Periksa Dulu'
      });

      if (!result.isConfirmed) return;
    }

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
    sessionStorage.removeItem(`exam_init_${examId}`);
    
    await Swal.fire({
      title: isAuto ? 'Waktu Habis!' : 'Ujian Selesai!',
      html: `Jawaban Anda telah berhasil dikirim ke server.`,
      icon: 'success',
      confirmButtonColor: '#ea580c',
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
      <AlertTriangle size={72} className="mb-4 animate-bounce" />
      <h1 className="text-3xl sm:text-4xl font-black uppercase italic mb-2">Ujian Terkunci!</h1>
      <p className="max-w-md font-bold text-sm opacity-90 leading-relaxed">
        Sistem mendeteksi perpindahan aplikasi melebihi batas toleransi. Silakan laporkan kepada pengawas ruangan Anda.
      </p>
      <div className="mt-6 px-5 py-3 bg-black/25 rounded-2xl flex items-center gap-3 border border-white/10 text-xs font-black uppercase">
        <RefreshCw size={16} className="animate-spin" />
        <span>Menunggu Pembukaan Kunci oleh Pengawas...</span>
      </div>
    </div>
  );

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-50 dark:bg-zinc-950 text-orange-600 font-black animate-pulse uppercase tracking-widest text-xs">
        Menyiapkan Lembar Kerja Ujian...
      </div>
    );
  }

  const currentQ = questions[currentIndex] || null;
  const currentQId = currentQ ? String(currentQ.id) : '';

  return (
    <div translate="no" className="notranslate min-h-screen bg-slate-50 dark:bg-zinc-950 flex flex-col font-sans text-left transition-colors pb-28 lg:pb-10">
      
      {/* Sticky Header */}
      <header className="bg-white/90 dark:bg-zinc-900/90 backdrop-blur-md border-b border-slate-100 dark:border-zinc-800 px-4 sm:px-6 py-3 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div className="text-left">
            <h1 className="text-orange-600 font-black italic text-xs sm:text-sm uppercase tracking-tight leading-none">
              EXAM JINGGA LIVE
            </h1>
            <p className="text-[9px] sm:text-[10px] font-bold text-slate-400 dark:text-zinc-500 uppercase mt-0.5 truncate max-w-[150px] sm:max-w-md">
              {schedule?.exams?.title}
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            {/* Tombol Drawer Mobile */}
            <button
              onClick={() => setIsDrawerOpen(true)}
              className="lg:hidden flex items-center gap-1.5 bg-orange-50 dark:bg-orange-950/40 text-orange-600 border border-orange-200/80 dark:border-orange-900/40 px-3 py-1.5 rounded-xl text-[10px] font-black uppercase cursor-pointer"
            >
              <LayoutGrid size={14} />
              <span>{currentIndex + 1}/{questions.length}</span>
            </button>

            {/* Countdown Timer Badge */}
            <div className={`px-4 py-1.5 rounded-xl font-black font-mono text-sm sm:text-base transition-all shadow-inner flex items-center gap-1.5 ${
              timeLeft < 300 
                ? 'bg-red-500 text-white animate-pulse' 
                : 'bg-slate-900 text-white dark:bg-white dark:text-black'
            }`}>
              <Clock size={14} />
              <span>{formatTime(timeLeft)}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex-1 flex flex-col lg:flex-row max-w-7xl mx-auto w-full p-4 sm:p-6 lg:p-8 gap-6 sm:gap-8">
        
        {/* Left Column: Active Question & Options */}
        <main className="flex-1 space-y-6">
          {/* M3 Elevated Question Card */}
          <M3Card variant="elevated" className="p-6 sm:p-10 border border-stone-200 dark:border-stone-800 relative m3-elevation-2">
             
             {/* Question Badge & Doubt Button */}
             <div className="flex justify-between items-center mb-6">
               <span className="bg-orange-600 text-white px-4 py-1.5 rounded-full text-[10px] font-black uppercase italic tracking-widest shadow-md shadow-orange-600/20">
                 Soal {currentIndex + 1} dari {questions.length}
               </span>
               
               <button 
                onClick={() => toggleDoubt(currentQ.id)}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-[10px] font-black uppercase transition-all border cursor-pointer ${
                  doubtfulQuestions.includes(currentQId) 
                    ? 'bg-amber-400 border-amber-400 text-slate-950 font-black shadow-md shadow-amber-400/20' 
                    : 'bg-transparent border-stone-200 dark:border-stone-800 text-stone-400 hover:border-amber-400'
                }`}
               >
                 <HelpCircle size={14}/> 
                 <span>{doubtfulQuestions.includes(currentQId) ? 'Ragu-Ragu Aktif' : 'Tandai Ragu'}</span>
               </button>
             </div>
             
             {/* Question Text */}
             <h2 className="text-base sm:text-lg font-bold text-stone-900 dark:text-stone-100 leading-relaxed mb-6 whitespace-pre-wrap">
               {currentQ?.question_text}
             </h2>

             {/* Question Image (with Tap-to-Zoom Lightbox) */}
             {currentQ?.question_image && (
               <div className="relative group inline-block mb-6 cursor-pointer" onClick={() => setLightboxImg(currentQ.question_image)}>
                 <img 
                   src={currentQ.question_image} 
                   className="max-h-72 rounded-2xl border border-stone-200 dark:border-stone-800 shadow-xs object-contain" 
                   alt="Ilustrasi Soal" 
                 />
                 <div className="absolute bottom-2 right-2 bg-black/70 backdrop-blur-md text-white text-[9px] font-bold px-2.5 py-1 rounded-lg flex items-center gap-1 opacity-90 group-hover:opacity-100 transition-opacity">
                   <ZoomIn size={12} /> Ketuk untuk perbesar
                 </div>
               </div>
             )}
             
             {/* Multiple Choice Options (M3RadioCard) */}
             <div className="grid grid-cols-1 gap-3.5">
                {currentQ?.displayOptions?.map((opt, idx) => {
                  const letter = String.fromCharCode(65 + idx); // A, B, C, D, E
                  const val = opt.toUpperCase(); 
                  const optionText = currentQ[`option_${opt}`] || currentQ[`option_${letter}`] || '';
                  const optionImg = currentQ[`image_${opt}`] || currentQ[`image_${letter}`] || null;
                  const active = answers[currentQId] === val;
                  const isDoubt = doubtfulQuestions.includes(currentQId);

                  if (!optionText && !optionImg) return null;

                  return (
                    <M3RadioCard
                      key={val}
                      optionKey={letter}
                      optionText={optionText}
                      selected={active}
                      doubtful={isDoubt}
                      onClick={() => handleSelectOption(currentQ.id, val)}
                    />
                  );
                })}
             </div>
          </M3Card>

          {/* Desktop Navigation Row */}
          <div className="hidden lg:flex justify-between items-center pb-6">
            <M3Button 
              variant="outlined"
              size="md"
              disabled={currentIndex === 0} 
              onClick={() => setCurrentIndex(prev => prev - 1)} 
              icon={ChevronLeft}
              iconPosition="left"
            >
              Sebelumnya
            </M3Button>
            
            {currentIndex === questions.length - 1 ? (
              <M3Button 
                variant="filled"
                size="md"
                onClick={() => submitExam(false)} 
                icon={Send}
                iconPosition="right"
                className="bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-600/20"
              >
                Selesai & Kirim Jawaban
              </M3Button>
            ) : (
              <M3Button 
                variant="filled"
                size="md"
                onClick={() => setCurrentIndex(prev => prev + 1)} 
                icon={ChevronRight}
                iconPosition="right"
              >
                Selanjutnya
              </M3Button>
            )}
          </div>
        </main>

        {/* Desktop Sidebar: Navigation Grid */}
        <aside className="hidden lg:block w-80 shrink-0">
          <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2.5rem] border border-slate-100 dark:border-zinc-800 shadow-xs sticky top-24">
            <div className="flex items-center justify-between mb-5">
              <h3 className="font-black text-[10px] uppercase text-slate-400 dark:text-zinc-500 flex items-center gap-2 tracking-[0.2em]">
                <LayoutGrid size={14} className="text-orange-600"/> Nomor Soal
              </h3>
              <span className="text-[10px] font-black text-orange-600">
                {Object.keys(answers).length}/{questions.length}
              </span>
            </div>

            <div className="grid grid-cols-5 gap-2 max-h-[320px] overflow-y-auto pr-1 custom-scrollbar">
              {questions.map((q, idx) => {
                const qIdStr = String(q.id);
                const isAnswered = !!answers[qIdStr];
                const isDoubt = doubtfulQuestions.includes(qIdStr);
                const isCurrent = currentIndex === idx;

                let btnStyle = 'bg-slate-50 dark:bg-zinc-800/80 text-slate-500 dark:text-zinc-400';
                if (isDoubt) {
                  btnStyle = 'bg-amber-400 text-slate-950 font-black shadow-md shadow-amber-400/20';
                } else if (isAnswered) {
                  btnStyle = 'bg-emerald-500 text-white font-black shadow-md shadow-emerald-500/20';
                }

                return (
                  <button 
                    key={q.id} 
                    onClick={() => setCurrentIndex(idx)} 
                    className={`h-11 rounded-xl text-xs font-black transition-all cursor-pointer flex flex-col items-center justify-center ${btnStyle} ${
                      isCurrent ? 'ring-2 ring-orange-600 ring-offset-2 dark:ring-offset-zinc-950 scale-105 shadow-md z-10' : ''
                    }`}
                  >
                    <span>{idx + 1}</span>
                    {isAnswered && <span className="text-[7px] leading-none uppercase">{answers[qIdStr]}</span>}
                  </button>
                );
              })}
            </div>
            
            {/* Progress Bar & Legend */}
            <div className="mt-6 pt-5 border-t border-slate-100 dark:border-zinc-800 space-y-3">
               <div className="w-full bg-slate-100 dark:bg-zinc-800 h-2 rounded-full overflow-hidden">
                  <div 
                    className="bg-gradient-to-r from-orange-500 to-orange-600 h-full transition-all duration-500" 
                    style={{ width: `${questions.length > 0 ? (Object.keys(answers).length / questions.length) * 100 : 0}%` }}
                  ></div>
               </div>
               <div className="flex justify-between pt-1 text-[8px] font-black uppercase text-slate-400">
                  <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-emerald-500 rounded-sm"></div><span>Terjawab</span></div>
                  <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-amber-400 rounded-sm"></div><span>Ragu</span></div>
                  <div className="flex items-center gap-1.5"><div className="w-2.5 h-2.5 bg-slate-100 dark:bg-zinc-800 rounded-sm"></div><span>Kosong</span></div>
               </div>
            </div>

            {/* Selesai Button in Sidebar */}
            <button
              onClick={() => submitExam(false)}
              className="mt-6 w-full py-3.5 bg-slate-900 dark:bg-white text-white dark:text-slate-900 rounded-2xl font-black uppercase text-xs tracking-widest hover:bg-orange-600 hover:text-white transition-all shadow-md cursor-pointer"
            >
              Kirim Jawaban
            </button>
          </div>
        </aside>
      </div>

      {/* 📱 THUMB-ZONE STICKY BOTTOM ACTION BAR (Mobile Ergonomics) */}
      <nav 
        aria-label="Navigasi Ujian Jempol"
        className="lg:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 dark:bg-zinc-900/95 backdrop-blur-xl border-t border-slate-200/80 dark:border-zinc-800 px-4 py-3 shadow-2xl"
      >
        <div className="max-w-md mx-auto flex items-center justify-between gap-2">
          
          {/* Tombol Sebelumnya */}
          <button
            disabled={currentIndex === 0}
            onClick={() => setCurrentIndex(prev => prev - 1)}
            className="flex-1 py-3.5 px-3 bg-slate-100 dark:bg-zinc-800 text-slate-700 dark:text-zinc-200 rounded-2xl font-black text-xs uppercase flex items-center justify-center gap-1 disabled:opacity-30 active:scale-95 transition-all cursor-pointer"
          >
            <ChevronLeft size={16} />
            <span>Prev</span>
          </button>

          {/* Tombol Ragu-Ragu Toggle (Tengah) */}
          <button
            onClick={() => toggleDoubt(currentQ?.id)}
            className={`py-3.5 px-4 rounded-2xl font-black text-xs uppercase flex items-center justify-center gap-1.5 transition-all active:scale-95 cursor-pointer ${
              doubtfulQuestions.includes(currentQId)
                ? 'bg-amber-400 text-slate-950 font-black shadow-md shadow-amber-400/20'
                : 'bg-slate-100 dark:bg-zinc-800 text-slate-500 dark:text-zinc-400'
            }`}
          >
            <HelpCircle size={16} />
            <span>{doubtfulQuestions.includes(currentQId) ? 'Ragu' : 'Ragu?'}</span>
          </button>

          {/* Tombol Drawer Trigger */}
          <button
            onClick={() => setIsDrawerOpen(true)}
            className="py-3.5 px-4 bg-orange-100 dark:bg-orange-950/40 text-orange-600 rounded-2xl font-black text-xs uppercase flex items-center justify-center gap-1 transition-all active:scale-95 cursor-pointer"
          >
            <LayoutGrid size={16} />
            <span>{currentIndex + 1}</span>
          </button>

          {/* Tombol Selanjutnya / Selesai */}
          {currentIndex === questions.length - 1 ? (
            <button
              onClick={() => submitExam(false)}
              className="flex-1 py-3.5 px-3 bg-emerald-600 text-white rounded-2xl font-black text-xs uppercase flex items-center justify-center gap-1 shadow-md shadow-emerald-600/25 active:scale-95 transition-all cursor-pointer"
            >
              <Send size={14} />
              <span>Kirim</span>
            </button>
          ) : (
            <button
              onClick={() => setCurrentIndex(prev => prev + 1)}
              className="flex-1 py-3.5 px-3 bg-orange-600 text-white rounded-2xl font-black text-xs uppercase flex items-center justify-center gap-1 shadow-md shadow-orange-600/25 active:scale-95 transition-all cursor-pointer"
            >
              <span>Next</span>
              <ChevronRight size={16} />
            </button>
          )}

        </div>
      </nav>

      {/* Mobile Question Bottom Sheet Drawer */}
      <ExamQuestionDrawer
        isOpen={isDrawerOpen}
        onClose={() => setIsDrawerOpen(false)}
        questions={questions}
        currentIndex={currentIndex}
        onSelectQuestion={(idx) => setCurrentIndex(idx)}
        answers={answers}
        doubts={doubtfulQuestions}
      />

      {/* Tap-to-Zoom Lightbox Modal */}
      {lightboxImg && (
        <ImageLightbox
          src={lightboxImg}
          onClose={() => setLightboxImg(null)}
        />
      )}
    </div>
  );
};

export default ExamInterface;

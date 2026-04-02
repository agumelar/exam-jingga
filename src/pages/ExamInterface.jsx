import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { ChevronLeft, ChevronRight, AlertTriangle, LayoutGrid, CheckCircle2, RefreshCw, Clock, HelpCircle } from 'lucide-react';
import Swal from 'sweetalert2';

const ExamInterface = () => {
  const { examId } = useParams(); 
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [doubtfulQuestions, setDoubtfulQuestions] = useState([]); 
  const [timeLeft, setTimeLeft] = useState(0);
  const [loading, setLoading] = useState(true);
  
  const [sessionId, setSessionId] = useState(null);
  const [isLocked, setIsLocked] = useState(false);
  const [violationCount, setViolationCount] = useState(0);
  
  const timerRef = useRef(null);
  const lastCheatTime = useRef(0);

  const shuffleArray = (array) => {
    let newArr = [...array];
    for (let i = newArr.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [newArr[i], newArr[j]] = [newArr[j], newArr[i]];
    }
    return newArr;
  };

  useEffect(() => {
    const user = JSON.parse(localStorage.getItem('user_session'));
    if (!user || user.role !== 'siswa') {
      navigate('/login');
    } else {
      startExam(user.id);
    }
  }, [examId]);

  const startExam = async (studentId) => {
    try {
      const { data: schData } = await supabase
        .from('schedules')
        .select(`*, exams(*, subjects(name))`)
        .eq('id', examId)
        .single();
      
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
        if (existingSession.status === 'finished') throw new Error("Ujian ini sudah diselesaikan!");
        if (existingSession.status === 'locked') {
          setSessionId(existingSession.id);
          setIsLocked(true);
          setLoading(false);
          return; 
        }
        setViolationCount(existingSession.violation_count || 0);
        currentSession = existingSession;
      } else {
        const { data: newSession, error: nsErr } = await supabase
          .from('exam_sessions')
          .insert([{ student_id: studentId, schedule_id: examId, status: 'active' }])
          .select().single();
        if (nsErr) throw nsErr;
        currentSession = newSession;
      }
      setSessionId(currentSession.id);

      // --- TIMER LOGIC (DENGAN PERBAIKAN AUTO-SUBMIT ADIL) ---
      const durationInSeconds = (schData.exams?.duration || 60) * 60;
      const startTime = new Date(currentSession.started_at).getTime();
      const now = new Date().getTime();
      const timePassed = Math.floor((now - startTime) / 1000);
      let remaining = durationInSeconds - timePassed;
      
      if (remaining <= 0) { 
         const { data: studentData } = await supabase.from('students').select('class_id').eq('id', studentId).single();
         const { data: myTeachers } = await supabase.from('teacher_assignments').select('teacher_id')
            .eq('class_id', studentData?.class_id).eq('subject_id', schData.exams.subject_id);
         const allowedTeacherIds = myTeachers?.map(t => t.teacher_id) || [];

         const { data: qData } = await supabase
            .from('exam_questions')
            .select('question_id, questions!inner(*)')
            .eq('exam_id', schData.exam_id)
            .in('questions.created_by', allowedTeacherIds);

         const { data: aData } = await supabase.from('student_answers').select('question_id, chosen_answer').eq('session_id', currentSession.id);
         
         let dbCorrect = 0;
         const dbQuestions = qData ? qData.map(q => q.questions).filter(Boolean) : [];
         
         dbQuestions.forEach(q => {
             const ans = aData?.find(a => String(a.question_id) === String(q.id));
             const kunci = q.correct_answer || q.answer_key || q.kunci_jawaban || q.answer;
             if (ans && ans.chosen_answer && kunci) {
                 if (String(ans.chosen_answer).toUpperCase() === String(kunci).toUpperCase()) {
                     dbCorrect++;
                 }
             }
         });

         const dbScore = dbQuestions.length > 0 ? Math.round((dbCorrect / dbQuestions.length) * 100) : 0;
         
         await supabase.from('exam_sessions').update({ 
             status: 'finished', 
             finished_at: new Date().toISOString(), 
             score: dbScore 
         }).eq('id', currentSession.id);
         
         await Swal.fire({
             title: 'Waktu Habis!',
             html: `Waktu ujian telah berakhir saat sesi Anda tertahan.<br/>Sistem telah menyimpan otomatis sisa jawaban Anda.<br/><br/>Skor Anda: <span style="font-size:36px; font-weight:900; color:#ea580c;">${dbScore}</span>`,
             icon: 'info',
             allowOutsideClick: false
         });
         
         navigate('/student-dashboard');
         return; 
      }
      
      setTimeLeft(remaining);

      // Fetch Questions (Untuk Ujian Normal)
      const { data: studentDataNormal } = await supabase.from('students').select('class_id').eq('id', studentId).single();
      const { data: myTeachersNormal } = await supabase.from('teacher_assignments').select('teacher_id')
        .eq('class_id', studentDataNormal?.class_id).eq('subject_id', schData.exams.subject_id);
      
      const allowedTeacherIdsNormal = myTeachersNormal?.map(t => t.teacher_id) || [];

      const { data: qData, error: qErr } = await supabase
        .from('exam_questions')
        .select(`question_id, questions!inner(*)`)
        .eq('exam_id', schData.exam_id)
        .in('questions.created_by', allowedTeacherIdsNormal)
        .order('order_number', { ascending: true });

      if (qErr) throw qErr;
      
      let fetchedQuestions = shuffleArray(qData.map(item => ({
        ...item.questions,
        displayOptions: shuffleArray(['a', 'b', 'c', 'd', 'e'])
      })));

      setQuestions(fetchedQuestions);
      
      const { data: savedAns } = await supabase.from('student_answers').select('*').eq('session_id', currentSession.id);
      if (savedAns) {
        const ansMap = {};
        const doubts = [];
        savedAns.forEach(a => {
          ansMap[a.question_id] = a.chosen_answer;
          if (a.is_doubt) doubts.push(a.question_id);
        });
        setAnswers(ansMap);
        setDoubtfulQuestions(doubts);
      }

      setLoading(false);
    } catch (error) {
      Swal.fire('Akses Ditolak', error.message, 'error');
      navigate('/student-dashboard');
    }
  };

  // --- LOGIKA ANTI CHEAT (FIXED UNTUK PTS & UH) ---
  useEffect(() => {
    if (loading || isLocked || !sessionId || !schedule) return;

    const handleCheatDetection = async () => {
      const now = Date.now();
      if (now - lastCheatTime.current < 2000) return; 
      lastCheatTime.current = now;

      const newCount = violationCount + 1;
      setViolationCount(newCount);
      
      // PERBAIKAN: Cek apakah ujian ini termasuk ketat (Selain UH dan PTS)
      const examType = schedule.exams?.type;
      const isStrictExam = !['UH', 'PTS'].includes(examType); 
      
      // Hanya mengunci jika ujian ketat DAN sudah 2x melanggar
      const isNowLocked = (isStrictExam && newCount >= 2);

      await supabase.from('exam_sessions').update({ violation_count: newCount, status: isNowLocked ? 'locked' : 'active' }).eq('id', sessionId);

      if (!isStrictExam) {
        // Buat UH dan PTS: Hanya peringatan terus menerus, tidak pernah lock
        Swal.fire('Peringatan!', 'Tetap fokus pada lembar ujian!', 'warning');
      } else {
        // Buat PAS, PAT, SAJ:
        if (newCount === 1) {
          Swal.fire({ title: 'PERINGATAN!', text: 'Dilarang keluar halaman ujian atau akun Anda akan TERKUNCI!', icon: 'warning' });
        } else if (isNowLocked) { 
          setIsLocked(true); 
        }
      }
    };

    const handleVisibility = () => { if (document.hidden) handleCheatDetection(); };
    window.addEventListener('visibilitychange', handleVisibility);
    window.addEventListener('blur', handleCheatDetection);
    return () => { window.removeEventListener('visibilitychange', handleVisibility); window.removeEventListener('blur', handleCheatDetection); };
  }, [loading, isLocked, sessionId, schedule, violationCount]);

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

  // --- SAVE JAWABAN & RAGU ---
  const handleSelectOption = async (questionId, option) => {
    if (isLocked) return;
    setAnswers(prev => ({ ...prev, [questionId]: option }));
    await saveToDB(questionId, option, doubtfulQuestions.includes(questionId));
  };

  const toggleDoubt = async (questionId) => {
    let newDoubts;
    if (doubtfulQuestions.includes(questionId)) {
      newDoubts = doubtfulQuestions.filter(id => id !== questionId);
    } else {
      newDoubts = [...doubtfulQuestions, questionId];
    }
    setDoubtfulQuestions(newDoubts);
    if (answers[questionId]) {
      await saveToDB(questionId, answers[questionId], newDoubts.includes(questionId));
    }
  };

  const saveToDB = async (questionId, option, doubtStatus) => {
    try {
      await supabase.from('student_answers').upsert({
        session_id: sessionId,
        question_id: questionId,
        chosen_answer: option,
        is_doubt: doubtStatus 
      }, { onConflict: 'session_id, question_id' });
    } catch (err) { console.error("Save error:", err); }
  };

  // --- SUBMIT EXAM ---
  const submitExam = async (isAuto = false) => {
    if (!isAuto && timeLeft > 60) return; 

    let correct = 0;
    questions.forEach(q => {
      const kunci = q.correct_answer || q.answer_key || q.answer;
      if (answers[q.id]?.toUpperCase() === kunci?.toUpperCase()) correct++;
    });

    const score = questions.length > 0 ? Math.round((correct / questions.length) * 100) : 0;
    
    await supabase.from('exam_sessions').update({ status: 'finished', finished_at: new Date().toISOString(), score }).eq('id', sessionId);
    
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

  const currentQ = questions[currentIndex];

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
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-[10px] font-black uppercase transition-all border-2 ${doubtfulQuestions.includes(currentQ.id) ? 'bg-amber-400 border-amber-400 text-slate-900 shadow-lg shadow-amber-400/20' : 'bg-transparent border-slate-100 dark:border-zinc-800 text-slate-400'}`}
               >
                 <HelpCircle size={14}/> {doubtfulQuestions.includes(currentQ.id) ? 'Ragu-Ragu Aktif' : 'Tandai Ragu-Ragu'}
               </button>
             </div>
             
             <h2 className="text-xl font-bold dark:text-white leading-relaxed mb-8 whitespace-pre-wrap">{currentQ?.question_text}</h2>
             {currentQ?.question_image && <img src={currentQ.question_image} className="max-h-64 rounded-3xl mb-8 border border-slate-100 dark:border-zinc-800 shadow-sm" alt="img" />}
             
             <div className="grid grid-cols-1 gap-3">
               {currentQ?.displayOptions?.map((opt, idx) => {
                 const letter = String.fromCharCode(65 + idx); 
                 const val = opt.toUpperCase(); 
                 const active = answers[currentQ.id] === val;
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
                const isAnswered = !!answers[q.id];
                const isDoubt = doubtfulQuestions.includes(q.id);
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
      </div>
    </div>
  );
};

export default ExamInterface;
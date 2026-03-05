import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import { ChevronLeft, ChevronRight, AlertTriangle, LayoutGrid, CheckCircle2, RefreshCw } from 'lucide-react';
import Swal from 'sweetalert2';

const ExamInterface = () => {
  const { examId } = useParams(); 
  const navigate = useNavigate();
  const [schedule, setSchedule] = useState(null);
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
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
      const { data: existingSessions, error: esErr } = await supabase
        .from('exam_sessions')
        .select('id, status, violation_count, started_at')
        .eq('student_id', studentId)
        .eq('schedule_id', examId)
        .order('started_at', { ascending: false })
        .limit(1);

      if (esErr) throw esErr;

      const existingSession = existingSessions?.[0];

      if (existingSession) {
        if (existingSession.status === 'finished') throw new Error("Kamu sudah menyelesaikan ujian ini!");
        
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

      const durationInMinutes = schData.exams?.duration || 60; 
      const durationInSeconds = durationInMinutes * 60;
      
      const startTime = new Date(currentSession.started_at).getTime();
      const now = new Date().getTime();
      const timePassed = Math.floor((now - startTime) / 1000);
      
      let remaining = durationInSeconds - timePassed;
      
      if (remaining <= 0) {
         await submitExam(true); 
         return;
      }
      
      setTimeLeft(remaining);

      const { data: qData, error: qErr } = await supabase
        .from('exam_questions')
        .select(`question_id, questions(*)`)
        .eq('exam_id', schData.exam_id)
        .order('order_number', { ascending: true });

      if (qErr) throw qErr;
      if (!qData || qData.length === 0) throw new Error("Soal belum divalidasi oleh Admin/Guru!");
      
      let fetchedQuestions = qData.map(item => item.questions);
      
      fetchedQuestions = shuffleArray(fetchedQuestions);
      
      fetchedQuestions = fetchedQuestions.map(q => {
        const options = ['a', 'b', 'c', 'd', 'e'];
        return {
          ...q,
          displayOptions: shuffleArray([...options]) 
        };
      });

      setQuestions(fetchedQuestions);
      
      const { data: savedAns } = await supabase
        .from('student_answers')
        .select('question_id, chosen_answer')
        .eq('session_id', currentSession.id);
      
      if (savedAns && savedAns.length > 0) {
        const ansMap = {};
        savedAns.forEach(a => {
          ansMap[a.question_id] = a.chosen_answer;
        });
        setAnswers(ansMap);
        
        const lastAnsweredIndex = fetchedQuestions.findIndex(q => !ansMap[q.id]);
        if (lastAnsweredIndex !== -1) {
          setCurrentIndex(lastAnsweredIndex);
        }
      }

      setLoading(false);
    } catch (error) {
      Swal.fire('Akses Ditolak', error.message, 'error');
      navigate('/student-dashboard');
    }
  };

  useEffect(() => {
    if (loading || isLocked || !sessionId || !schedule) return;

    const handleCheatDetection = async () => {
      const now = Date.now();
      if (now - lastCheatTime.current < 2000) return; 
      lastCheatTime.current = now;

      const examType = schedule.exams?.type;
      const newCount = violationCount + 1;
      setViolationCount(newCount);

      const isNowLocked = (examType !== 'UH' && newCount >= 2);

      await supabase.from('exam_sessions')
        .update({ 
          violation_count: newCount, 
          status: isNowLocked ? 'locked' : 'active' 
        })
        .eq('id', sessionId);

      if (examType === 'UH') {
        Swal.fire('Peringatan!', 'Terdeteksi meninggalkan halaman. Tetap fokus pada ujian!', 'warning');
      } else {
        if (newCount === 1) {
          Swal.fire({
            title: 'PERINGATAN KERAS!',
            text: 'Sistem mendeteksi Anda membuka tab/aplikasi lain. Jika diulangi, ujian akan TERKUNCI OTOMATIS!',
            icon: 'warning',
            confirmButtonColor: '#ea580c',
            confirmButtonText: 'Saya Mengerti & Tidak Mengulangi'
          });
        } else if (isNowLocked) {
          setIsLocked(true);
        }
      }
    };

    const handleVisibilityChange = () => { if (document.hidden) handleCheatDetection(); };
    const handleBlur = () => { handleCheatDetection(); };

    window.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('blur', handleBlur);

    return () => {
      window.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('blur', handleBlur);
    };
  }, [loading, isLocked, sessionId, schedule, violationCount]);

  useEffect(() => {
    if (loading || isLocked) return;

    if (timeLeft <= 0) {
      submitExam(true);
      return;
    }

    timerRef.current = setInterval(() => {
      setTimeLeft(prev => prev - 1);
    }, 1000);

    return () => clearInterval(timerRef.current);
  }, [loading, isLocked, timeLeft]);

  useEffect(() => {
    if (!isLocked || !sessionId) return;

    const checkLockStatus = async () => {
      const { data } = await supabase
        .from('exam_sessions')
        .select('status')
        .eq('id', sessionId)
        .single();

      if (data && data.status === 'active') {
        Swal.fire({
          title: 'Kunci Terbuka!',
          text: 'Admin telah mereset sesi Anda. Silakan lanjutkan ujian dengan fokus.',
          icon: 'success',
          confirmButtonColor: '#10b981',
          confirmButtonText: 'Lanjutkan'
        }).then(() => {
          navigate('/student-dashboard');
        });
      }
    };

    const lockInterval = setInterval(checkLockStatus, 3000);
    return () => clearInterval(lockInterval);
  }, [isLocked, sessionId, navigate]);

  const handleSelectOption = async (questionId, option) => {
    if (isLocked) return;
    
    setAnswers(prev => ({ ...prev, [questionId]: option }));
    
    try {
      const { data: existingAnswer } = await supabase
        .from('student_answers')
        .select('id')
        .eq('session_id', sessionId)
        .eq('question_id', questionId)
        .maybeSingle();

      if (existingAnswer) {
        await supabase
          .from('student_answers')
          .update({ chosen_answer: option })
          .eq('id', existingAnswer.id);
      } else {
        await supabase
          .from('student_answers')
          .insert([{
            session_id: sessionId,
            question_id: questionId,
            chosen_answer: option
          }]);
      }
    } catch (err) {
      console.error("Gagal simpan jawaban ke database:", err);
    }
  };

  const submitExam = async (isAuto = false) => {
    if (!isAuto) {
      const answeredCount = Object.keys(answers).length;
      const totalQuestions = questions.length;

      if (answeredCount < totalQuestions) {
        Swal.fire({
          title: 'Belum Selesai!',
          text: `Kamu baru menjawab ${answeredCount} dari ${totalQuestions} soal. Silakan isi yang kosong dulu bro!`,
          icon: 'warning',
          confirmButtonColor: '#ea580c'
        });
        return; 
      }

      const { isConfirmed } = await Swal.fire({
        title: 'Selesai Ujian?',
        text: "Pastikan semua jawaban sudah benar bro.",
        icon: 'question',
        showCancelButton: true,
        confirmButtonColor: '#ea580c',
        confirmButtonText: 'Ya, Kirim!'
      });
      if (!isConfirmed) return;
    }

    let correctCount = 0;
    questions.forEach(q => {
      const studentAnswer = answers[q.id];
      const kunciJawaban = q.correct_answer || q.answer_key || q.kunci_jawaban || q.answer;
      
      if (studentAnswer && kunciJawaban && studentAnswer.toUpperCase() === kunciJawaban.toUpperCase()) {
        correctCount++;
      }
    });

    const finalScore = questions.length > 0 ? Math.round((correctCount / questions.length) * 100) : 0;

    try {
      // PERBAIKAN: Tangkap error dari Supabase secara eksplisit menggunakan .select()
      const { error: updateErr } = await supabase.from('exam_sessions')
        .update({ 
          status: 'finished', 
          finished_at: new Date().toISOString(),
          score: finalScore 
        })
        .eq('id', sessionId)
        .select();
      
      // Jika supabase gagal update, lemparkan error ke blok catch
      if (updateErr) throw updateErr;

      await Swal.fire({
        title: isAuto ? 'Waktu Habis!' : 'Ujian Selesai!',
        html: `Jawaban lu berhasil dikirim ke server.<br><br>Skor Akhir Kamu:<br><span style="font-size: 64px; font-weight: 900; color: #ea580c;">${finalScore}</span>`,
        icon: 'success',
        confirmButtonColor: '#10b981',
        confirmButtonText: 'Kembali ke Dashboard',
        allowOutsideClick: false
      });

      navigate('/student-dashboard');
    } catch (err) {
      console.error("Error saving score:", err);
      // Jika pop-up ini yang muncul, berarti ada masalah dengan Database/RLS lu bro
      Swal.fire('Gagal Menyimpan!', `Sistem menolak update nilai: ${err.message}. Hubungi admin atau pengawas!`, 'error');
    }
  };

  const formatTime = (seconds) => {
    if (seconds < 0) return "00:00:00";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    
    if (h > 0) {
       return `${h}:${m < 10 ? '0' + m : m}:${s < 10 ? '0' + s : s}`;
    }
    return `${m < 10 ? '0' + m : m}:${s < 10 ? '0' + s : s}`;
  };

  if (isLocked) {
    return (
      <div className="h-screen w-screen bg-red-600 flex flex-col items-center justify-center text-white p-6 z-50 fixed inset-0 font-sans text-center">
        <AlertTriangle size={100} className="mb-6 animate-pulse text-white" />
        <h1 className="text-5xl md:text-6xl font-black uppercase italic tracking-tighter mb-4">AKUN TERKUNCI!</h1>
        <p className="text-xl md:text-2xl font-bold max-w-3xl leading-relaxed">
          Sistem mendeteksi adanya indikasi kecurangan (Berpindah Tab / Keluar Aplikasi). 
          Sesi ujian Anda telah dibekukan demi menjaga integritas.
        </p>
        <p className="mt-8 px-6 py-4 bg-black/30 rounded-2xl font-bold text-lg md:text-xl border border-white/20 flex flex-col items-center gap-3">
          Silakan melapor ke Pengawas Ujian untuk membuka sesi Anda.
          <span className="flex items-center gap-2 text-sm text-red-200 mt-2">
            <RefreshCw size={16} className="animate-spin" /> Menunggu respon dari Admin...
          </span>
        </p>
      </div>
    );
  }

  if (loading) return <div className="h-screen flex items-center justify-center bg-zinc-950 text-orange-600 font-black animate-pulse text-left italic uppercase">Menyiapkan Lembar Jawaban...</div>;

  const currentQ = questions[currentIndex];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex flex-col font-sans text-left transition-colors">
      <header className="bg-white dark:bg-zinc-900 border-b dark:border-zinc-800 p-4 sticky top-0 z-20">
        <div className="max-w-7xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-orange-600 font-black italic text-sm uppercase tracking-tighter">EXAM JINGGA LIVE</h1>
            <p className="text-[10px] font-bold text-slate-400 uppercase">{schedule?.exams?.title} • {schedule?.exams?.subjects?.name}</p>
          </div>
          <div className={`px-6 py-2 rounded-2xl font-black font-mono text-xl transition-all ${timeLeft < 300 ? 'bg-red-500 text-white animate-pulse' : 'bg-slate-900 text-white dark:bg-white dark:text-black'}`}>
            {formatTime(timeLeft)}
          </div>
        </div>
      </header>

      <div className="flex-1 flex flex-col lg:flex-row max-w-7xl mx-auto w-full p-4 lg:p-8 gap-8">
        <main className="flex-1 space-y-6">
          <div className="bg-white dark:bg-zinc-900 p-8 lg:p-12 rounded-[3rem] shadow-sm border border-slate-100 dark:border-zinc-800 relative">
             <div className="flex justify-between items-center mb-8">
               <span className="bg-orange-600 text-white px-5 py-1.5 rounded-full text-[10px] font-black uppercase italic">Pertanyaan {currentIndex + 1} / {questions.length}</span>
             </div>
             
             <h2 className="text-xl font-bold dark:text-white leading-relaxed mb-8 whitespace-pre-wrap">{currentQ?.question_text}</h2>
             {currentQ?.question_image && <img src={currentQ.question_image} className="max-h-64 rounded-3xl mb-8 border border-slate-100 dark:border-zinc-800" alt="soal" />}
             
             <div className="grid grid-cols-1 gap-3">
               {currentQ?.displayOptions?.map((actualOpt, idx) => {
                 const displayLetter = String.fromCharCode(65 + idx); 
                 const dbValue = actualOpt.toUpperCase(); 
                 const isSelected = answers[currentQ.id] === dbValue;

                 return (
                   <button 
                    key={dbValue}
                    onClick={() => handleSelectOption(currentQ.id, dbValue)}
                    className={`w-full p-6 rounded-[2rem] border-2 transition-all flex items-center gap-5 text-left group ${
                      isSelected 
                      ? 'border-orange-600 bg-orange-50 dark:bg-orange-900/10' 
                      : 'border-slate-50 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-orange-200'
                    }`}
                   >
                     <span className={`w-10 h-10 rounded-full flex items-center justify-center font-black transition-all shrink-0 ${isSelected ? 'bg-orange-600 text-white scale-110 shadow-lg' : 'bg-slate-100 dark:bg-zinc-800 text-slate-500'}`}>
                      {displayLetter}
                     </span>
                     <div className="flex-1 flex flex-col gap-2">
                        <span className="font-bold dark:text-zinc-200 whitespace-pre-wrap">{currentQ[`option_${actualOpt}`]}</span>
                        {currentQ[`image_${actualOpt}`] && <img src={currentQ[`image_${actualOpt}`]} className="h-20 w-20 object-cover rounded-xl border border-slate-100 dark:border-zinc-700" alt={`Opsi ${displayLetter}`} />}
                     </div>
                     {isSelected && <CheckCircle2 className="text-orange-600 shrink-0" size={24}/>}
                   </button>
                 );
               })}
             </div>
          </div>

          <div className="flex justify-between items-center pb-10 lg:pb-0">
            <button disabled={currentIndex === 0} onClick={() => setCurrentIndex(prev => prev - 1)} className="px-6 py-3 font-black text-slate-400 uppercase text-xs flex items-center gap-2 hover:text-orange-600 disabled:opacity-20 transition-all"><ChevronLeft size={20}/> Kembali</button>
            {currentIndex === questions.length - 1 ? (
              <button onClick={() => submitExam()} className="bg-emerald-600 text-white px-10 py-4 rounded-2xl font-black uppercase text-xs shadow-lg hover:bg-emerald-700 transition-all hover:scale-105 italic">Kirim Jawaban</button>
            ) : (
              <button onClick={() => setCurrentIndex(prev => prev + 1)} className="bg-slate-900 dark:bg-white dark:text-black text-white px-10 py-4 rounded-2xl font-black uppercase text-xs shadow-lg hover:scale-105 transition-all">Selanjutnya <ChevronRight size={20}/></button>
            )}
          </div>
        </main>

        <aside className="w-full lg:w-80">
          <div className="bg-white dark:bg-zinc-900 p-8 rounded-[2.5rem] border border-slate-100 dark:border-zinc-800 shadow-sm sticky top-28">
            <h3 className="font-black text-[10px] uppercase text-slate-400 mb-6 flex items-center gap-2 tracking-widest"><LayoutGrid size={14}/> Navigasi Soal</h3>
            <div className="grid grid-cols-5 gap-3">
              {questions.map((q, idx) => (
                <button 
                  key={q.id}
                  onClick={() => setCurrentIndex(idx)}
                  className={`h-11 rounded-xl text-[10px] font-black transition-all ${
                    currentIndex === idx ? 'ring-2 ring-orange-600 ring-offset-2 dark:ring-offset-zinc-950 scale-110 shadow-lg' : ''
                  } ${answers[q.id] ? 'bg-orange-600 text-white' : 'bg-slate-50 dark:bg-zinc-800 text-slate-400'}`}
                >
                  {idx + 1}
                </button>
              ))}
            </div>
            
            <div className="mt-8 pt-8 border-t dark:border-zinc-800">
               <div className="flex items-center justify-between text-[10px] font-black uppercase text-slate-400 mb-4 px-2">
                  <span>Progres</span>
                  <span>{Object.keys(answers).length} / {questions.length}</span>
               </div>
               <div className="w-full bg-slate-100 dark:bg-zinc-800 h-2 rounded-full overflow-hidden">
                  <div className="bg-orange-600 h-full transition-all duration-500" style={{width: `${(Object.keys(answers).length / questions.length) * 100}%`}}></div>
               </div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
};

export default ExamInterface;
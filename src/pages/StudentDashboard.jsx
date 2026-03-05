import React, { useEffect, useState, useRef } from 'react';
import { LogOut, GraduationCap, User, BookOpen, Clock, LayoutDashboard, Moon, Sun, Key, CheckCircle, AlertTriangle, FileSpreadsheet } from 'lucide-react';
import { supabase } from '../supabaseClient';
import { useNavigate } from 'react-router-dom';
import Swal from 'sweetalert2';

const StudentDashboard = () => {
  const navigate = useNavigate();
  const [student, setStudent] = useState(null);
  const [logistics, setLogistics] = useState(null);
  const [availableExams, setAvailableExams] = useState([]);
  const [examHistory, setExamHistory] = useState([]); 
  const [isDark, setIsDark] = useState(false); 
  const [loading, setLoading] = useState(true);
  
  // State Modal Token
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [selectedExam, setSelectedExam] = useState(null);
  const [tokenInput, setTokenInput] = useState(['', '', '', '', '', '']);
  const inputRefs = useRef([]);

  useEffect(() => {
    const session = localStorage.getItem('user_session');
    if (session) {
      const userData = JSON.parse(session);
      if (userData.role !== 'siswa') {
        window.location.href = '/';
      } else {
        setStudent(userData);
        fetchStudentData(userData.id);
      }
    } else {
      window.location.href = '/login';
    }

    if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      setIsDark(true);
      document.documentElement.classList.add('dark');
    } else {
      setIsDark(false);
      document.documentElement.classList.remove('dark');
    }
  }, []);

  const fetchStudentData = async (studentId) => {
    setLoading(true);
    try {
      // 1. Tarik Logistik (Ruangan)
      const { data: logData } = await supabase
        .from('student_logistics')
        .select('*')
        .eq('student_id', studentId)
        .single();
      setLogistics(logData);

      // 2. Tarik Data Siswa & Kelas
      const { data: stuData } = await supabase
        .from('students')
        .select('*, classes(name)')
        .eq('id', studentId)
        .single();
        
      setStudent(stuData); 
      const level = parseInt(stuData.classes.name.split(' ')[0]);

      // 3. JEMBATAN GURU
      const { data: assignments } = await supabase
        .from('teacher_assignments')
        .select('subject_id, teacher_id')
        .eq('class_id', stuData.class_id);

      const tMap = {};
      assignments?.forEach(a => { tMap[a.subject_id] = a.teacher_id; });

      // 4. Tarik Jadwal Ujian Aktif
      const { data: schData } = await supabase
        .from('schedules')
        .select('*, exams(*, subjects(name)), teachers(full_name)')
        .eq('status', 'active');

      const today = new Date();
      const todayString = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

      const validExams = schData.filter(sch => {
        const examDate = new Date(sch.start_time);
        const examDateString = `${examDate.getFullYear()}-${String(examDate.getMonth() + 1).padStart(2, '0')}-${String(examDate.getDate()).padStart(2, '0')}`;
        const isToday = examDateString === todayString;

        const isExamReady = ['validated', 'ready', 'live'].includes(sch.exams?.status);
        
        let isClassAndTeacherValid = false;
        if (sch.exams?.type === 'UH' || sch.exams?.type === 'PTS') {
           isClassAndTeacherValid = sch.class_id === stuData.class_id;
        } else {
           const isLevelValid = parseInt(sch.exams?.level) === level;
           const isTeacherValid = sch.teacher_id === tMap[sch.exams?.subject_id];
           
           const sessionNumber = logData ? parseInt(logData.session_name.replace(/\D/g, '')) : 1;
           const isSessionValid = sch.session_no === 0 || sch.session_no === sessionNumber;

           isClassAndTeacherValid = isLevelValid && isTeacherValid && isSessionValid;
        }

        return isExamReady && isToday && isClassAndTeacherValid;
      });

      // 5. Cek Status Pengerjaan (ANTI GHOST SESSION)
      if (validExams.length > 0) {
        const { data: sessionData } = await supabase
          .from('exam_sessions')
          .select('schedule_id, status, score')
          .eq('student_id', studentId)
          .in('schedule_id', validExams.map(v => v.id));

        const examsWithStatus = validExams.map(ex => {
          // Cari semua sesi untuk jadwal ini
          const studentSessions = sessionData?.filter(s => s.schedule_id === ex.id) || [];
          
          let bestSession = null;
          if (studentSessions.length > 0) {
            // Prioritas Sesi: 1. Finished, 2. Locked, 3. Active
            bestSession = studentSessions.find(s => s.status === 'finished') || 
                          studentSessions.find(s => s.status === 'locked') || 
                          studentSessions[0];
          }

          return {
            ...ex,
            studentStatus: bestSession?.status || 'not_started',
            studentScore: bestSession?.score || null
          };
        });

        examsWithStatus.sort((a, b) => {
           if (a.studentStatus === 'finished' && b.studentStatus !== 'finished') return 1;
           if (a.studentStatus !== 'finished' && b.studentStatus === 'finished') return -1;
           return 0;
        });

        setAvailableExams(examsWithStatus);
      } else {
        setAvailableExams([]);
      }

      // 6. TARIK RIWAYAT NILAI 
      const { data: historyData } = await supabase
        .from('exam_sessions')
        .select(`id, score, finished_at, schedules ( exams ( title, type, subjects (name) ) )`)
        .eq('student_id', studentId)
        .eq('status', 'finished')
        .order('finished_at', { ascending: false });

      if (historyData) {
        // Biar riwayat juga bebas ghost session (filter ID yang unik aja kalau perlu)
        const uniqueHistory = [];
        const seenSchedules = new Set();
        for (const h of historyData) {
          if (!seenSchedules.has(h.schedules?.exams?.title)) {
            seenSchedules.add(h.schedules?.exams?.title);
            uniqueHistory.push(h);
          }
        }
        setExamHistory(uniqueHistory);
      }

    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const toggleDarkMode = () => {
    if (isDark) {
      document.documentElement.classList.remove('dark');
      localStorage.theme = 'light';
      setIsDark(false);
    } else {
      document.documentElement.classList.add('dark');
      localStorage.theme = 'dark';
      setIsDark(true);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('user_session');
    window.location.href = '/login';
  };

  // FUNGSI POP UP TOKEN
  const handleStartExam = (schedule) => {
    const examType = schedule.exams?.type;
    const isStrictLogistics = ['PAS/PAT', 'SAJ'].includes(examType);

    if (isStrictLogistics && !logistics) {
      Swal.fire({
        title: 'Akses Ditolak!',
        text: 'Anda belum terdaftar di Ruangan & Sesi manapun untuk ujian ini. Silahkan lapor ke Pengawas/Kurikulum.',
        icon: 'error'
      });
      return;
    }

    setSelectedExam(schedule);
    setTokenInput(['', '', '', '', '', '']);
    setShowTokenModal(true);
    setTimeout(() => inputRefs.current[0]?.focus(), 100);
  };

  const handleTokenChange = (index, value) => {
    if (value.length > 1) value = value.slice(-1);
    const newToken = [...tokenInput];
    newToken[index] = value.toUpperCase();
    setTokenInput(newToken);
    if (value && index < 5) inputRefs.current[index + 1].focus();
  };

  const handleTokenKeyDown = (index, e) => {
    if (e.key === 'Backspace' && !tokenInput[index] && index > 0) {
      inputRefs.current[index - 1].focus();
    }
  };

  const verifyTokenAndStart = () => {
    const enteredToken = tokenInput.join('');
    if (enteredToken === selectedExam.token) {
      Swal.fire({
        title: 'Token Valid!',
        text: 'Selamat mengerjakan ujian.',
        icon: 'success',
        timer: 1500,
        showConfirmButton: false
      }).then(() => {
        setShowTokenModal(false);
        navigate(`/exam-interface/${selectedExam.id}`);
      });
    } else {
      Swal.fire({
        title: 'Token Salah!',
        text: 'Silakan minta token yang valid ke pengawas.',
        icon: 'error',
        confirmButtonColor: '#ea580c'
      });
      setTokenInput(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    }
  };

  // FUNGSI POP UP LIHAT NILAI
  const handleShowScore = (schedule) => {
    Swal.fire({
      title: 'NILAI UJIAN',
      html: `
        <p class="text-slate-500 font-bold mb-4 uppercase text-xs tracking-widest">${schedule.exams?.title}</p>
        <div style="font-size: 80px; font-weight: 900; color: #10b981; line-height: 1;">${schedule.studentScore ?? 0}</div>
        <p class="text-emerald-600 font-bold mt-4 uppercase flex items-center justify-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg> SELESAI
        </p>
      `,
      confirmButtonColor: '#ea580c',
      confirmButtonText: 'Tutup',
      customClass: {
        popup: 'rounded-[2rem]'
      }
    });
  };

  const formatDateShort = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('id-ID', { day: 'numeric', month: 'short', year: 'numeric' });
  };

  if (!student) return null;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 transition-colors duration-500">
      <nav className="bg-white dark:bg-zinc-900 border-b dark:border-zinc-800 px-6 py-4 sticky top-0 z-10 transition-colors">
        <div className="max-w-5xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="bg-orange-600 p-2 rounded-lg">
              <LayoutDashboard size={20} className="text-white" />
            </div>
            <h1 className="text-xl font-black text-slate-800 dark:text-white italic tracking-tighter">
              EXAM <span className="text-orange-600">JINGGA</span>
            </h1>
          </div>
          
          <div className="flex items-center gap-2 md:gap-4">
            <button onClick={toggleDarkMode} className="p-2.5 rounded-xl bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-orange-400 hover:ring-2 ring-orange-500/50 transition-all">
              {isDark ? <Sun size={20} /> : <Moon size={20} />}
            </button>
            <button onClick={handleLogout} className="flex items-center gap-2 text-red-500 font-bold hover:bg-red-50 dark:hover:bg-red-900/10 px-4 py-2 rounded-xl transition-all">
              <LogOut size={18}/> <span className="hidden md:block">Keluar</span>
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto p-6 animate-in fade-in zoom-in-95 duration-700 slide-in-from-bottom-4 text-left">
        <div className="bg-gradient-to-br from-orange-500 to-orange-700 rounded-[2rem] p-8 text-white shadow-xl shadow-orange-500/20 mb-8 relative overflow-hidden">
          <div className="relative z-10">
            <p className="text-orange-100 font-medium mb-1">Selamat Datang,</p>
            <h2 className="text-3xl md:text-4xl font-black uppercase mb-4 tracking-tight">{student.full_name || student.name}</h2>
            <div className="flex flex-wrap gap-4">
              <div className="bg-white/20 backdrop-blur-md px-4 py-2 rounded-full flex items-center gap-2 border border-white/10">
                <GraduationCap size={18}/>
                <span className="font-bold text-sm">{student.classes?.name || student.class}</span>
              </div>
              <div className="bg-white/20 backdrop-blur-md px-4 py-2 rounded-full flex items-center gap-2 border border-white/10">
                <User size={18}/>
                <span className="font-bold text-sm">Siswa Aktif</span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 space-y-6">
            <h3 className="text-lg font-bold text-slate-800 dark:text-white flex items-center gap-2">
              <BookOpen size={20} className="text-orange-600"/> Daftar Ujian Hari Ini
            </h3>
            
            {loading ? (
              <div className="bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-[2rem] p-12 text-center animate-pulse">
                <p className="text-orange-600 font-black italic uppercase">Mencari Jadwal Hari Ini...</p>
              </div>
            ) : availableExams.length === 0 ? (
              <div className="bg-white dark:bg-zinc-900 border-2 border-dashed border-slate-200 dark:border-zinc-800 rounded-[2rem] p-12 text-center transition-colors">
                <div className="bg-slate-100 dark:bg-zinc-800 w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Clock size={32} className="text-slate-400" />
                </div>
                <h4 className="font-bold text-slate-800 dark:text-zinc-200 uppercase">Belum Ada Jadwal Ujian</h4>
                <p className="text-sm text-slate-500 mt-1">Ujian yang aktif pada hari ini akan muncul di sini.</p>
              </div>
            ) : (
              <div className="grid gap-4">
                {availableExams.map(sch => (
                  <div key={sch.id} className={`bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4 transition-colors ${sch.studentStatus === 'finished' ? 'border-emerald-200 dark:border-emerald-800/50 opacity-80' : 'border-slate-200 dark:border-zinc-800 hover:border-orange-500'}`}>
                    <div>
                      <span className={`text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-widest ${sch.studentStatus === 'finished' ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30' : 'bg-orange-100 text-orange-600 dark:bg-orange-900/30'}`}>
                        {sch.exams?.type}
                      </span>
                      <h4 className="text-xl font-black text-slate-900 dark:text-white uppercase italic mt-2">{sch.exams?.title}</h4>
                      <p className="text-slate-500 text-sm font-bold">
                        {sch.exams?.subjects?.name} 
                        {['PAS/PAT', 'SAJ'].includes(sch.exams?.type) ? ` • ${sch.session_no === 0 ? 'Semua Sesi' : 'Sesi ' + sch.session_no}` : ''}
                      </p>
                    </div>

                    <div className="flex-shrink-0 w-full md:w-auto mt-2 md:mt-0">
                      {/* TOMBOL LIHAT NILAI & MULAI KERJAKAN */}
                      {sch.studentStatus === 'finished' ? (
                        <button onClick={() => handleShowScore(sch)} className="w-full md:w-auto bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-4 rounded-2xl font-black uppercase text-xs tracking-widest flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-600/20">
                          <CheckCircle size={16}/> Lihat Nilai
                        </button>
                      ) : sch.studentStatus === 'locked' ? (
                         <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800/50 px-5 py-3 rounded-2xl flex items-center justify-center">
                          <span className="text-red-500 font-black text-xs uppercase flex items-center gap-2"><AlertTriangle size={16}/> Terkunci Admin</span>
                        </div>
                      ) : (
                        <button onClick={() => handleStartExam(sch)} className="w-full md:w-auto bg-slate-900 dark:bg-white dark:text-black text-white px-6 py-4 rounded-2xl font-black uppercase text-xs tracking-widest flex items-center justify-center gap-2 hover:scale-105 transition-all shadow-lg">
                          <Key size={16}/> {sch.studentStatus === 'active' ? 'Lanjutkan' : 'Mulai Kerjakan'}
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {/* RIWAYAT NILAI SISWA */}
            <h3 className="text-lg font-bold text-slate-800 dark:text-white flex items-center gap-2 pt-6 border-t border-slate-200 dark:border-zinc-800">
              <FileSpreadsheet size={20} className="text-emerald-600"/> Riwayat Ujian (Selesai)
            </h3>
            
            <div className="bg-white dark:bg-zinc-900 rounded-[2rem] p-6 shadow-sm border border-slate-100 dark:border-zinc-800 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse min-w-[500px]">
                  <thead>
                    <tr className="border-b border-slate-100 dark:border-zinc-800">
                      <th className="pb-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Mata Pelajaran</th>
                      <th className="pb-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Waktu</th>
                      <th className="pb-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Nilai Akhir</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-50 dark:divide-zinc-800/50">
                    {examHistory.length === 0 ? (
                      <tr>
                        <td colSpan="3" className="py-6 text-center text-slate-400 font-bold italic text-xs">
                          Belum ada ujian yang diselesaikan.
                        </td>
                      </tr>
                    ) : (
                      examHistory.map((history, idx) => (
                        <tr key={idx} className="hover:bg-slate-50 dark:hover:bg-zinc-800/30 transition-colors">
                          <td className="py-4 text-xs font-black uppercase dark:text-white text-slate-800">
                            {history.schedules?.exams?.subjects?.name}
                            <div className="text-[10px] text-slate-400 mt-1">{history.schedules?.exams?.type} - {history.schedules?.exams?.title}</div>
                          </td>
                          <td className="py-4 text-xs font-bold text-slate-500 dark:text-zinc-400">
                            {formatDateShort(history.finished_at)}
                          </td>
                          <td className="py-4 text-right">
                            <span className="text-lg font-black text-emerald-600 dark:text-emerald-400">
                              {history.score ?? 0}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

          </div>

          <div className="space-y-6">
            <h3 className="text-lg font-bold text-slate-800 dark:text-white uppercase">Aturan Ujian</h3>
            <div className="bg-white dark:bg-zinc-900 border dark:border-zinc-800 rounded-3xl p-6 shadow-sm transition-colors mb-4">
              <p className="text-[10px] font-black uppercase text-slate-400 mb-2 tracking-widest">Informasi Logistik</p>
              {logistics ? (
                <div className="space-y-2 mb-4 pb-4 border-b border-dashed dark:border-zinc-800">
                  <p className="text-sm font-bold dark:text-zinc-300">Ruangan: <span className="text-orange-600 uppercase">{logistics.room_name}</span></p>
                  <p className="text-sm font-bold dark:text-zinc-300">Sesi Ujian: <span className="text-orange-600 uppercase">Sesi {logistics.session_name}</span></p>
                </div>
              ) : (
                <p className="text-xs text-orange-500 font-bold mb-4 pb-4 border-b border-dashed dark:border-zinc-800">Plotting Ruang & Sesi kosong.</p>
              )}
              <ul className="space-y-3">
                <li className="flex gap-3"><div className="w-2 h-2 bg-orange-500 rounded-full mt-1.5 shrink-0"></div><p className="text-xs font-bold text-slate-600 dark:text-zinc-400">Dilarang berpindah Tab/Aplikasi selama ujian.</p></li>
                <li className="flex gap-3"><div className="w-2 h-2 bg-orange-500 rounded-full mt-1.5 shrink-0"></div><p className="text-xs font-bold text-slate-600 dark:text-zinc-400">Mintalah Token Ujian kepada Pengawas.</p></li>
              </ul>
            </div>
          </div>

        </div>
      </main>

      {/* MODAL INPUT TOKEN PIN */}
      {showTokenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 text-center">
          <div className="bg-white dark:bg-zinc-950 w-full max-w-md rounded-[3rem] p-10 shadow-2xl relative border border-slate-100 dark:border-zinc-800">
             <button onClick={() => setShowTokenModal(false)} className="absolute top-6 right-6 p-2 text-slate-400 hover:text-red-500 transition-colors"><X size={24}/></button>
             
             <div className="mx-auto bg-orange-100 dark:bg-orange-900/30 text-orange-600 w-20 h-20 rounded-[2rem] flex items-center justify-center mb-6">
               <KeyRound size={40}/>
             </div>
             
             <h3 className="text-2xl font-black uppercase italic dark:text-white tracking-tighter mb-2">Masukkan Token</h3>
             <p className="text-xs font-bold text-slate-500 mb-8 uppercase">Mintalah 6 digit token kepada pengawas ujian</p>

             <div className="flex justify-center gap-2 mb-8">
               {tokenInput.map((digit, index) => (
                 <input
                   key={index}
                   ref={el => inputRefs.current[index] = el}
                   type="text"
                   value={digit}
                   onChange={e => handleTokenChange(index, e.target.value)}
                   onKeyDown={e => handleTokenKeyDown(index, e)}
                   className="w-12 h-14 bg-slate-50 dark:bg-zinc-900 border-2 border-slate-200 dark:border-zinc-800 rounded-xl text-center text-2xl font-black text-orange-600 uppercase focus:border-orange-500 focus:bg-orange-50 dark:focus:bg-orange-900/20 outline-none transition-all"
                   maxLength={1}
                 />
               ))}
             </div>

             <button onClick={verifyTokenAndStart} className="w-full bg-orange-600 text-white py-4 rounded-2xl font-black uppercase text-xs shadow-lg hover:scale-105 transition-all">
                Verifikasi & Mulai
             </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default StudentDashboard;
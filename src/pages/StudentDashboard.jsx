import React, { useEffect, useState, useRef } from 'react';
import { LogOut, GraduationCap, User, BookOpen, Clock, LayoutDashboard, Moon, Sun, Key, CheckCircle, AlertTriangle, FileSpreadsheet, X, KeyRound, ArrowRight } from 'lucide-react';
import { supabase } from '../supabaseClient';
import { useNavigate } from 'react-router-dom';
import Swal from 'sweetalert2';
import { isExamReadyForStudent } from '../features/schedules/constants';
import { buildTeacherSetKey } from '../features/schedules/utils';

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
        navigate('/login');
      } else {
        setStudent(userData);
        fetchStudentData(userData.id);
      }
    } else {
      navigate('/login');
    }

    if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      setIsDark(true);
      document.documentElement.classList.add('dark');
    }
  }, [navigate]);

  const fetchStudentData = async (studentId) => {
    setLoading(true);
    try {
      const { data: stuData } = await supabase.from('students').select('*, classes(id, name)').eq('id', studentId).single();
      const level = parseInt(stuData.classes.name.split(' ')[0]);

      const formatLocalDate = (value) => {
        const d = new Date(value);
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
      };

      const parseSessionNumber = (sessionName) => {
        const parsed = parseInt(String(sessionName || '').replace(/\D/g, ''), 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
      };

      const { data: logData } = await supabase.from('student_logistics').select('*').eq('student_id', studentId).maybeSingle();
      setLogistics(logData);

      // JEMBATAN GURU
      const { data: assignments } = await supabase.from('teacher_assignments').select('subject_id, teacher_id').eq('class_id', stuData.class_id);
      const myTeachersBySubject = {}; 
      assignments?.forEach(a => {
        if (!myTeachersBySubject[a.subject_id]) myTeachersBySubject[a.subject_id] = [];
        myTeachersBySubject[a.subject_id].push(a.teacher_id);
      });

      const { data: schData } = await supabase.from('schedules').select('*, exams(*, subjects(name)), teachers(full_name)').eq('status', 'active');
      const todayStr = formatLocalDate(new Date());

      // 1. Kumpulkan SEMUA jadwal yang eligible untuk siswa ini
      const collabGroups = new Map();
      const nonCollabSchedules = [];
      let hasInvalidTeacherSet = false;

      (schData || []).forEach((sch) => {
        const isToday = sch.start_time ? formatLocalDate(sch.start_time) === todayStr : false;
        const isReady = isExamReadyForStudent(sch.exams?.status);
        if (!isToday || !isReady) return;

        if (['UH', 'PTS'].includes(sch.exams?.type)) {
          if (sch.class_id === stuData.class_id) nonCollabSchedules.push(sch);
          return;
        }

        const isLevelOk = parseInt(sch.exams?.level) === level;
        const studentSessionNo = parseSessionNumber(logData?.session_name);
        const isSessionOk = sch.session_no === 0 || sch.session_no === studentSessionNo;
        if (!isLevelOk || !isSessionOk) return;

        if (!collabGroups.has(sch.exam_id)) collabGroups.set(sch.exam_id, []);
        collabGroups.get(sch.exam_id).push(sch);
      });

      const collabSchedules = [];
      collabGroups.forEach((groupSchedules) => {
        const subjectId = groupSchedules[0]?.exams?.subject_id;
        const classTeacherSetKey = buildTeacherSetKey(myTeachersBySubject[subjectId] || []);
        const examTeacherSetKey = buildTeacherSetKey(groupSchedules.map((s) => s.teacher_id));

        if (!examTeacherSetKey) {
          hasInvalidTeacherSet = true;
          return;
        }
        if (!classTeacherSetKey || classTeacherSetKey !== examTeacherSetKey) return;

        collabSchedules.push(...groupSchedules);
      });

      if (hasInvalidTeacherSet) {
        Swal.fire('Error', 'Grup guru tidak valid untuk ujian ini.', 'error');
      }

      const validExamsAll = [...nonCollabSchedules, ...collabSchedules];

      // 2. Tarik Data Session berdasarkan semua jadwal yang valid
      let sessionData = [];
      if (validExamsAll.length > 0) {
        const { data: sData } = await supabase.from('exam_sessions')
          .select('*')
          .eq('student_id', studentId)
          .in('schedule_id', validExamsAll.map(v => v.id));
        sessionData = sData || [];
      }

      // 3. Deduplikasi & Prioritas Status Sesi
      const examMap = new Map(); 
      validExamsAll.forEach(sch => {
        if (!examMap.has(sch.exam_id)) {
          const relatedScheduleIds = validExamsAll.filter(v => v.exam_id === sch.exam_id).map(v => v.id);
          const relatedSessions = sessionData.filter(s => relatedScheduleIds.includes(s.schedule_id));
          
          let bestSession = null;
          if (relatedSessions.length > 0) {
             bestSession = relatedSessions.find(s => s.status === 'finished') || 
                           relatedSessions.find(s => s.status === 'locked') || 
                           relatedSessions.find(s => s.status === 'active') || 
                           relatedSessions[0];
          }

          examMap.set(sch.exam_id, {
             ...sch,
             studentStatus: bestSession?.status || 'not_started',
             studentScore: bestSession?.score ?? null
          });
        }
      });

      const finalAvailableExams = Array.from(examMap.values());
      
      setAvailableExams(finalAvailableExams.sort((a) => a.studentStatus === 'finished' ? 1 : -1));

      const { data: history } = await supabase.from('exam_sessions').select(`score, finished_at, schedules(exams(title, subjects(name)))`)
        .eq('student_id', studentId).eq('status', 'finished').order('finished_at', { ascending: false });
      setExamHistory(history || []);
      setStudent(stuData);

    } catch (err) { console.error(err); }
    finally { setLoading(false); }
  };

  const handleStartExam = (sch) => {
    if (['PAS/PAT', 'SAJ'].includes(sch.exams.type) && !logistics) {
      return Swal.fire('Akses Ditolak', 'Data ruangan/sesi Anda belum disetting.', 'error');
    }
    setSelectedExam(sch);
    setTokenInput(['','','','','','']);
    setShowTokenModal(true);
    setTimeout(() => inputRefs.current[0]?.focus(), 100);
  };

  const verifyToken = () => {
    if (tokenInput.join('') === selectedExam.token) {
      setShowTokenModal(false);
      navigate(`/exam-interface/${selectedExam.id}`);
    } else {
      Swal.fire('Token Salah', 'Minta token ke pengawas.', 'error');
      setTokenInput(['','','','','','']);
      inputRefs.current[0].focus();
    }
  };

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

  const toggleDarkMode = () => {
    const newDark = !isDark;
    setIsDark(newDark);
    document.documentElement.classList.toggle('dark');
    localStorage.theme = newDark ? 'dark' : 'light';
  };

  if (loading) return <div className="h-screen flex items-center justify-center bg-zinc-950 text-orange-600 font-black animate-pulse uppercase italic">Sinkronisasi Identitas...</div>;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 transition-colors duration-500 font-sans text-left">
      <nav className="bg-white dark:bg-zinc-900 border-b dark:border-zinc-800 px-6 py-4 sticky top-0 z-30 shadow-sm">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="bg-orange-600 p-2 rounded-xl shadow-lg shadow-orange-600/20"><LayoutDashboard size={20} className="text-white" /></div>
            <h1 className="text-xl font-black text-slate-800 dark:text-white italic tracking-tighter uppercase">EXAM <span className="text-orange-600">JINGGA</span></h1>
          </div>
          <div className="flex items-center gap-4">
            <button onClick={toggleDarkMode} className="p-3 rounded-2xl bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-orange-400 active:scale-90 transition-all">{isDark ? <Sun size={20} /> : <Moon size={20} />}</button>
            <button onClick={() => { localStorage.removeItem('user_session'); navigate('/login'); }} className="hidden md:flex items-center gap-2 text-red-500 font-black uppercase text-[10px] tracking-widest bg-red-50 dark:bg-red-950/20 px-5 py-3 rounded-2xl hover:bg-red-500 hover:text-white transition-all"><LogOut size={16}/> Keluar</button>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto p-6 lg:p-10">
        <div className="bg-gradient-to-br from-orange-500 to-orange-700 rounded-[3rem] p-10 text-white shadow-2xl shadow-orange-500/30 mb-10 relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-20 -mt-20 blur-3xl group-hover:scale-110 transition-all duration-700"></div>
          <div className="relative z-10">
            <p className="text-orange-100 font-bold uppercase tracking-[0.3em] text-[10px] mb-2">Profil Siswa</p>
            <h2 className="text-4xl md:text-5xl font-black uppercase italic tracking-tighter mb-6">{student?.full_name}</h2>
            <div className="flex flex-wrap gap-3">
              <div className="bg-black/20 backdrop-blur-md px-6 py-3 rounded-2xl flex items-center gap-3 border border-white/10">
                <GraduationCap size={20} className="text-orange-300"/><span className="font-black text-xs uppercase tracking-widest">{student?.classes?.name}</span>
              </div>
              <div className="bg-black/20 backdrop-blur-md px-6 py-3 rounded-2xl flex items-center gap-3 border border-white/10">
                <User size={20} className="text-orange-300"/><span className="font-black text-xs uppercase tracking-widest">NIS: {student?.nis}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
          <div className="lg:col-span-2 space-y-8">
            <h3 className="text-xl font-black text-slate-800 dark:text-white uppercase italic flex items-center gap-3"><BookOpen size={24} className="text-orange-600"/> Jadwal Ujian Hari Ini</h3>
            
            {availableExams.length === 0 ? (
              <div className="bg-white dark:bg-zinc-900 border-2 border-dashed border-slate-200 dark:border-zinc-800 rounded-[3rem] p-20 text-center">
                <Clock size={48} className="text-slate-300 mx-auto mb-4 animate-bounce" />
                <h4 className="font-black text-slate-400 uppercase tracking-widest italic text-sm">Tidak ada ujian untuk hari ini.</h4>
              </div>
            ) : (
              <div className="grid gap-6">
                {availableExams.map(sch => (
                  <div key={sch.id} className={`bg-white dark:bg-zinc-900 p-8 rounded-[3rem] border-2 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6 transition-all ${sch.studentStatus === 'finished' ? 'border-emerald-500/30 bg-emerald-50/5 dark:bg-emerald-950/10' : 'border-white dark:border-zinc-900 hover:border-orange-500'}`}>
                    <div className="text-left">
                      <div className="flex items-center gap-2 mb-3">
                        <span className="bg-orange-100 dark:bg-orange-900/40 text-orange-600 px-3 py-1 rounded-lg text-[9px] font-black uppercase tracking-widest">{sch.exams?.type}</span>
                        {sch.studentStatus === 'finished' && <span className="bg-emerald-500 text-white px-3 py-1 rounded-lg text-[9px] font-black uppercase flex items-center gap-1 shadow-lg shadow-emerald-500/20"><CheckCircle size={10}/> Selesai</span>}
                      </div>
                      <h4 className="text-2xl font-black text-slate-900 dark:text-white uppercase italic leading-tight mb-1">{sch.exams?.title}</h4>
                      
                      {/* PENAMBAHAN NAMA GURU KHUSUS UH & PTS */}
                      <p className="text-slate-500 dark:text-zinc-400 text-xs font-bold uppercase tracking-widest leading-relaxed">
                        Mapel: {sch.exams?.subjects?.name} 
                        {['UH', 'PTS'].includes(sch.exams?.type) && sch.teachers?.full_name && (
                           <span className="block mt-1 text-orange-600 dark:text-orange-500">
                             Guru: {sch.teachers.full_name}
                           </span>
                        )}
                      </p>

                    </div>

                    <div>
                      {sch.studentStatus === 'finished' ? (
                        <button onClick={() => handleShowScore(sch)} className="w-full md:w-auto bg-emerald-600 hover:bg-emerald-700 text-white px-8 py-4 rounded-[2rem] font-black uppercase text-[10px] tracking-[0.2em] flex items-center justify-center gap-2 transition-all shadow-lg shadow-emerald-600/20 hover:scale-105 active:scale-95">
                          <CheckCircle size={16}/> Lihat Nilai
                        </button>
                      ) : sch.studentStatus === 'locked' ? (
                        <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 p-5 rounded-[2rem] flex items-center gap-3 text-red-600">
                          <AlertTriangle size={20}/> <span className="text-[10px] font-black uppercase">Terkunci</span>
                        </div>
                      ) : (
                        <button onClick={() => handleStartExam(sch)} className="bg-slate-900 dark:bg-white dark:text-black text-white px-10 py-5 rounded-[2rem] font-black uppercase text-[10px] tracking-[0.2em] flex items-center justify-center gap-3 hover:scale-105 active:scale-95 transition-all shadow-xl">
                          {sch.studentStatus === 'active' ? 'LANJUTKAN' : 'MULAI'} <ArrowRight size={16}/>
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="space-y-8">
            <div className="bg-white dark:bg-zinc-900 p-8 rounded-[3rem] border border-slate-100 dark:border-zinc-800 shadow-sm text-left">
              <h3 className="font-black text-[10px] uppercase text-slate-400 mb-6 tracking-widest flex items-center gap-2">
                <AlertTriangle size={14} className="text-orange-600"/> Aturan & Penempatan
              </h3>
              
              {logistics ? (
                <div className="space-y-4 mb-6 pb-6 border-b border-dashed border-slate-200 dark:border-zinc-800">
                   <div className="flex justify-between items-center p-4 bg-slate-50 dark:bg-zinc-950 rounded-2xl">
                      <span className="text-[10px] font-black text-slate-400 uppercase">Ruangan</span>
                      <span className="font-black dark:text-white uppercase italic text-orange-600">{logistics.room_name}</span>
                   </div>
                   <div className="flex justify-between items-center p-4 bg-slate-50 dark:bg-zinc-950 rounded-2xl">
                      <span className="text-[10px] font-black text-slate-400 uppercase">Sesi</span>
                      <span className="font-black dark:text-white uppercase italic text-orange-600">{logistics.session_name}</span>
                   </div>
                </div>
              ) : (
                <p className="text-[10px] font-bold text-orange-500 uppercase italic mb-6 pb-6 border-b border-dashed border-slate-200 dark:border-zinc-800">Ruangan & Sesi Belum Diploting.</p>
              )}

              <ul className="space-y-4">
                <li className="flex gap-3 items-start"><div className="w-2 h-2 bg-orange-500 rounded-full mt-1.5 shrink-0"></div><p className="text-xs font-bold text-slate-600 dark:text-zinc-400 leading-relaxed">Dilarang berpindah Tab/Aplikasi selama ujian berlangsung.</p></li>
                <li className="flex gap-3 items-start"><div className="w-2 h-2 bg-orange-500 rounded-full mt-1.5 shrink-0"></div><p className="text-xs font-bold text-slate-600 dark:text-zinc-400 leading-relaxed">Mintalah Token Ujian kepada Pengawas Ruangan.</p></li>
                <li className="flex gap-3 items-start"><div className="w-2 h-2 bg-orange-500 rounded-full mt-1.5 shrink-0"></div><p className="text-xs font-bold text-slate-600 dark:text-zinc-400 leading-relaxed">Ujian akan berakhir otomatis saat waktu habis.</p></li>
              </ul>
            </div>

            <div className="bg-white dark:bg-zinc-900 p-8 rounded-[3rem] border border-slate-100 dark:border-zinc-800 shadow-sm text-left">
              <h3 className="font-black text-[10px] uppercase text-slate-400 mb-6 tracking-widest flex items-center gap-2"><FileSpreadsheet size={14} className="text-emerald-600"/> Riwayat Nilai</h3>
              <div className="space-y-4 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                {examHistory.length === 0 ? (
                  <p className="text-[10px] font-bold text-slate-400 italic py-4 text-center">Belum ada ujian diselesaikan.</p>
                ) : (
                  examHistory.map((h, i) => (
                    <div key={i} className="flex justify-between items-center p-4 hover:bg-slate-50 dark:hover:bg-zinc-800 rounded-2xl transition-all border-b dark:border-zinc-800 last:border-0">
                       <div className="max-w-[70%]">
                          <p className="text-xs font-black uppercase dark:text-white truncate">{h.schedules?.exams?.subjects?.name}</p>
                          <p className="text-[8px] font-bold text-slate-400 uppercase mt-1">{h.schedules?.exams?.title}</p>
                       </div>
                       <span className="text-xl font-black text-emerald-500 italic">{h.score}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* TOKEN MODAL */}
      {showTokenModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="bg-white dark:bg-zinc-950 w-full max-w-md rounded-[3.5rem] p-12 shadow-2xl relative border border-slate-100 dark:border-zinc-800">
             <button onClick={() => setShowTokenModal(false)} className="absolute top-10 right-10 p-2 text-slate-400 hover:text-red-500 transition-colors"><X size={24}/></button>
             <div className="mx-auto bg-orange-100 dark:bg-orange-900/40 text-orange-600 w-20 h-20 rounded-[2rem] flex items-center justify-center mb-8"><KeyRound size={40}/></div>
             <h3 className="text-3xl font-black uppercase italic dark:text-white tracking-tighter mb-2 text-center">Input Token</h3>
             <p className="text-[10px] font-black text-slate-400 mb-10 uppercase tracking-widest text-center">Silahkan minta 6 digit token ke pengawas</p>
             <div className="flex justify-center gap-3 mb-10">
               {tokenInput.map((digit, index) => (
                 <input key={index} ref={el => inputRefs.current[index] = el} type="text" value={digit} onChange={e => {
                   const val = e.target.value.toUpperCase().slice(-1);
                   const nt = [...tokenInput]; nt[index] = val; setTokenInput(nt);
                   if (val && index < 5) inputRefs.current[index + 1].focus();
                 }} onKeyDown={e => { if (e.key === 'Backspace' && !tokenInput[index] && index > 0) inputRefs.current[index - 1].focus(); }}
                 className="w-12 h-16 bg-slate-50 dark:bg-zinc-900 border-2 border-slate-200 dark:border-zinc-800 rounded-2xl text-center text-3xl font-black text-orange-600 focus:border-orange-500 outline-none transition-all"/>
               ))}
             </div>
             <button onClick={verifyToken} className="w-full bg-orange-600 text-white py-5 rounded-[2rem] font-black uppercase text-xs tracking-[0.3em] shadow-xl shadow-orange-600/30 hover:scale-105 transition-all">VALIDASI & MULAI</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default StudentDashboard;

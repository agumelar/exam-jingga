import React, { useEffect, useState } from 'react';
import { LogOut, GraduationCap, User, BookOpen, Clock, LayoutDashboard, Moon, Sun, KeyRound, CheckCircle, AlertTriangle, FileSpreadsheet, ArrowRight, Sparkles, RefreshCw } from 'lucide-react';
import { supabase } from '../supabaseClient';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Swal from 'sweetalert2';
import { isExamReadyForStudent } from '../features/schedules/constants';
import { buildTeacherSetKey, isWithinLocalRange } from '../features/schedules/utils';
import TokenInputOTP from '../components/TokenInputOTP';

const StudentDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [student, setStudent] = useState(null);
  const [logistics, setLogistics] = useState(null);
  const [availableExams, setAvailableExams] = useState([]);
  const [examHistory, setExamHistory] = useState([]); 
  const [isDark, setIsDark] = useState(false); 
  const [loading, setLoading] = useState(true);
  const [validatingToken, setValidatingToken] = useState(false);
  
  // State Modal Token OTP
  const [showTokenModal, setShowTokenModal] = useState(false);
  const [selectedExam, setSelectedExam] = useState(null);

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
      const { data: stuData } = await supabase
        .from('students')
        .select('*, classes(id, name, major:majors(code, name))')
        .eq('id', studentId)
        .single();
      
      if (!stuData) return;
      setStudent(prev => ({ ...prev, ...stuData }));

      const level = parseInt(stuData.classes?.name?.split(' ')[0]) || 10;

      const parseSessionNumber = (sessionName) => {
        const parsed = parseInt(String(sessionName || '').replace(/\D/g, ''), 10);
        return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
      };

      const { data: logData } = await supabase
        .from('student_logistics')
        .select('*')
        .eq('student_id', studentId)
        .maybeSingle();
      setLogistics(logData);

      // Jembatan Guru
      const { data: assignments } = await supabase
        .from('teacher_assignments')
        .select('subject_id, teacher_id')
        .eq('class_id', stuData.class_id);
      
      const myTeachersBySubject = {}; 
      assignments?.forEach(a => {
        if (!myTeachersBySubject[a.subject_id]) myTeachersBySubject[a.subject_id] = [];
        myTeachersBySubject[a.subject_id].push(a.teacher_id);
      });

      const { data: schData } = await supabase
        .from('schedules')
        .select('*, exams(*, subjects(name)), teachers(full_name)')
        .eq('status', 'active');
      
      const now = new Date();
      const nonCollabSchedules = [];
      const collabGroups = new Map();

      (schData || []).forEach((sch) => {
        const isReady = isExamReadyForStudent(sch.exams?.status);
        const isInWindow = isWithinLocalRange({
          now,
          startTime: sch.start_time,
          endTime: sch.end_time,
          durationMinutes: sch.exams?.duration,
        });
        if (!isInWindow || !isReady) return;

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

        if (!examTeacherSetKey) return;
        if (!classTeacherSetKey || classTeacherSetKey !== examTeacherSetKey) return;
        collabSchedules.push(...groupSchedules);
      });

      const allEligibleSchedules = [...nonCollabSchedules, ...collabSchedules];

      // Ambil Sesi Siswa
      const { data: mySessions } = await supabase
        .from('exam_sessions')
        .select('*')
        .eq('student_id', studentId);

      const activeList = [];
      const historyList = [];

      for (const sch of allEligibleSchedules) {
        const mySession = mySessions?.find(s => s.schedule_id === sch.id);
        const studentStatus = mySession ? mySession.status : 'not_started';

        const examItem = {
          ...sch,
          studentStatus,
          score: mySession?.score,
          sessionId: mySession?.id
        };

        if (studentStatus === 'finished') {
          historyList.push(examItem);
        } else {
          activeList.push(examItem);
        }
      }

      setAvailableExams(activeList);
      setExamHistory(historyList);

    } catch (error) {
      console.error('Error fetching student data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenTokenModal = (sch) => {
    setSelectedExam(sch);
    setShowTokenModal(true);
  };

  // Validasi Token Ujian via Atomic RPC
  const handleVerifyTokenAndStart = async (enteredToken) => {
    if (!selectedExam || !student) return;
    setValidatingToken(true);

    try {
      // 1. Eksekusi Atomic RPC Function ke PostgreSQL 17
      const { data: startResult, error: rpcError } = await supabase.rpc('fn_start_student_exam', {
        p_schedule_id: selectedExam.id,
        p_token: enteredToken.trim().toUpperCase(),
        p_student_id: student.id
      });

      if (rpcError) {
        throw new Error(rpcError.message || 'Token ujian tidak valid atau sesi gagal dimulai.');
      }

      setShowTokenModal(false);

      // Simpan session data yang dikembalikan secara atomic
      if (startResult?.session_id) {
        sessionStorage.setItem(`exam_init_${selectedExam.id}`, JSON.stringify(startResult));
      }

      Swal.fire({
        title: 'Token Diterima!',
        text: 'Membuka lembar kerja ujian...',
        icon: 'success',
        timer: 1200,
        showConfirmButton: false
      }).then(() => {
        navigate(`/exam-interface/${selectedExam.id}`);
      });

    } catch (error) {
      Swal.fire({
        title: 'Validasi Gagal',
        text: error.message,
        icon: 'error',
        confirmButtonColor: '#ea580c'
      });
    } finally {
      setValidatingToken(false);
    }
  };

  const toggleDarkMode = () => {
    const newDark = !isDark;
    setIsDark(newDark);
    document.documentElement.classList.toggle('dark');
    localStorage.theme = newDark ? 'dark' : 'light';
  };

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-50 dark:bg-zinc-950">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-2xl bg-orange-600 flex items-center justify-center animate-bounce shadow-xl shadow-orange-600/30">
            <Sparkles size={24} className="text-white" />
          </div>
          <span className="text-xs font-black uppercase tracking-widest text-slate-500 dark:text-zinc-400">
            Sinkronisasi Data Ujian...
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 transition-colors duration-500 font-sans text-left pb-16">
      
      {/* Top Navigation */}
      <nav className="bg-white/80 dark:bg-zinc-900/80 backdrop-blur-md border-b border-slate-100 dark:border-zinc-800 px-4 sm:px-6 py-3.5 sticky top-0 z-30 shadow-xs">
        <div className="max-w-6xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-2.5">
            <div className="bg-orange-600 p-2 rounded-xl shadow-md shadow-orange-600/20 text-white">
              <LayoutDashboard size={18} />
            </div>
            <h1 className="text-lg font-black text-slate-900 dark:text-white italic tracking-tighter uppercase">
              EXAM <span className="text-orange-600">JINGGA</span>
            </h1>
          </div>
          <div className="flex items-center gap-2.5">
            <button 
              onClick={toggleDarkMode} 
              aria-label="Toggle Dark Mode"
              className="p-2.5 rounded-xl bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-orange-400 hover:scale-105 active:scale-95 transition-all cursor-pointer"
            >
              {isDark ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button
              onClick={logout}
              className="flex items-center gap-2 text-red-500 font-black uppercase text-[10px] tracking-widest bg-red-50 dark:bg-red-950/20 px-4 py-2.5 rounded-xl hover:bg-red-500 hover:text-white transition-all cursor-pointer"
            >
              <LogOut size={14}/> Keluar
            </button>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto p-4 sm:p-6 lg:p-10 space-y-8">
        
        {/* Student Profile Card (Jingga Gradient) */}
        <div className="bg-gradient-to-br from-orange-500 to-orange-700 rounded-[2.5rem] sm:rounded-[3rem] p-6 sm:p-10 text-white shadow-2xl shadow-orange-500/20 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-20 -mt-20 blur-3xl pointer-events-none"></div>
          
          <div className="relative z-10 space-y-4">
            <span className="inline-block px-3 py-1 bg-white/20 backdrop-blur-md rounded-full text-[10px] font-black uppercase tracking-widest text-orange-100">
              Peserta Ujian Resmi
            </span>
            <h2 className="text-2xl sm:text-4xl font-black uppercase italic tracking-tight leading-tight">
              {student?.full_name}
            </h2>
            <div className="flex flex-wrap gap-2.5 sm:gap-3 pt-1">
              <div className="bg-black/20 backdrop-blur-md px-4 py-2 rounded-xl flex items-center gap-2 border border-white/10 text-xs font-black uppercase tracking-wider">
                <GraduationCap size={16} className="text-orange-300"/>
                <span>{student?.classes?.name || 'Kelas Terdaftar'}</span>
              </div>
              <div className="bg-black/20 backdrop-blur-md px-4 py-2 rounded-xl flex items-center gap-2 border border-white/10 text-xs font-black uppercase tracking-wider">
                <User size={16} className="text-orange-300"/>
                <span>NIS: {student?.nis}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Main Grid: Schedules & Logistics */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8">
          
          {/* Left Column: Active Exams */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-black text-slate-800 dark:text-white uppercase italic flex items-center gap-2.5">
                <BookOpen size={20} className="text-orange-600"/> Jadwal Ujian Tersedia
              </h3>
              <button 
                onClick={() => fetchStudentData(student?.id)} 
                aria-label="Refresh Jadwal"
                className="p-2 text-slate-400 hover:text-orange-600 transition-colors cursor-pointer"
              >
                <RefreshCw size={16} />
              </button>
            </div>
            
            {availableExams.length === 0 ? (
              <div className="bg-white dark:bg-zinc-900 border border-slate-100 dark:border-zinc-800 rounded-[2.5rem] p-12 text-center shadow-xs">
                <Clock size={40} className="text-slate-300 dark:text-zinc-600 mx-auto mb-3" />
                <h4 className="font-black text-slate-400 dark:text-zinc-500 uppercase tracking-widest text-xs">
                  Tidak ada jadwal ujian aktif saat ini.
                </h4>
                <p className="text-[11px] text-slate-400 dark:text-zinc-600 mt-1">
                  Ujian akan muncul otomatis sesuai jam pelaksanaan.
                </p>
              </div>
            ) : (
              <div className="grid gap-4">
                {availableExams.map(sch => (
                  <div 
                    key={sch.id} 
                    className="bg-white dark:bg-zinc-900 p-6 sm:p-7 rounded-[2rem] border border-slate-100 dark:border-zinc-800/80 shadow-xs hover:border-orange-500/50 dark:hover:border-orange-500/50 transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-5"
                  >
                    <div className="space-y-2 text-left">
                      <div className="flex items-center gap-2">
                        <span className="bg-orange-100 dark:bg-orange-950/50 text-orange-600 px-2.5 py-0.5 rounded-lg text-[9px] font-black uppercase tracking-wider">
                          {sch.exams?.type || 'UJIAN'}
                        </span>
                        <span className="text-[10px] font-bold text-slate-400 dark:text-zinc-500">
                          {sch.exams?.duration || 90} Menit
                        </span>
                      </div>
                      <h4 className="text-xl font-black text-slate-900 dark:text-white uppercase italic leading-tight">
                        {sch.exams?.title}
                      </h4>
                      <p className="text-xs font-bold text-slate-500 dark:text-zinc-400">
                        {sch.exams?.subjects?.name} {sch.teachers?.full_name ? `• ${sch.teachers.full_name}` : ''}
                      </p>
                    </div>

                    <button 
                      onClick={() => handleOpenTokenModal(sch)} 
                      className="w-full sm:w-auto bg-orange-600 hover:bg-orange-700 text-white px-8 py-4 rounded-2xl font-black uppercase text-xs tracking-wider flex items-center justify-center gap-2 shadow-lg shadow-orange-600/25 transition-all hover:scale-105 active:scale-95 cursor-pointer shrink-0"
                    >
                      <span>{sch.studentStatus === 'active' ? 'LANJUTKAN' : 'MASUK UJIAN'}</span>
                      <ArrowRight size={16}/>
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right Column: Rules & History */}
          <div className="space-y-6">
            
            {/* Room & Session Allocation */}
            <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-xs">
              <h3 className="font-black text-[10px] uppercase text-slate-400 dark:text-zinc-500 mb-4 tracking-widest flex items-center gap-2">
                <AlertTriangle size={14} className="text-orange-600"/> Ruang & Sesi Logistik
              </h3>
              
              {logistics ? (
                <div className="grid grid-cols-2 gap-3 mb-4">
                   <div className="p-3.5 bg-slate-50 dark:bg-zinc-950 rounded-2xl text-center">
                      <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider block mb-1">Ruangan</span>
                      <span className="font-black dark:text-white uppercase italic text-orange-600 text-sm">{logistics.room_name}</span>
                   </div>
                   <div className="p-3.5 bg-slate-50 dark:bg-zinc-950 rounded-2xl text-center">
                      <span className="text-[9px] font-black text-slate-400 uppercase tracking-wider block mb-1">Sesi</span>
                      <span className="font-black dark:text-white uppercase italic text-orange-600 text-sm">{logistics.session_name}</span>
                   </div>
                </div>
              ) : (
                <p className="text-xs font-bold text-slate-500 dark:text-zinc-400 mb-4 pb-4 border-b border-dashed border-slate-100 dark:border-zinc-800">
                  Pembagian ruangan & sesi belum dikocok oleh panitia.
                </p>
              )}

              <ul className="space-y-2.5 text-[11px] font-bold text-slate-600 dark:text-zinc-400">
                <li className="flex gap-2.5 items-start">
                  <div className="w-1.5 h-1.5 bg-orange-500 rounded-full mt-1.5 shrink-0"></div>
                  <span>Dilarang berpindah aplikasi atau tab selama ujian.</span>
                </li>
                <li className="flex gap-2.5 items-start">
                  <div className="w-1.5 h-1.5 bg-orange-500 rounded-full mt-1.5 shrink-0"></div>
                  <span>Minta token 6 karakter kepada pengawas ruangan.</span>
                </li>
                <li className="flex gap-2.5 items-start">
                  <div className="w-1.5 h-1.5 bg-orange-500 rounded-full mt-1.5 shrink-0"></div>
                  <span>Jawaban tersimpan otomatis setiap kali Anda memilih opsi.</span>
                </li>
              </ul>
            </div>

            {/* Exam Score History */}
            <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-xs">
              <h3 className="font-black text-[10px] uppercase text-slate-400 dark:text-zinc-500 mb-4 tracking-widest flex items-center gap-2">
                <FileSpreadsheet size={14} className="text-emerald-600"/> Riwayat Ujian Selesai
              </h3>
              
              <div className="space-y-2.5 max-h-[240px] overflow-y-auto pr-1 custom-scrollbar">
                {examHistory.length === 0 ? (
                  <p className="text-xs font-bold text-slate-400 dark:text-zinc-500 italic py-4 text-center">
                    Belum ada riwayat ujian yang diselesaikan.
                  </p>
                ) : (
                  examHistory.map((h, i) => (
                    <div key={i} className="flex justify-between items-center p-3 hover:bg-slate-50 dark:hover:bg-zinc-800/60 rounded-xl transition-all border-b border-slate-100 dark:border-zinc-800/50 last:border-0">
                       <div className="max-w-[70%]">
                          <p className="text-xs font-black uppercase dark:text-white truncate">{h.exams?.subjects?.name}</p>
                          <p className="text-[9px] font-bold text-slate-400 uppercase mt-0.5">{h.exams?.title}</p>
                       </div>
                       <span className="text-base font-black text-emerald-500 italic">{h.score ?? 0}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

        </div>
      </main>

      {/* Alphanumeric Token Input OTP Modal */}
      <TokenInputOTP 
        isOpen={showTokenModal}
        onClose={() => setShowTokenModal(false)}
        onSubmit={handleVerifyTokenAndStart}
        loading={validatingToken}
        examTitle={selectedExam?.exams?.title}
        examType={selectedExam?.exams?.type}
      />
    </div>
  );
};

export default StudentDashboard;

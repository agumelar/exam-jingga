import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { ArrowLeft, Download, FileSpreadsheet, BarChart3, Users, CheckCircle2, AlertTriangle, RefreshCw, Search, Filter, Trophy, AlertCircle } from 'lucide-react';
import Swal from 'sweetalert2';
import * as XLSX from 'xlsx';

const ExamResults = () => {
  const { examId } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('rekap'); 
  
  const [schedule, setSchedule] = useState(null);
  const [exam, setExam] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [analysisData, setAnalysisData] = useState([]);
  const [stats, setStats] = useState({ avg: 0, highest: 0, lowest: 0, completed: 0, total: 0 }); 
  
  // State Pencarian & Filter
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedClass, setSelectedClass] = useState('Semua Kelas');
  
  const [loading, setLoading] = useState(true);
  const [userRole, setUserRole] = useState('');

  useEffect(() => {
    fetchResultData();
  }, [examId]);

  const fetchResultData = async () => {
    setLoading(true);
    try {
      const userSession = JSON.parse(localStorage.getItem('user_session'));
      const role = userSession?.role?.toLowerCase() || ''; 
      const userId = userSession?.id;
      setUserRole(role);

      const { data: schData, error: schErr } = await supabase
        .from('schedules')
        .select(`*, exams(*, subjects(name))`)
        .eq('id', examId)
        .single();
      if (schErr) throw schErr;
      setSchedule(schData);
      setExam(schData.exams);

      // --- LOGIKA SATU RUMAH BANYAK PINTU ---
      const { data: allRelatedSch } = await supabase
        .from('schedules')
        .select('id')
        .eq('exam_id', schData.exam_id);
      const allSchIds = allRelatedSch?.map(s => s.id) || [examId];

      // JEMBATAN LOGIKA GURU (ANTI BOCOR)
      let allowedClassIds = null;
      if (role === 'guru') {
        const { data: assignments } = await supabase
          .from('teacher_assignments')
          .select('class_id')
          .eq('teacher_id', userId)
          .eq('subject_id', schData.exams.subject_id);
        allowedClassIds = assignments?.map(a => a.class_id) || [];
      }

      let idsToFetch = [];
      if (['UH', 'PTS'].includes(schData.exams.type) && schData.class_id) {
        idsToFetch = [schData.class_id];
      } else {
         const { data: allClasses } = await supabase.from('classes').select('id, name');
         const classIdsForLevel = allClasses
            ?.filter(c => c.name.startsWith(schData.exams.level.toString()))
            .map(c => c.id) || [];

         if (role === 'guru' && allowedClassIds) {
            idsToFetch = classIdsForLevel.filter(id => allowedClassIds.includes(id));
         } else {
            idsToFetch = classIdsForLevel;
         }
      }

      if (idsToFetch.length === 0) {
         setParticipants([]); 
         setAnalysisData([]);
         setLoading(false);
         return;
      }
      
      const { data: students } = await supabase
        .from('students')
        .select('*, classes(name)')
        .in('class_id', idsToFetch)
        .eq('status', 'aktif')
        .order('full_name');
        
      setParticipants(students || []);

      // TARIK SESI DARI SEMUA PINTU
      const { data: sessionData } = await supabase
        .from('exam_sessions')
        .select('*')
        .in('schedule_id', allSchIds); 
      setSessions(sessionData || []);

      // PERBAIKAN 1: Tambah !inner biar kunci_jawaban pasti ketarik 100%
      const { data: qData } = await supabase
        .from('exam_questions')
        .select(`question_id, questions!inner(*)`)
        .eq('exam_id', schData.exam_id)
        .order('order_number', { ascending: true });
      
      const realQuestions = qData?.map(q => q.questions).filter(Boolean) || [];
      setQuestions(realQuestions);

      const sessionIds = sessionData?.map(s => s.id) || [];
      let allAnswers = [];
      if (sessionIds.length > 0) {
        const { data: ansData } = await supabase
          .from('student_answers')
          .select('*')
          .in('session_id', sessionIds);
        allAnswers = ansData || [];
      }

      const getBestSession = (studentId) => {
        const studentSessions = (sessionData || []).filter(s => s.student_id === studentId);
        if (studentSessions.length === 0) return null;
        const finished = studentSessions.find(s => s.status === 'finished');
        if (finished) return finished; 
        const locked = studentSessions.find(s => s.status === 'locked');
        if (locked) return locked; 
        return studentSessions[0]; 
      };

      // --- KALKULASI STATISTIK ---
      const bestSessionsAll = (students || []).map(p => getBestSession(p.id)).filter(Boolean);
      const completedSessions = bestSessionsAll.filter(s => s.status === 'finished');
      if (completedSessions.length > 0) {
        const scores = completedSessions.map(s => s.score ?? 0);
        setStats({
          avg: Math.round(scores.reduce((a,b)=>a+b,0) / scores.length),
          highest: Math.max(...scores),
          lowest: Math.min(...scores),
          completed: completedSessions.length,
          total: students?.length || 0
        });
      } else {
        setStats({ avg: 0, highest: 0, lowest: 0, completed: 0, total: students?.length || 0 });
      }

      // --- ANALISIS BUTIR SOAL + PENGECOH ---
      const finishedSessionIds = completedSessions.map(s => s.id);
      const totalFinished = finishedSessionIds.length;

      const analysis = realQuestions.map((q, index) => {
        let correct = 0;
        let wrong = 0;
        let blank = 0;
        let distro = { A: 0, B: 0, C: 0, D: 0, E: 0 };

        finishedSessionIds.forEach(sId => {
          // PERBAIKAN 2: Ambil semua jawaban anak untuk soal ini
          const studentAnswersForQ = allAnswers.filter(a => String(a.session_id) === String(sId) && String(a.question_id) === String(q.id));
          
          // PERBAIKAN 3: Sort dari yang terbaru! (Antisipasi ada jawaban duplikat di database)
          const finalAns = studentAnswersForQ.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0];
          
          // Tarik kunci jawaban dari database
          const kunci = q.correct_answer || q.answer_key || q.kunci_jawaban || q.answer;
          
          // PERBAIKAN 4: Pake .trim() buat ilangin spasi gaib
          const validKunci = kunci ? String(kunci).trim().toUpperCase() : null;

          if (!finalAns || !finalAns.chosen_answer) {
            blank++;
          } else {
            const chosen = String(finalAns.chosen_answer).trim().toUpperCase();
            if (distro.hasOwnProperty(chosen)) distro[chosen]++; 

            if (validKunci && chosen === validKunci) {
              correct++;
            } else {
              wrong++;
            }
          }
        });

        return {
          no: index + 1,
          question_text: q.question_text,
          correct,
          wrong,
          blank,
          distro, 
          correctPercentage: totalFinished > 0 ? ((correct / totalFinished) * 100).toFixed(1) : 0,
        };
      });

      setAnalysisData(analysis);

    } catch (error) {
      console.error(error);
      Swal.fire('Error', 'Gagal memuat data hasil ujian.', 'error');
    } finally {
      setLoading(false);
    }
  };

  const getBestSessionForExport = (studentId) => {
    const studentSessions = sessions.filter(s => s.student_id === studentId);
    if (studentSessions.length === 0) return null;
    const finished = studentSessions.find(s => s.status === 'finished');
    if (finished) return finished;
    const locked = studentSessions.find(s => s.status === 'locked');
    if (locked) return locked;
    return studentSessions[0];
  };

  const exportToExcel = () => {
    if (participants.length === 0) return Swal.fire('Kosong', 'Tidak ada data untuk diexport', 'info');

    const dataRekap = filteredParticipants.map((p, idx) => {
      const session = getBestSessionForExport(p.id);
      return {
        'No': idx + 1,
        'NIS': p.nis,
        'Nama Siswa': p.full_name,
        'Kelas': p.classes?.name || '-',
        'Status': session ? (session.status === 'finished' ? 'Selesai' : session.status === 'locked' ? 'Terkunci' : 'Mengerjakan') : 'Belum Mulai',
        'Nilai Akhir': session?.status === 'finished' ? session.score : 0
      };
    });

    const dataAnalisis = analysisData.map(a => ({
      'No Soal': a.no,
      'Cuplikan Soal': a.question_text?.substring(0, 50) + '...',
      'Jawab Benar': a.correct,
      'Jawab Salah': a.wrong,
      'Kosong': a.blank,
      'Pilih A': a.distro.A, 'Pilih B': a.distro.B, 'Pilih C': a.distro.C, 'Pilih D': a.distro.D, 'Pilih E': a.distro.E,
      'Tuntas (%)': a.correctPercentage + '%'
    }));

    const wb = XLSX.utils.book_new();
    const wsRekap = XLSX.utils.json_to_sheet(dataRekap);
    const wsAnalisis = XLSX.utils.json_to_sheet(dataAnalisis);

    XLSX.utils.book_append_sheet(wb, wsRekap, "Rekap Nilai");
    XLSX.utils.book_append_sheet(wb, wsAnalisis, "Analisis Pengecoh");

    XLSX.writeFile(wb, `Hasil_Ujian_${exam?.subjects?.name}.xlsx`);
  };

  // --- LOGIKA FILTER & SORTING ---
  const availableClasses = Array.from(new Set(participants.map(p => p.classes?.name))).filter(Boolean).sort();

  const filteredParticipants = participants
    .filter(p => {
      const matchSearch = p.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) || p.nis?.toLowerCase().includes(searchTerm.toLowerCase());
      const matchClass = selectedClass === 'Semua Kelas' || p.classes?.name === selectedClass;
      return matchSearch && matchClass;
    })
    .sort((a, b) => {
      const classA = a.classes?.name || '';
      const classB = b.classes?.name || '';
      if (classA !== classB) return classA.localeCompare(classB);
      return (a.full_name || '').localeCompare(b.full_name || '');
    });

  if (loading) return <div className="min-h-screen flex items-center justify-center dark:bg-zinc-950 text-emerald-600 font-black animate-pulse uppercase italic">Mengalkulasi Hasil...</div>;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex font-sans text-left">
      <Sidebar role={userRole} />
      <main className="flex-1 lg:ml-64 p-4 lg:p-8 mt-12 lg:mt-0">
        <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b dark:border-zinc-800 pb-6 text-left">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/schedules')} className="p-3 bg-white dark:bg-zinc-900 rounded-2xl shadow-sm hover:text-emerald-600 transition-all dark:text-white"><ArrowLeft size={20}/></button>
            <div>
              <h2 className="text-2xl font-black text-slate-800 dark:text-zinc-100 uppercase italic tracking-tighter">HASIL UJIAN: {exam?.title}</h2>
              <p className="text-emerald-600 font-black text-xs uppercase tracking-widest">{exam?.subjects?.name} | {exam?.type}</p>
            </div>
          </div>
          <button onClick={exportToExcel} className="bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-2xl font-black text-xs uppercase tracking-widest transition-all shadow-lg flex items-center gap-2"><Download size={16}/> Unduh Excel</button>
        </header>

        {/* --- STATS CARDS --- */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
            <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm flex flex-col items-center justify-center text-center">
                <BarChart3 size={24} className="text-blue-500 mb-2"/>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Rata-Rata</p>
                <p className="text-3xl font-black text-slate-800 dark:text-white italic">{stats.avg}</p>
            </div>
            <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm flex flex-col items-center justify-center text-center">
                <Trophy size={24} className="text-emerald-500 mb-2"/>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Tertinggi</p>
                <p className="text-3xl font-black text-emerald-500 italic">{stats.highest}</p>
            </div>
            <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm flex flex-col items-center justify-center text-center">
                <AlertCircle size={24} className="text-red-500 mb-2"/>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Terendah</p>
                <p className="text-3xl font-black text-red-500 italic">{stats.lowest}</p>
            </div>
            <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm flex flex-col items-center justify-center text-center">
                <Users size={24} className="text-orange-500 mb-2"/>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Progress</p>
                <p className="text-3xl font-black text-slate-800 dark:text-white italic">{stats.completed} <span className="text-sm text-slate-400">/ {stats.total}</span></p>
            </div>
        </div>

        <div className="flex gap-4 mb-6 border-b border-slate-200 dark:border-zinc-800 pb-4 overflow-x-auto">
          {['rekap', 'analisis'].map((tab) => (
             <button key={tab} onClick={() => setActiveTab(tab)} className={`flex items-center gap-2 px-6 py-3 rounded-xl font-black text-xs uppercase tracking-widest transition-all whitespace-nowrap ${activeTab === tab ? 'bg-slate-900 text-white dark:bg-white dark:text-black shadow-md' : 'bg-white dark:bg-zinc-900 text-slate-400 border border-slate-200 dark:border-zinc-800'}`}>
                {tab === 'rekap' ? <FileSpreadsheet size={16}/> : <BarChart3 size={16}/>}
                {tab === 'rekap' ? 'Rekap Nilai Siswa' : 'Analisis Butir Soal'}
             </button>
          ))}
        </div>

        {activeTab === 'rekap' ? (
          <div className="bg-white dark:bg-zinc-900 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-slate-50 dark:border-zinc-800 flex flex-col lg:flex-row gap-4 justify-between items-center">
              <h3 className="w-full lg:w-auto font-black text-xs uppercase tracking-[0.2em] text-slate-400 flex items-center gap-2"><Users size={16} className="text-emerald-600"/> Daftar Peserta</h3>
              <div className="flex flex-col sm:flex-row w-full lg:w-auto gap-3">
                <div className="relative w-full sm:w-64">
                  <Search className="absolute left-4 top-3.5 text-slate-400" size={16}/>
                  <input type="text" placeholder="Cari Nama / NIS..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="w-full bg-slate-50 dark:bg-zinc-950/50 border border-slate-200 dark:border-zinc-800 rounded-xl py-3 pl-11 pr-4 text-xs font-bold outline-none focus:ring-2 focus:ring-emerald-500 transition-all dark:text-white" />
                </div>
                <div className="relative w-full sm:w-48">
                  <Filter className="absolute left-4 top-3.5 text-slate-400" size={16}/>
                  <select value={selectedClass} onChange={(e) => setSelectedClass(e.target.value)} className="w-full bg-slate-50 dark:bg-zinc-950/50 border border-slate-200 dark:border-zinc-800 rounded-xl py-3 pl-11 pr-4 text-xs font-bold outline-none focus:ring-2 focus:ring-emerald-500 transition-all dark:text-white appearance-none cursor-pointer">
                    <option value="Semua Kelas">Semua Kelas</option>
                    {availableClasses.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 dark:bg-zinc-950/50 border-b border-slate-100 dark:border-zinc-800 text-[10px] font-black text-slate-400 uppercase tracking-widest">
                    <th className="p-5">No</th>
                    <th className="p-5">NIS</th>
                    <th className="p-5">Nama Peserta</th>
                    <th className="p-5">Kelas</th>
                    <th className="p-5">Status</th>
                    <th className="p-5 text-right">Nilai Akhir</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-zinc-800">
                  {filteredParticipants.map((p, idx) => {
                    const session = getBestSessionForExport(p.id);
                    return (
                      <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-zinc-800/50 transition-colors">
                        <td className="p-5 text-sm font-bold text-slate-500">{idx + 1}</td>
                        <td className="p-5 text-xs font-mono font-bold dark:text-zinc-300">{p.nis}</td>
                        <td className="p-5 text-sm font-black dark:text-white uppercase">{p.full_name}</td>
                        <td className="p-5 text-xs font-bold dark:text-zinc-300 uppercase">{p.classes?.name}</td>
                        <td className="p-5">
                          <span className={`text-[10px] font-black px-3 py-1 rounded-lg uppercase ${session?.status === 'finished' ? 'bg-emerald-100 text-emerald-600' : session?.status === 'locked' ? 'bg-red-100 text-red-600' : session?.status === 'active' ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-400 dark:bg-zinc-800 dark:text-zinc-400'}`}>
                            {session ? (session.status === 'finished' ? 'Selesai' : session.status === 'locked' ? 'Terkunci' : 'Aktif') : 'Belum Mulai'}
                          </span>
                        </td>
                        <td className="p-5 text-right font-black text-xl dark:text-white">{session?.status === 'finished' ? session.score : '-'}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="bg-white dark:bg-zinc-900 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm overflow-hidden">
             <div className="p-6 border-b border-slate-100 dark:border-zinc-800">
                <h3 className="font-black text-slate-800 dark:text-white uppercase text-sm">Analisis Pengecoh & Kesulitan</h3>
                <p className="text-[10px] text-slate-400 font-bold mt-1">Siswa Selesai: {stats.completed}</p>
             </div>
             <div className="overflow-x-auto custom-scrollbar">
              <table className="w-full text-left border-collapse min-w-[800px]">
                <thead>
                  <tr className="bg-slate-50 dark:bg-zinc-950/50 border-b border-slate-100 dark:border-zinc-800 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">
                    <th className="p-5 text-left">No</th>
                    <th className="p-5 text-left w-1/3">Pertanyaan & Sebaran Jawaban</th>
                    <th className="p-5">Benar</th>
                    <th className="p-5">Salah</th>
                    <th className="p-5">Kosong</th>
                    <th className="p-5 text-right pr-8">Ketuntasan</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-zinc-800">
                  {analysisData.map((item) => (
                    <tr key={item.no} className="hover:bg-slate-50 dark:hover:bg-zinc-800/50 transition-colors">
                      <td className="p-5 text-sm font-black dark:text-zinc-300">{item.no}</td>
                      <td className="p-5">
                        <p className="text-xs font-bold text-slate-600 dark:text-slate-400 line-clamp-2 mb-3 leading-relaxed">{item.question_text}</p>
                        <div className="flex gap-2">
                          {['A', 'B', 'C', 'D', 'E'].map(opt => (
                            <div key={opt} className="flex flex-col items-center bg-slate-100 dark:bg-zinc-800 px-3 py-1.5 rounded-xl border border-slate-200 dark:border-zinc-700 min-w-[36px]">
                              <span className="text-[9px] font-black text-slate-400">{opt}</span>
                              <span className={`text-xs font-black ${item.distro[opt] > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-400 dark:text-zinc-500'}`}>{item.distro[opt]}</span>
                            </div>
                          ))}
                        </div>
                      </td>
                      <td className="p-5 text-center font-black text-emerald-600 text-lg">{item.correct}</td>
                      <td className="p-5 text-center font-black text-red-500 text-lg">{item.wrong}</td>
                      <td className="p-5 text-center font-black text-slate-400 text-lg">{item.blank}</td>
                      <td className="p-5 text-right pr-8">
                        <span className={`text-xl font-black italic ${item.correctPercentage >= 75 ? 'text-emerald-500' : 'text-orange-500'}`}>{item.correctPercentage}%</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
             </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default ExamResults;
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { FileSpreadsheet, Download, ArrowLeft, BarChart3, Users, CheckCircle2, AlertCircle, Search, Trophy } from 'lucide-react';
import Swal from 'sweetalert2';
import * as XLSX from 'xlsx';

const ExamResults = () => {
  const { examId } = useParams();
  const navigate = useNavigate();
  const [exam, setExam] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [results, setResults] = useState([]);
  const [stats, setStats] = useState({ avg: 0, highest: 0, lowest: 0, completed: 0, total: 0 });
  
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [userRole, setUserRole] = useState('');

  useEffect(() => {
    fetchResultData();
  }, [examId]);

  const fetchResultData = async () => {
    setLoading(true);
    try {
      const userSession = JSON.parse(localStorage.getItem('user_session'));
      const role = userSession?.role || '';
      const userId = userSession?.id;
      setUserRole(role);

      // 1. Ambil Jadwal & Detail Exam
      const { data: schData, error: schErr } = await supabase
        .from('schedules')
        .select(`*, exams(*, subjects(name)), classes(name)`)
        .eq('id', examId)
        .single();

      if (schErr || !schData) throw new Error("Data ujian tidak ditemukan");
      setSchedule(schData);
      setExam(schData.exams);

      // 2. Kumpulkan Semua Schedule ID (Satu Rumah, Banyak Pintu)
      const { data: allRelatedSch } = await supabase
        .from('schedules')
        .select('id')
        .eq('exam_id', schData.exam_id);
      
      const allSchIds = allRelatedSch?.map(s => s.id) || [examId];

      // 3. JEMBATAN LOGIKA GURU (Cari Kelas yang Diajar)
      let allowedClassIds = null;
      if (role === 'guru') {
        const { data: assignments } = await supabase
          .from('teacher_assignments')
          .select('class_id')
          .eq('teacher_id', userId)
          .eq('subject_id', schData.exams.subject_id);
        allowedClassIds = assignments?.map(a => a.class_id) || [];
      }

      // 4. Tarik Siswa Sesuai Filter
      let studentQuery = supabase.from('students').select('*, classes(name)');
      
      if (['UH', 'PTS'].includes(schData.exams.type) && schData.class_id) {
        studentQuery = studentQuery.eq('class_id', schData.class_id);
      } else {
        const { data: allClassIds } = await supabase.from('classes').select('id').like('name', `${schData.exams.level} %`);
        let ids = allClassIds?.map(c => c.id) || [];
        
        if (role === 'guru') {
           ids = ids.filter(id => allowedClassIds.includes(id));
        }

        if (ids.length === 0) {
           setResults([]); 
           setLoading(false);
           return; 
        }
        studentQuery = studentQuery.in('class_id', ids);
      }

      const { data: students, error: stdErr } = await studentQuery.eq('status', 'aktif').order('full_name');
      if (stdErr) throw stdErr;

      // 5. Tarik Sesi dari Semua Pintu yang Valid
      const studentIds = students?.map(s => s.id) || [];
      let sessionData = [];
      
      if (studentIds.length > 0) {
         const { data: sData } = await supabase
           .from('exam_sessions')
           .select('*')
           .in('schedule_id', allSchIds)
           .in('student_id', studentIds);
           
         sessionData = sData || [];
      }

      // 6. Mapping Data Siswa & Hitung Statistik
      const finalResults = students.map(student => {
        // Ambil sesi terbaik untuk siswa ini
        const stSessions = sessionData.filter(s => s.student_id === student.id);
        const bestSession = stSessions.find(s => s.status === 'finished') || 
                            stSessions.find(s => s.status === 'locked') || 
                            stSessions.find(s => s.status === 'active');

        return {
          ...student,
          session: bestSession || null,
          score: bestSession?.status === 'finished' ? (bestSession.score ?? 0) : null,
          status: bestSession ? bestSession.status : 'Belum Ujian'
        };
      });

      setResults(finalResults);

      // Kalkulasi Statistik Cepat
      const completed = finalResults.filter(r => r.score !== null);
      if (completed.length > 0) {
        const scores = completed.map(r => r.score);
        const sum = scores.reduce((a, b) => a + b, 0);
        setStats({
          avg: Math.round(sum / completed.length),
          highest: Math.max(...scores),
          lowest: Math.min(...scores),
          completed: completed.length,
          total: finalResults.length
        });
      } else {
        setStats({ avg: 0, highest: 0, lowest: 0, completed: 0, total: finalResults.length });
      }

    } catch (error) {
      console.error(error);
      Swal.fire('Error', error.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const exportToExcel = () => {
    if (results.length === 0) {
      return Swal.fire('Kosong', 'Tidak ada data untuk diekspor.', 'warning');
    }

    const dataToExport = results.map((r, index) => ({
      'No': index + 1,
      'NIS': r.nis,
      'Nama Siswa': r.full_name,
      'Kelas': r.classes?.name,
      'Status': r.status === 'finished' ? 'Selesai' : (r.status === 'active' ? 'Sedang Ujian' : (r.status === 'locked' ? 'Terkunci' : 'Belum Mulai')),
      'Nilai': r.score !== null ? r.score : '0'
    }));

    const ws = XLSX.utils.json_to_sheet(dataToExport);
    
    // Styling Kolom Lebar Excel
    const wscols = [{wch: 5}, {wch: 15}, {wch: 35}, {wch: 15}, {wch: 15}, {wch: 10}];
    ws['!cols'] = wscols;

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Rekap Nilai");
    
    // Nama file rapih
    const className = ['UH', 'PTS'].includes(exam?.type) ? schedule?.classes?.name : `Level ${exam?.level}`;
    const filename = `Nilai_${exam?.type}_${exam?.subjects?.name}_${className}.xlsx`.replace(/\s+/g, '_');
    
    XLSX.writeFile(wb, filename);
  };

  const filteredResults = results.filter(r => 
    r.full_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
    r.nis.toLowerCase().includes(searchTerm.toLowerCase()) ||
    r.classes?.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) return <div className="min-h-screen flex items-center justify-center dark:bg-zinc-950 text-orange-600 font-black animate-pulse uppercase italic tracking-widest">Kalkulasi Rekap Nilai...</div>;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex font-sans text-left transition-colors duration-500">
      <Sidebar role={userRole} />
      <main className="flex-1 lg:ml-64 p-4 lg:p-8 mt-12 lg:mt-0">
        
        <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b dark:border-zinc-800 pb-6">
          <div className="flex items-center gap-4 text-left">
            <button onClick={() => navigate('/schedules')} className="p-3 bg-white dark:bg-zinc-900 rounded-2xl shadow-sm hover:text-orange-600 transition-all dark:text-white border border-slate-100 dark:border-zinc-800"><ArrowLeft size={20}/></button>
            <div>
              <h2 className="text-2xl font-black text-slate-800 dark:text-zinc-100 uppercase italic tracking-tighter">{exam?.title}</h2>
              <p className="text-orange-600 font-black text-[10px] uppercase tracking-widest">{exam?.subjects?.name} | {['UH', 'PTS'].includes(exam?.type) ? schedule?.classes?.name || 'KELAS' : `JENJANG ${exam?.level}`}</p>
            </div>
          </div>
          
          <button onClick={exportToExcel} className="flex items-center gap-2 bg-emerald-600 text-white px-6 py-3 rounded-2xl font-black text-xs uppercase tracking-widest hover:bg-emerald-700 transition-all shadow-lg shadow-emerald-600/20 active:scale-95">
            <Download size={16} /> Unduh Excel
          </button>
        </header>

        {/* KARTU STATISTIK */}
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

        <div className="bg-white dark:bg-zinc-900 p-8 rounded-[3rem] border border-slate-100 dark:border-zinc-800 shadow-sm">
            
            <div className="mb-8 relative group max-w-md">
                <div className="absolute inset-y-0 left-5 flex items-center pointer-events-none text-slate-400 group-focus-within:text-orange-600 transition-colors">
                    <Search size={18} />
                </div>
                <input 
                    type="text" 
                    placeholder="Cari siswa atau kelas..." 
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-12 pr-6 py-4 bg-slate-50 dark:bg-zinc-950 border border-slate-100 dark:border-zinc-800 rounded-2xl outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent font-bold dark:text-white transition-all text-sm"
                />
            </div>

            <div className="overflow-x-auto custom-scrollbar pb-4">
                <table className="w-full text-left border-collapse min-w-[700px]">
                    <thead>
                        <tr className="border-b-2 border-slate-100 dark:border-zinc-800">
                            <th className="py-4 px-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">No</th>
                            <th className="py-4 px-4 text-[10px] font-black text-slate-400 uppercase tracking-widest">Identitas Siswa</th>
                            <th className="py-4 px-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Kelas</th>
                            <th className="py-4 px-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Status Sesi</th>
                            <th className="py-4 px-4 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Skor Akhir</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50 dark:divide-zinc-800/50">
                        {filteredResults.length === 0 ? (
                            <tr>
                                <td colSpan="5" className="py-10 text-center text-slate-400 font-bold italic">Tidak ada data siswa ditemukan.</td>
                            </tr>
                        ) : (
                            filteredResults.map((r, idx) => (
                                <tr key={r.id} className="hover:bg-slate-50 dark:hover:bg-zinc-800/30 transition-colors">
                                    <td className="py-4 px-4 text-xs font-bold text-slate-400">{idx + 1}</td>
                                    <td className="py-4 px-4">
                                        <p className="text-sm font-black text-slate-800 dark:text-white uppercase">{r.full_name}</p>
                                        <p className="text-[10px] font-bold text-slate-400 font-mono mt-1">NIS: {r.nis}</p>
                                    </td>
                                    <td className="py-4 px-4 text-center">
                                        <span className="bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-300 px-3 py-1.5 rounded-lg text-[10px] font-black uppercase tracking-widest">
                                            {r.classes?.name}
                                        </span>
                                    </td>
                                    <td className="py-4 px-4 text-center">
                                        {r.status === 'finished' ? (
                                            <span className="inline-flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20 px-3 py-1.5 rounded-lg"><CheckCircle2 size={12}/> Selesai</span>
                                        ) : r.status === 'active' ? (
                                            <span className="inline-flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-blue-600 bg-blue-50 dark:bg-blue-900/20 px-3 py-1.5 rounded-lg"><RefreshCw size={12} className="animate-spin"/> Mengerjakan</span>
                                        ) : r.status === 'locked' ? (
                                            <span className="inline-flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-red-600 bg-red-50 dark:bg-red-900/20 px-3 py-1.5 rounded-lg"><AlertTriangle size={12}/> Terkunci</span>
                                        ) : (
                                            <span className="inline-flex items-center gap-1.5 text-[10px] font-black uppercase tracking-widest text-slate-400">Belum Mulai</span>
                                        )}
                                    </td>
                                    <td className="py-4 px-4 text-right">
                                        <span className={`text-xl font-black italic ${r.score !== null ? 'text-emerald-500' : 'text-slate-300 dark:text-zinc-700'}`}>
                                            {r.score !== null ? r.score : '-'}
                                        </span>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>

      </main>
    </div>
  );
};

export default ExamResults;
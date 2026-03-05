import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { ArrowLeft, Download, FileSpreadsheet, BarChart3, Users, CheckCircle2, XCircle, MinusCircle, RefreshCw } from 'lucide-react';
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

      const { data: schData, error: schErr } = await supabase
        .from('schedules')
        .select(`*, exams(*, subjects(name))`)
        .eq('id', examId)
        .single();
      if (schErr) throw schErr;
      setSchedule(schData);
      setExam(schData.exams);

      // JEMBATAN LOGIKA GURU
      let allowedClassIds = null;
      if (role === 'guru') {
        const { data: assignments } = await supabase
          .from('teacher_assignments')
          .select('class_id')
          .eq('teacher_id', userId)
          .eq('subject_id', schData.exams.subject_id);
        allowedClassIds = assignments?.map(a => a.class_id) || [];
      }

      let studentQuery = supabase.from('students').select('*, classes(name)');
      if (schData.exams.type === 'UH') {
        studentQuery = studentQuery.eq('class_id', schData.class_id);
      } else {
        const { data: allClassIds } = await supabase.from('classes').select('id').like('name', `${schData.exams.level}%`);
        let ids = allClassIds?.map(c => c.id) || [];
        
        if (role === 'guru' && allowedClassIds) {
           ids = ids.filter(id => allowedClassIds.includes(id));
        }

        if (ids.length === 0) {
           setParticipants([]); 
           setLoading(false);
           return;
        }
        studentQuery = studentQuery.in('class_id', ids);
      }
      
      const { data: students } = await studentQuery.eq('status', 'aktif').order('full_name');
      setParticipants(students || []);

      const { data: sessionData } = await supabase
        .from('exam_sessions')
        .select('*')
        .eq('schedule_id', examId);
      setSessions(sessionData || []);

      const { data: qData } = await supabase
        .from('exam_questions')
        .select(`question_id, questions(*)`)
        .eq('exam_id', schData.exam_id)
        .order('order_number', { ascending: true });
      
      const realQuestions = qData?.map(q => q.questions) || [];
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

      // Analisis Butir Soal HANYA DARI SISWA YANG GURU TERSEBUT AJAR!
      const bestSessions = (students || []).map(p => getBestSession(p.id)).filter(s => s && s.status === 'finished');
      const finishedSessionIds = bestSessions.map(s => s.id);
      const totalFinished = finishedSessionIds.length;

      const analysis = realQuestions.map((q, index) => {
        let correct = 0;
        let wrong = 0;
        let blank = 0;

        finishedSessionIds.forEach(sId => {
          const studentAns = allAnswers.find(a => a.session_id === sId && a.question_id === q.id);
          const kunci = q.correct_answer || q.answer_key || q.kunci_jawaban || q.answer;

          if (!studentAns || !studentAns.chosen_answer) {
            blank++;
          } else if (kunci && studentAns.chosen_answer.toUpperCase() === kunci.toUpperCase()) {
            correct++;
          } else {
            wrong++;
          }
        });

        return {
          no: index + 1,
          question_text: q.question_text,
          correct,
          wrong,
          blank,
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

    const dataRekap = participants.map((p, idx) => {
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
      'Kosong/Tidak Jawab': a.blank,
      'Persentase Ketuntasan (%)': a.correctPercentage + '%'
    }));

    const wb = XLSX.utils.book_new();
    const wsRekap = XLSX.utils.json_to_sheet(dataRekap);
    const wsAnalisis = XLSX.utils.json_to_sheet(dataAnalisis);

    wsRekap['!cols'] = [{ wch: 5 }, { wch: 15 }, { wch: 35 }, { wch: 15 }, { wch: 15 }, { wch: 15 }];
    wsAnalisis['!cols'] = [{ wch: 10 }, { wch: 50 }, { wch: 15 }, { wch: 15 }, { wch: 20 }, { wch: 25 }];

    XLSX.utils.book_append_sheet(wb, wsRekap, "Rekap Nilai");
    XLSX.utils.book_append_sheet(wb, wsAnalisis, "Analisis Soal");

    const fileName = `Hasil_${exam?.type}_${exam?.subjects?.name}_${exam?.level || 'UH'}.xlsx`;
    XLSX.writeFile(wb, fileName);
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center dark:bg-zinc-950 text-emerald-600 font-black animate-pulse uppercase italic">Mengalkulasi Hasil & Analisis...</div>;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex font-sans text-left">
      <Sidebar role={userRole} />
      <main className="flex-1 lg:ml-64 p-4 lg:p-8 mt-12 lg:mt-0">
        <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b dark:border-zinc-800 pb-6">
          <div className="flex items-center gap-4 text-left">
            <button onClick={() => navigate('/schedules')} className="p-3 bg-white dark:bg-zinc-900 rounded-2xl shadow-sm hover:text-emerald-600 transition-all dark:text-white"><ArrowLeft size={20}/></button>
            <div>
              <h2 className="text-2xl font-black text-slate-800 dark:text-zinc-100 uppercase italic tracking-tighter">HASIL UJIAN: {exam?.title}</h2>
              <p className="text-emerald-600 font-black text-xs uppercase">{exam?.subjects?.name} | {exam?.type}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <button 
              onClick={fetchResultData} 
              disabled={loading}
              className="flex items-center gap-2 bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-300 hover:text-emerald-600 px-5 py-3 rounded-2xl font-black text-xs uppercase tracking-widest transition-all shadow-sm"
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} /> 
              {loading ? 'Memuat...' : 'Refresh'}
            </button>

            <button 
              onClick={exportToExcel}
              className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-6 py-3 rounded-2xl font-black text-xs uppercase tracking-widest hover:scale-105 transition-all shadow-lg"
            >
              <Download size={16} /> Unduh Excel (.XLSX)
            </button>
          </div>
        </header>

        <div className="flex gap-4 mb-6 border-b border-slate-200 dark:border-zinc-800 pb-4 overflow-x-auto">
          <button 
            onClick={() => setActiveTab('rekap')}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-black text-xs uppercase tracking-widest transition-all whitespace-nowrap ${activeTab === 'rekap' ? 'bg-slate-900 text-white dark:bg-white dark:text-black shadow-md' : 'bg-white dark:bg-zinc-900 text-slate-400 hover:text-slate-800 dark:hover:text-white border border-slate-200 dark:border-zinc-800'}`}
          >
            <FileSpreadsheet size={16}/> Rekap Nilai Siswa
          </button>
          <button 
            onClick={() => setActiveTab('analisis')}
            className={`flex items-center gap-2 px-6 py-3 rounded-xl font-black text-xs uppercase tracking-widest transition-all whitespace-nowrap ${activeTab === 'analisis' ? 'bg-emerald-600 text-white shadow-md shadow-emerald-600/20' : 'bg-white dark:bg-zinc-900 text-slate-400 hover:text-emerald-600 border border-slate-200 dark:border-zinc-800'}`}
          >
            <BarChart3 size={16}/> Analisis Butir Soal
          </button>
        </div>

        {activeTab === 'rekap' && (
          <div className="bg-white dark:bg-zinc-900 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[600px]">
                <thead>
                  <tr className="bg-slate-50 dark:bg-zinc-950/50 border-b border-slate-100 dark:border-zinc-800">
                    <th className="p-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">No</th>
                    <th className="p-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">NIS</th>
                    <th className="p-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Nama Peserta</th>
                    <th className="p-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Kelas</th>
                    <th className="p-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">Status Ujian</th>
                    <th className="p-5 text-[10px] font-black text-slate-400 uppercase tracking-widest text-right">Nilai Akhir</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-zinc-800">
                  {participants.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="p-10 text-center text-slate-400 font-bold italic">
                        Tidak ada siswa di kelas Anda untuk ujian ini.
                      </td>
                    </tr>
                  ) : participants.map((p, idx) => {
                    const session = getBestSessionForExport(p.id);
                    return (
                      <tr key={p.id} className="hover:bg-slate-50 dark:hover:bg-zinc-800/50 transition-colors">
                        <td className="p-5 text-sm font-bold text-slate-500 dark:text-slate-400">{idx + 1}</td>
                        <td className="p-5 text-xs font-mono font-bold dark:text-zinc-300">{p.nis}</td>
                        <td className="p-5 text-sm font-black dark:text-white uppercase">{p.full_name}</td>
                        <td className="p-5 text-xs font-bold dark:text-zinc-300 uppercase">{p.classes?.name}</td>
                        <td className="p-5">
                          {session?.status === 'finished' ? <span className="text-[10px] font-black bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 px-3 py-1 rounded-lg uppercase">Selesai</span> :
                           session?.status === 'locked' ? <span className="text-[10px] font-black bg-red-100 text-red-600 dark:bg-red-900/30 px-3 py-1 rounded-lg uppercase">Terkunci</span> :
                           session?.status === 'active' ? <span className="text-[10px] font-black bg-blue-100 text-blue-600 dark:bg-blue-900/30 px-3 py-1 rounded-lg uppercase">Mengerjakan</span> :
                           <span className="text-[10px] font-bold text-slate-400 italic">Belum Mulai</span>}
                        </td>
                        <td className="p-5 text-right">
                          <span className={`text-xl font-black ${session?.status === 'finished' ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-300 dark:text-zinc-700'}`}>
                            {session?.status === 'finished' ? session.score : '-'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'analisis' && (
          <div className="bg-white dark:bg-zinc-900 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm overflow-hidden">
             <div className="p-6 bg-slate-50 dark:bg-zinc-950/50 border-b border-slate-100 dark:border-zinc-800 flex items-center justify-between">
                <div>
                  <h3 className="font-black text-slate-800 dark:text-white uppercase text-sm">Tingkat Kesulitan Soal</h3>
                  <p className="text-xs text-slate-500 font-medium mt-1">
                    Dihitung dari {participants.map(p => getBestSessionForExport(p.id)).filter(s => s?.status === 'finished').length} siswa yang telah selesai (di kelas Anda).
                  </p>
                </div>
             </div>
             <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse min-w-[700px]">
                <thead>
                  <tr className="bg-slate-50 dark:bg-zinc-950/50 border-b border-slate-100 dark:border-zinc-800">
                    <th className="p-5 text-[10px] font-black text-slate-400 uppercase tracking-widest">No. Soal</th>
                    <th className="p-5 text-[10px] font-black text-slate-400 uppercase tracking-widest w-1/2">Cuplikan Pertanyaan</th>
                    <th className="p-5 text-[10px] font-black text-emerald-500 uppercase tracking-widest text-center">Benar</th>
                    <th className="p-5 text-[10px] font-black text-red-500 uppercase tracking-widest text-center">Salah</th>
                    <th className="p-5 text-[10px] font-black text-slate-400 uppercase tracking-widest text-center">Kosong</th>
                    <th className="p-5 text-[10px] font-black text-blue-500 uppercase tracking-widest text-right">Ketuntasan</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-zinc-800">
                  {analysisData.map((item) => (
                    <tr key={item.no} className="hover:bg-slate-50 dark:hover:bg-zinc-800/50 transition-colors">
                      <td className="p-5 text-sm font-black dark:text-zinc-300 text-center">{item.no}</td>
                      <td className="p-5 text-xs font-bold text-slate-600 dark:text-slate-400 line-clamp-2">{item.question_text}</td>
                      <td className="p-5 text-center">
                        <span className="flex items-center justify-center gap-1 text-emerald-600 font-black"><CheckCircle2 size={14}/> {item.correct}</span>
                      </td>
                      <td className="p-5 text-center">
                        <span className="flex items-center justify-center gap-1 text-red-500 font-black"><XCircle size={14}/> {item.wrong}</span>
                      </td>
                      <td className="p-5 text-center">
                        <span className="flex items-center justify-center gap-1 text-slate-400 font-black"><MinusCircle size={14}/> {item.blank}</span>
                      </td>
                      <td className="p-5 text-right">
                        <div className="flex flex-col items-end gap-1">
                          <span className={`text-sm font-black ${item.correctPercentage >= 75 ? 'text-emerald-500' : item.correctPercentage >= 50 ? 'text-orange-500' : 'text-red-500'}`}>
                            {item.correctPercentage}%
                          </span>
                          <div className="w-16 bg-slate-100 dark:bg-zinc-800 h-1.5 rounded-full overflow-hidden">
                             <div className={`h-full ${item.correctPercentage >= 75 ? 'bg-emerald-500' : item.correctPercentage >= 50 ? 'bg-orange-500' : 'bg-red-500'}`} style={{width: `${item.correctPercentage}%`}}></div>
                          </div>
                        </div>
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
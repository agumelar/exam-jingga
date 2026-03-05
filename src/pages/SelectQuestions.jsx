import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { CheckCircle2, Circle, Save, ArrowLeft, Info, Lock } from 'lucide-react';
import Swal from 'sweetalert2';

const SelectQuestions = () => {
  const { examId } = useParams();
  const navigate = useNavigate();
  const [examInfo, setExamInfo] = useState(null);
  const [bankQuestions, setBankQuestions] = useState([]);
  const [selectedIds, setSelectedIds] = useState([]); // Milik user login
  const [othersSelectedIds, setOthersSelectedIds] = useState([]); // Milik rekan duet
  const [loading, setLoading] = useState(true);
  const [userRole, setUserRole] = useState('');
  const [myId, setMyId] = useState(null);

  useEffect(() => { fetchExamAndQuestions(); }, [examId]);

  const fetchExamAndQuestions = async () => {
    setLoading(true);
    try {
      const userSession = JSON.parse(localStorage.getItem('user_session'));
      setMyId(userSession.id);
      setUserRole(userSession.role || '');

      const { data: schData } = await supabase
        .from('schedules')
        .select(`*, exams(*, subjects(name))`)
        .eq('id', examId)
        .single();
      
      if (!schData) throw new Error("Jadwal tidak ditemukan");
      setExamInfo(schData);

      // Ambil Bank Soal milik Guru login
      const { data: questions } = await supabase.from('questions')
        .select('*')
        .eq('subject_id', schData.exams.subject_id)
        .eq('level', schData.exams.level)
        .eq('created_by', userSession.id); 
      
      setBankQuestions(questions || []);
      
      // Ambil SEMUA soal yang sudah dipilih untuk ujian ini
      const { data: allSelected } = await supabase
        .from('exam_questions')
        .select('question_id, questions(created_by)')
        .eq('exam_id', schData.exam_id);
      
      if (allSelected) {
        // Pisahkan mana yang punya saya, mana yang punya orang lain
        const mine = allSelected.filter(q => q.questions.created_by === userSession.id).map(q => q.question_id);
        const others = allSelected.filter(q => q.questions.created_by !== userSession.id).map(q => q.question_id);
        setSelectedIds(mine);
        setOthersSelectedIds(others);
      }

    } catch (error) {
      Swal.fire('Error', error.message, 'error');
      navigate('/schedules');
    } finally {
      setLoading(false);
    }
  };

  const toggleQuestion = (id) => {
    const totalSelected = selectedIds.length + othersSelectedIds.length;
    
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter(i => i !== id));
    } else {
      if (totalSelected >= examInfo.exams.target_question_count) {
        return Swal.fire('Limit!', `Total target ${examInfo.exams.target_question_count} soal sudah terpenuhi.`, 'warning');
      }
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleSave = async () => {
    const totalNow = selectedIds.length + othersSelectedIds.length;
    
    // Jika soal sudah pas, atau jika mau nyicil dulu
    const { isConfirmed } = await Swal.fire({
      title: 'Simpan Pilihan?',
      text: totalNow < examInfo.exams.target_question_count 
        ? `Baru ${totalNow}/${examInfo.exams.target_question_count} soal. Simpan sementara?`
        : "Soal sudah lengkap. Ajukan validasi ke Admin?",
      icon: 'question',
      showCancelButton: true,
      confirmButtonText: 'Ya, Simpan'
    });

    if (!isConfirmed) return;

    try {
      // SUNTIKAN: Hanya hapus soal MILIK SAYA di ujian ini
      // Kita pakai subquery untuk hapus berdasarkan created_by di tabel questions
      const { data: myOldQuestions } = await supabase
        .from('exam_questions')
        .select('id, questions!inner(created_by)')
        .eq('exam_id', examInfo.exam_id)
        .eq('questions.created_by', myId);

      if (myOldQuestions?.length > 0) {
        await supabase.from('exam_questions').delete().in('id', myOldQuestions.map(q => q.id));
      }
      
      // Insert pilihan baru saya
      if (selectedIds.length > 0) {
        const payload = selectedIds.map((qid) => ({
          exam_id: examInfo.exam_id,
          question_id: qid
        }));
        await supabase.from('exam_questions').insert(payload);
      }
      
      // Jika total sudah pas, ganti status ke waiting_validation
      if (totalNow === examInfo.exams.target_question_count) {
        await supabase.from('exams').update({ status: 'waiting_validation' }).eq('id', examInfo.exam_id);
        Swal.fire('Berhasil!', 'Soal lengkap & diajukan ke Admin.', 'success');
      } else {
        Swal.fire('Tersimpan!', 'Progress berhasil disimpan sementara.', 'success');
      }
      
      navigate('/schedules');
    } catch (error) {
      Swal.fire('Gagal!', error.message, 'error');
    }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center dark:bg-zinc-950 text-orange-600 font-black animate-pulse uppercase italic text-left">Sinkronisasi Bank Soal...</div>;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex font-sans text-left">
      <Sidebar role={userRole} />
      <main className="flex-1 lg:ml-64 p-4 lg:p-8">
        <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/schedules')} className="p-3 bg-white dark:bg-zinc-900 rounded-2xl shadow-sm hover:text-orange-600 transition-all dark:text-white"><ArrowLeft size={20}/></button>
            <div className="text-left">
              <h2 className="text-2xl font-black text-slate-800 dark:text-zinc-100 uppercase italic tracking-tighter">{examInfo?.exams?.title}</h2>
              <p className="text-orange-600 font-black text-xs uppercase tracking-widest">{examInfo?.exams?.subjects?.name} • KELAS {examInfo?.exams?.level}</p>
            </div>
          </div>
          
          <div className="bg-white dark:bg-zinc-900 px-8 py-5 rounded-[2.5rem] shadow-sm border border-orange-500/20 flex items-center gap-8">
             <div className="text-left border-r border-slate-100 dark:border-zinc-800 pr-8">
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Total Terkumpul</p>
                <p className={`text-3xl font-black ${selectedIds.length + othersSelectedIds.length === examInfo?.exams?.target_question_count ? 'text-emerald-500' : 'text-orange-600'}`}>
                  {selectedIds.length + othersSelectedIds.length} <span className="text-slate-300 text-sm">/ {examInfo?.exams?.target_question_count}</span>
                </p>
             </div>
             <button onClick={handleSave} className="bg-slate-900 dark:bg-white dark:text-black text-white px-10 py-4 rounded-2xl font-black uppercase text-xs tracking-widest hover:scale-105 transition-all shadow-xl flex items-center gap-2">
               <Save size={18}/> Simpan & Ajukan
             </button>
          </div>
        </header>

        {/* Info Mode Kolaborasi */}
        {othersSelectedIds.length > 0 && (
          <div className="mb-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-2xl flex items-center gap-3 text-blue-600 dark:text-blue-400 text-xs font-bold">
            <Info size={16}/> <span>Rekan duet Anda sudah memilih {othersSelectedIds.length} soal. Silakan lengkapi sisanya.</span>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4">
          {bankQuestions.map((q, idx) => (
            <div key={q.id} onClick={() => toggleQuestion(q.id)} className={`p-8 rounded-[3rem] border-2 transition-all cursor-pointer flex gap-8 items-start relative group ${selectedIds.includes(q.id) ? 'border-emerald-500 bg-emerald-50/20 dark:bg-emerald-900/10' : 'border-white dark:border-zinc-900 bg-white dark:bg-zinc-900 hover:border-orange-200'}`}>
              <div className="mt-1">
                {selectedIds.includes(q.id) ? <CheckCircle2 className="text-emerald-500" size={32}/> : <Circle className="text-slate-100 dark:text-zinc-800" size={32}/>}
              </div>
              <div className="flex-1 text-left">
                <span className="text-[10px] font-black uppercase text-slate-400 tracking-tighter mb-2 block">SOAL SAYA #{idx + 1}</span>
                <p className="font-bold dark:text-white leading-relaxed text-lg">{q.question_text}</p>
                {q.question_image && <img src={q.question_image} className="max-h-48 rounded-2xl mt-6 border border-slate-100 dark:border-zinc-800 shadow-sm" alt="Soal" />}
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-8 opacity-60 group-hover:opacity-100 transition-opacity">
                  {['a','b','c','d','e'].map(opt => (
                    <div key={opt} className={`text-xs font-bold p-4 rounded-xl border ${q.correct_answer === opt.toUpperCase() ? 'border-emerald-500 text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20' : 'border-slate-50 dark:border-zinc-800 text-slate-400'}`}>
                      <div className="flex flex-col gap-2">
                        <span><span className="uppercase">{opt}:</span> {q[`option_${opt}`]}</span>
                        {q[`image_${opt}`] && <img src={q[`image_${opt}`]} className="h-24 w-24 object-cover rounded-lg border border-slate-100 dark:border-zinc-700 mt-1" alt={`Opsi ${opt}`} />}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
};

export default SelectQuestions;
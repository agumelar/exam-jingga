import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { Calendar, Key, Trash2, X, ShieldCheck, User, Edit3, RefreshCw, BookOpen, Check, AlertCircle, Users, FileSpreadsheet, Unlock, Search, CalendarDays } from 'lucide-react';
import Swal from 'sweetalert2';

const Schedules = () => {
  const navigate = useNavigate();
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [userRole, setUserRole] = useState('');
  const [myTeacherId, setMyTeacherId] = useState(null);
  const [allAssignments, setAllAssignments] = useState([]);
  
  // --- STATE UNTUK FITUR PENCARIAN & FILTER ---
  const [searchTerm, setSearchTerm] = useState('');
  const [dateFilter, setDateFilter] = useState('Semua Ujian');

  const initialForm = {
    title: '', subject_id: '', level: '', class_id: '', teacher_id: '', 
    start_time: '', duration: 60, token: '', target_question_count: 40, 
    type: 'UH', session_no: 'Semua Sesi', sub_type: '' 
  };
  const [formData, setFormData] = useState(initialForm);

  useEffect(() => { fetchInitialData(); fetchExams(); }, []);

  const fetchInitialData = async () => {
    const userSession = localStorage.getItem('user_session');
    if (userSession) {
      const userData = JSON.parse(userSession);
      setMyTeacherId(userData.id);
      setUserRole(userData.role?.toLowerCase() || '');
      const { data: assignData } = await supabase.from('teacher_assignments').select(`subject_id, teacher_id, subjects(id, name), classes(id, name), teachers(id, full_name)`);
      setAllAssignments(assignData || []);
    } else { navigate('/login'); }
  };

  const fetchExams = async () => {
    setLoading(true);
    const user = JSON.parse(localStorage.getItem('user_session'));

    const { data } = await supabase
      .from('schedules')
      .select(`*, exams(*, subjects(name)), teachers(full_name), classes(name)`)
      .order('created_at', { ascending: false });
    
    if (data) {
      const { data: allQuestions } = await supabase
        .from('exam_questions')
        .select('exam_id, questions!inner(created_by)');

      const cleaned = data.map(ex => {
        const teacherInputCount = allQuestions?.filter(q => q.exam_id === ex.exam_id && q.questions.created_by === ex.teacher_id).length || 0;
        
        return {
          ...ex,
          start_time: ex.start_time ? ex.start_time.split('+')[0].replace('T', ' ') : null,
          end_time: ex.end_time ? ex.end_time.split('+')[0].replace('T', ' ') : null,
          my_question_count: teacherInputCount,
          cluster_classes_text: `GABUNGAN KELAS ${ex.exams?.level}` 
        };
      });

      if (user.role === 'guru') {
        const filtered = cleaned.filter(ex => ex.teacher_id === user.id);
        setExams(filtered);
      } else {
        setExams(cleaned); 
      }
    }
    setLoading(false);
  };

  const formatWIB = (dateStr) => {
    if (!dateStr) return '-';
    const t = dateStr.split(/[- : T]/);
    const d = t[2], m = t[1], y = t[0], h = t[3], min = t[4];
    const bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];
    return `${d} ${bulan[parseInt(m)-1]} ${y}, ${h}:${min}`;
  };

  const toSQL = (date) => {
    const p = (n) => n.toString().padStart(2, '0');
    return `${date.getFullYear()}-${p(date.getMonth()+1)}-${p(date.getDate())} ${p(date.getHours())}:${p(date.getMinutes())}:00`;
  };

  const generateToken = () => {
    const char = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let res = '';
    for (let i = 0; i < 6; i++) res += char.charAt(Math.floor(Math.random() * char.length));
    setFormData(prev => ({ ...prev, token: res }));
  };

  const handleEdit = (ex) => {
    setEditingId(ex.id);
    setFormData({
      title: ex.exams?.title || '',
      subject_id: ex.exams?.subject_id || '',
      level: ex.exams?.level || '',
      class_id: ex.class_id || '',
      teacher_id: ex.teacher_id || '',
      start_time: ex.start_time ? ex.start_time.slice(0, 16).replace(' ', 'T') : '',
      duration: ex.exams?.duration || 60,
      token: ex.token || '',
      target_question_count: ex.exams?.target_question_count || 40,
      type: ex.exams?.type || 'UH',
      session_no: ex.session_no || 'Semua Sesi',
      sub_type: (ex.exams?.type === 'PTS' || ex.exams?.type === 'PAS/PAT') ? ex.exams?.title : ''
    });
    setShowModal(true);
  };

  const handleVerify = async (examId) => {
    const { isConfirmed } = await Swal.fire({
      title: 'Verifikasi Ujian?',
      text: "Setelah diverifikasi, soal siap diakses oleh siswa.",
      icon: 'info',
      showCancelButton: true,
      confirmButtonText: 'Ya, Verifikasi!'
    });

    if (isConfirmed) {
      try {
        await supabase.from('exams').update({ status: 'validated' }).eq('id', examId);
        Swal.fire('Terverifikasi!', 'Ujian siap dilaksanakan.', 'success');
        fetchExams();
      } catch (err) {
        Swal.fire('Error', 'Gagal memverifikasi', 'error');
      }
    }
  };

  const handleUnlockUH = async (examId) => {
    const { isConfirmed } = await Swal.fire({
      title: 'Buka Kunci Ujian?',
      text: "Status ujian akan kembali jadi 'Tunggu Soal'. Siswa tidak bisa mengakses ujian ini sampai Anda menyimpan soal kembali.",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Ya, Buka Kunci!'
    });

    if (isConfirmed) {
      try {
        await supabase.from('exams').update({ status: 'pending_selection' }).eq('id', examId);
        Swal.fire('Terbuka!', 'Silakan pilih atau revisi ulang soal Anda.', 'success');
        fetchExams();
      } catch (err) {
        Swal.fire('Error', 'Gagal membuka kunci ujian', 'error');
      }
    }
  };

  const handleSaveSchedule = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (!formData.subject_id) throw new Error("Mapel wajib dipilih!");
      const startObj = new Date(formData.start_time);
      const endObj = new Date(startObj.getTime() + formData.duration * 60000);
      const finalStart = toSQL(startObj);
      const finalEnd = toSQL(endObj);

      const finalTitle = (formData.type === 'PTS' || formData.type === 'PAS/PAT') ? formData.sub_type : (formData.type === 'SAJ' ? "Asesmen Sumatif Akhir Jenjang" : formData.title);
      const initialStatus = 'pending_selection';
      const parsedSessionNo = formData.session_no === 'Semua Sesi' ? 0 : parseInt(formData.session_no);
      const totalTarget = parseInt(formData.target_question_count);

      if (editingId) {
        const scheduleData = exams.find(ex => ex.id === editingId);
        
        await supabase.from('exams').update({ 
          title: finalTitle, duration: parseInt(formData.duration), target_question_count: totalTarget, type: formData.type
        }).eq('id', scheduleData.exam_id);
        
        const { data: existingSchedules } = await supabase.from('schedules').select('id, teacher_id').eq('exam_id', scheduleData.exam_id);
        
        if (['PAS/PAT', 'SAJ'].includes(formData.type)) {
           const matchedAssignments = allAssignments.filter(a => parseInt(a.classes.name.split(' ')[0]) === parseInt(formData.level) && a.subject_id === formData.subject_id);
           const teacherCountPerClass = {};
           matchedAssignments.forEach(a => {
             if (!teacherCountPerClass[a.classes.id]) teacherCountPerClass[a.classes.id] = new Set();
             teacherCountPerClass[a.classes.id].add(a.teacher_id);
           });
           
           let maxTeachersPerClass = 1;
           for (const classId in teacherCountPerClass) {
             if (teacherCountPerClass[classId].size > maxTeachersPerClass) maxTeachersPerClass = teacherCountPerClass[classId].size;
           }

           const baseQuota = Math.floor(totalTarget / maxTeachersPerClass);
           const remainder = totalTarget % maxTeachersPerClass;

           for (let i = 0; i < existingSchedules.length; i++) {
             const sch = existingSchedules[i];
             const quota = baseQuota + (i < remainder ? 1 : 0);
             
             await supabase.from('schedules').update({ 
               start_time: finalStart, end_time: finalEnd, token: formData.token, session_no: parsedSessionNo,
               teacher_quota: quota 
             }).eq('id', sch.id);
           }
        } else {
           await supabase.from('schedules').update({ 
             start_time: finalStart, end_time: finalEnd, token: formData.token, session_no: parsedSessionNo,
             teacher_quota: totalTarget 
           }).eq('id', editingId);
        }
      
      } else {
        if (formData.type === 'UH' || formData.type === 'PTS') {
           const selectedTeacherId = userRole === 'guru' ? myTeacherId : formData.teacher_id;
           if (!selectedTeacherId) throw new Error("Guru pengampu wajib dipilih!");

           const { data: examData, error: exErr } = await supabase.from('exams').insert([{
              title: finalTitle, subject_id: formData.subject_id, type: formData.type, level: parseInt(formData.level),
              teacher_id: selectedTeacherId, status: initialStatus,
              duration: parseInt(formData.duration), target_question_count: totalTarget,
              token: formData.token 
           }]).select().single();
           if (exErr) throw exErr;

           await supabase.from('schedules').insert([{
              exam_id: examData.id, class_id: formData.class_id, teacher_id: selectedTeacherId, 
              start_time: finalStart, end_time: finalEnd, token: formData.token, session_no: parsedSessionNo, status: 'active',
              teacher_quota: totalTarget 
           }]);

        } else {
           const matchedAssignments = allAssignments.filter(a => parseInt(a.classes.name.split(' ')[0]) === parseInt(formData.level) && a.subject_id === formData.subject_id);
           if (matchedAssignments.length === 0) throw new Error("Tidak ada guru yang ditugaskan untuk mapel dan jenjang ini!");

           const uniqueTeachers = Array.from(new Set(matchedAssignments.map(a => a.teacher_id)));

           const teacherCountPerClass = {};
           matchedAssignments.forEach(a => {
             if (!teacherCountPerClass[a.classes.id]) teacherCountPerClass[a.classes.id] = new Set();
             teacherCountPerClass[a.classes.id].add(a.teacher_id);
           });

           let maxTeachersPerClass = 1;
           for (const classId in teacherCountPerClass) {
             if (teacherCountPerClass[classId].size > maxTeachersPerClass) {
               maxTeachersPerClass = teacherCountPerClass[classId].size;
             }
           }

           const { data: examData, error: exErr } = await supabase.from('exams').insert([{
              title: finalTitle, subject_id: formData.subject_id, type: formData.type, level: parseInt(formData.level),
              teacher_id: myTeacherId, status: initialStatus,
              duration: parseInt(formData.duration), target_question_count: totalTarget, token: formData.token 
           }]).select().single();
           if (exErr) throw exErr;

           const baseQuota = Math.floor(totalTarget / maxTeachersPerClass);
           const remainder = totalTarget % maxTeachersPerClass;

           for (let i = 0; i < uniqueTeachers.length; i++) {
             const tId = uniqueTeachers[i];
             const quota = baseQuota + (i < remainder ? 1 : 0); 
             
             await supabase.from('schedules').insert([{
                exam_id: examData.id, class_id: null, teacher_id: tId, 
                start_time: finalStart, end_time: finalEnd, token: formData.token, session_no: parsedSessionNo, status: 'active',
                teacher_quota: quota 
             }]);
           }
        }
      }
      
      Swal.fire('Berhasil!', 'Jadwal tersimpan.', 'success');
      setShowModal(false); setEditingId(null); setFormData(initialForm); fetchExams();
    } catch (error) { Swal.fire('Gagal!', error.message, 'error'); }
    finally { setLoading(false); }
  };

  const filteredAssignments = userRole === 'guru' ? allAssignments.filter(a => a.teacher_id === myTeacherId) : allAssignments;
  
  const availableLevels = Array.from(new Set(filteredAssignments.map(a => parseInt(a.classes?.name?.split(' ')[0])))).filter(Boolean).sort((a,b) => a-b);
  
  const availableClasses = Array.from(
    new Map(
      filteredAssignments
        .filter(a => parseInt(a.classes?.name?.split(' ')[0]) === parseInt(formData.level))
        .map(a => [a.classes?.id, a.classes])
    ).values()
  ).filter(Boolean).sort((a, b) => a.name.localeCompare(b.name));
    
  const availableSubjects = Array.from(new Set(filteredAssignments
    .filter(a => parseInt(a.classes?.name?.split(' ')[0]) === parseInt(formData.level))
    .map(a => a.subject_id)))
    .map(id => filteredAssignments.find(a => a.subject_id === id)?.subjects)
    .filter(Boolean)
    .sort((a, b) => a.name.localeCompare(b.name));

  const availableTeachersForClass = Array.from(
    new Map(
      allAssignments
        .filter(a => a.classes?.id === formData.class_id && a.subject_id === formData.subject_id)
        .map(a => [a.teacher_id, a.teachers])
    ).values()
  ).filter(Boolean);

  const getStatusBadge = (status) => {
    switch(status) {
      case 'pending_selection': return <span className="bg-yellow-100 text-yellow-700 px-3 py-1 rounded-full text-[9px] font-black uppercase flex items-center gap-1"><AlertCircle size={10}/> Tunggu Soal</span>;
      case 'waiting_validation': return <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full text-[9px] font-black uppercase flex items-center gap-1"><ShieldCheck size={10}/> Tunggu Verifikasi</span>;
      case 'ready': 
      case 'validated': return <span className="bg-emerald-100 text-emerald-700 px-3 py-1 rounded-full text-[9px] font-black uppercase flex items-center gap-1"><Check size={10}/> Siap Ujian</span>;
      default: return <span className="bg-slate-100 text-slate-500 px-3 py-1 rounded-full text-[9px] font-black uppercase">{status}</span>;
    }
  };

  const getFinalQuota = (ex) => {
     return (ex.teacher_quota !== undefined && ex.teacher_quota !== null) ? ex.teacher_quota : ex.exams.target_question_count;
  };

  const isMyTaskDone = (ex) => {
    if (!ex.exams || ex.exams.status !== 'pending_selection') return false;
    return ex.my_question_count >= getFinalQuota(ex);
  };

  // --- LOGIKA PENCARIAN & FILTER JADWAL ---
  const displayedExams = exams.filter(ex => {
    // Pencarian berdasarkan Judul Ujian ATAU Nama Mapel
    const searchMatch = (ex.exams?.title || '').toLowerCase().includes(searchTerm.toLowerCase()) || 
                        (ex.exams?.subjects?.name || '').toLowerCase().includes(searchTerm.toLowerCase());
    
    // Pencarian berdasarkan Hari Ini
    let dateMatch = true;
    if (dateFilter === 'Hari Ini') {
      const today = new Date();
      const p = (n) => n.toString().padStart(2, '0');
      const todayStr = `${today.getFullYear()}-${p(today.getMonth() + 1)}-${p(today.getDate())}`; // YYYY-MM-DD
      
      // ex.start_time formatnya YYYY-MM-DD HH:mm:ss
      dateMatch = ex.start_time && ex.start_time.startsWith(todayStr);
    }
    
    return searchMatch && dateMatch;
  });

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex font-sans text-left text-slate-900 dark:text-white">
      <Sidebar role={userRole} />
      <main className="flex-1 lg:ml-64 p-4 lg:p-8 mt-12 lg:mt-0">
        <header className="mb-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 text-left">
          <div>
            <h2 className="text-3xl font-black italic uppercase tracking-tighter">{userRole === 'guru' ? 'Task Ujian Saya' : 'Jadwal Ujian'}</h2>
            <p className="text-orange-600 font-bold text-[10px] uppercase tracking-[0.3em] mt-1">Lifecycle Management Ujian</p>
          </div>
          
          <div className="flex items-center gap-3 w-full md:w-auto">
            <button 
              onClick={fetchExams} 
              disabled={loading} 
              className="bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 text-slate-600 dark:text-slate-300 hover:text-orange-600 dark:hover:text-orange-500 px-4 py-3 rounded-2xl font-black shadow-sm flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50 flex-1 md:flex-none"
              title="Refresh Data"
            >
              <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
              <span className="hidden sm:inline text-xs uppercase tracking-widest">Refresh</span>
            </button>

            {userRole === 'admin' ? (
              <button onClick={() => { setEditingId(null); setFormData({...initialForm, type: 'PTS', title: ''}); generateToken(); setShowModal(true); }} className="bg-orange-600 text-white px-6 py-3 rounded-2xl font-black shadow-lg uppercase text-xs flex items-center justify-center gap-2 transition-all hover:bg-orange-700 active:scale-95 flex-1 md:flex-none">
                + BUAT JADWAL PTS / PAS
              </button>
            ) : (
              <button onClick={() => { setEditingId(null); setFormData({...initialForm, type: 'UH', title: ''}); generateToken(); setShowModal(true); }} className="bg-orange-600 text-white px-6 py-3 rounded-2xl font-black shadow-lg uppercase text-xs flex items-center justify-center gap-2 transition-all hover:bg-orange-700 active:scale-95 flex-1 md:flex-none">
                + BUAT ULANGAN HARIAN
              </button>
            )}
          </div>
        </header>

        {/* TOOLBAR PENCARIAN DAN FILTER TANGGAL */}
        <div className="bg-white dark:bg-zinc-900 p-4 rounded-3xl border border-slate-100 dark:border-zinc-800 shadow-sm mb-8 flex flex-col sm:flex-row gap-4">
            <div className="flex-1 relative">
                <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-slate-400">
                    <Search size={18} />
                </div>
                <input 
                    type="text" 
                    placeholder="Cari nama ujian atau mapel..." 
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-12 pr-4 py-3 bg-slate-50 dark:bg-zinc-950 border-none rounded-2xl outline-none focus:ring-2 focus:ring-orange-500 font-bold dark:text-white"
                />
            </div>
            
            <div className="w-full sm:w-56 relative">
                <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-slate-400">
                    <CalendarDays size={18} />
                </div>
                <select 
                    value={dateFilter}
                    onChange={(e) => setDateFilter(e.target.value)}
                    className="w-full pl-12 pr-4 py-3 bg-slate-50 dark:bg-zinc-950 border-none rounded-2xl outline-none focus:ring-2 focus:ring-orange-500 font-bold dark:text-white appearance-none cursor-pointer"
                >
                    <option value="Semua Ujian">Semua Waktu</option>
                    <option value="Hari Ini">Jadwal Hari Ini</option>
                </select>
            </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 text-left font-sans">
          {displayedExams.length === 0 ? (
             <div className="col-span-full py-16 text-center text-slate-400 font-bold italic bg-white dark:bg-zinc-900 border-2 border-dashed border-slate-200 dark:border-zinc-800 rounded-[2.5rem]">
                Tidak ada jadwal ujian yang ditemukan.
             </div>
          ) : (
             displayedExams.map((ex, idx) => (
              <div key={`${ex.id}-${idx}`} className="bg-white dark:bg-zinc-900 p-8 rounded-[2.5rem] shadow-sm border border-slate-200 dark:border-zinc-800 relative group transition-all hover:border-orange-500 overflow-hidden">
                <div className="absolute top-0 right-0 bg-orange-100 dark:bg-orange-900/30 text-orange-600 font-black text-[10px] px-4 py-2 rounded-bl-2xl z-10">
                    {ex.exams?.type || 'UH'}
                </div>

                <div className="absolute top-10 right-8 flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity z-10">
                  {(userRole === 'admin' || (userRole === 'guru' && ex.exams?.type === 'UH')) && (
                    <>
                      <button onClick={() => handleEdit(ex)} className="p-2 bg-blue-50 text-blue-600 rounded-xl hover:bg-blue-100 transition-colors"><Edit3 size={16}/></button>
                      <button onClick={async () => { const { isConfirmed } = await Swal.fire({ title: 'Hapus?', icon: 'warning', showCancelButton: true }); if(isConfirmed) { await supabase.from('schedules').delete().eq('id', ex.id); fetchExams(); } }} className="p-2 bg-red-50 text-red-500 rounded-xl hover:bg-red-100 transition-colors"><Trash2 size={16}/></button>
                    </>
                  )}
                </div>

                <div className="flex justify-between items-start mb-6 pt-2">
                  {getStatusBadge(ex.exams?.status)}
                  
                  {['PAS/PAT', 'SAJ'].includes(ex.exams?.type) && (
                    <span className="bg-slate-100 dark:bg-zinc-800 px-3 py-1 rounded-lg text-[9px] font-bold text-slate-500 uppercase italic">
                      {ex.session_no === 0 ? 'Semua Sesi' : `Sesi ${ex.session_no}`}
                    </span>
                  )}
                </div>
                
                <h3 className="text-xl font-black mb-1 uppercase italic leading-tight pr-10 truncate">{ex.exams?.title}</h3>
                
                <p className="text-orange-600 font-black text-xs mb-6 uppercase truncate" title={['UH', 'PTS'].includes(ex.exams?.type) ? ex.classes?.name : ex.cluster_classes_text}>
                  {ex.exams?.subjects?.name} | {['UH', 'PTS'].includes(ex.exams?.type) ? ex.classes?.name : ex.cluster_classes_text}
                </p>
                
                <div className="space-y-3 mb-8 text-slate-500 text-xs font-bold uppercase">
                  <div className="flex items-center gap-3"><Calendar size={14} className="text-orange-500"/> {formatWIB(ex.start_time)}</div>
                  <div className="flex items-center gap-3 font-mono"><Key size={14} className="text-orange-500"/> <span className="text-zinc-900 dark:text-white tracking-widest">{ex.token}</span></div>
                  <div className="flex items-center gap-3"><User size={14} className="text-orange-500"/> <span className="truncate">{ex.teachers?.full_name}</span></div>
                </div>

                <div className="flex flex-col gap-2 border-t border-dashed border-zinc-200 dark:border-zinc-800 pt-6">
                  
                  {/* Progress Bar (Hanya Admin untuk ujian yg belum ready) */}
                  {userRole === 'admin' && ex.exams?.status === 'pending_selection' && (
                    <div className={`w-full py-3 px-4 rounded-xl font-bold text-[10px] uppercase flex justify-between items-center mb-1 ${isMyTaskDone(ex) ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800' : 'bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800'}`}>
                      <span className="flex items-center gap-2 truncate pr-2">
                        {isMyTaskDone(ex) ? <Check size={14} className="shrink-0"/> : <AlertCircle size={14} className="shrink-0"/>}
                        Progres: {ex.teachers?.full_name?.split(' ')[0] || 'Guru'}
                      </span>
                      <span className="text-xs whitespace-nowrap shrink-0">{ex.my_question_count} / {getFinalQuota(ex)} Soal</span>
                    </div>
                  )}

                  {/* Tombol Pilih Soal (Khusus Guru) */}
                  {userRole === 'guru' && ex.exams?.status === 'pending_selection' && (
                       <button onClick={() => navigate(`/select-questions/${ex.id}`)} className="w-full bg-blue-600 hover:bg-blue-700 transition-colors text-white py-4 rounded-2xl font-black text-[10px] uppercase shadow-lg flex items-center justify-center gap-2">
                         <BookOpen size={14}/> {ex.my_question_count > 0 ? `Lanjutkan Pilih Soal (${ex.my_question_count})` : 'Pilih Soal'}
                       </button>
                  )}

                  {/* Tombol Verifikasi (Khusus Admin) */}
                  {userRole === 'admin' && ex.exams?.status === 'waiting_validation' && (
                     <button onClick={() => handleVerify(ex.exams?.id)} className="w-full bg-emerald-600 hover:bg-emerald-700 transition-colors text-white py-4 rounded-2xl font-black text-[10px] uppercase shadow-lg flex items-center justify-center gap-2">
                       <ShieldCheck size={14}/> Verifikasi Ujian
                     </button>
                  )}

                  {/* Tombol Buka Kunci Mandiri Khusus Guru */}
                  {(ex.exams?.status === 'validated' || ex.exams?.status === 'ready') && userRole === 'guru' && ex.exams?.type === 'UH' && (
                     <button onClick={() => handleUnlockUH(ex.exams?.id)} className="w-full bg-amber-500 hover:bg-amber-600 transition-colors text-white py-4 rounded-2xl font-black text-[10px] uppercase shadow-sm flex items-center justify-center gap-2 mb-1">
                       <Unlock size={14}/> Buka Kunci & Edit Soal
                     </button>
                  )}

                  <button onClick={() => navigate(`/exam-participants/${ex.id}`)} className="w-full bg-slate-900 hover:bg-slate-800 text-white dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white transition-colors py-4 rounded-2xl font-black text-[10px] uppercase shadow-sm flex items-center justify-center gap-2">
                    <Users size={16}/> INFO PESERTA
                  </button>
                  
                  <button onClick={() => navigate(`/exam-results/${ex.id}`)}className="w-full bg-slate-900 hover:bg-slate-800 text-white dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-white transition-colors py-4 rounded-2xl font-black text-[10px] uppercase shadow-sm flex items-center justify-center gap-2"title="Rekap Nilai & Analisis">
                    <FileSpreadsheet size={16} /> REKAP NILAI & ANALISIS
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {showModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto font-sans">
            <div className="bg-white dark:bg-zinc-950 w-full max-w-4xl rounded-[3rem] p-10 shadow-2xl text-left relative text-slate-900 dark:text-white font-bold border border-zinc-200 dark:border-zinc-800">
              <button onClick={() => setShowModal(false)} className="absolute top-8 right-8 p-2 text-zinc-400 hover:text-red-500 transition-colors"><X size={24}/></button>
              <h3 className="text-2xl font-black uppercase italic mb-8 border-l-8 border-orange-600 pl-4 tracking-tighter">Konfigurasi {formData.type}</h3>
              
              <form onSubmit={handleSaveSchedule} className="space-y-4">
                {userRole === 'admin' && !editingId && (
                  <div className="grid grid-cols-3 gap-3 mb-6">
                    {['PTS', 'PAS/PAT', 'SAJ'].map(t => (
                      <button key={t} type="button" onClick={() => setFormData({...formData, type: t, sub_type: '', title: '', class_id: ''})} className={`py-4 rounded-2xl font-black text-[10px] transition-all border ${formData.type === t ? 'bg-orange-600 text-white border-orange-600 shadow-lg' : 'bg-slate-50 dark:bg-zinc-900 text-slate-500 border-slate-200 dark:border-zinc-800'}`}>
                        {t}
                      </button>
                    ))}
                  </div>
                )}

                {formData.type === 'UH' && (
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Nama Ujian</label>
                    <input required className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none font-bold shadow-inner outline-none focus:ring-2 focus:ring-orange-500" placeholder="Cth: Ulangan Harian Bab 1" value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} />
                  </div>
                )}

                {(formData.type === 'PTS' || formData.type === 'PAS/PAT') && (
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Jenis Semester</label>
                    <select required className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500" value={formData.sub_type} onChange={e => setFormData({...formData, sub_type: e.target.value})}>
                      <option value="">-- Pilih Jenis/Semester --</option>
                      {formData.type === 'PTS' ? (
                        <><option value="PTS Ganjil">PTS Ganjil</option><option value="PTS Genap">PTS Genap</option></>
                      ) : (
                        <><option value="Penilaian Akhir Semester">PAS (Ganjil)</option><option value="Penilaian Akhir Tahun">PAT (Genap)</option></>
                      )}
                    </select>
                  </div>
                )}

                {!editingId && (
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Tingkat Jenjang</label>
                      <select required className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500" value={formData.level} onChange={e => setFormData({...formData, level: e.target.value, class_id: '', subject_id: '', teacher_id: ''})}>
                        <option value="">-- Pilih Jenjang --</option>
                        {availableLevels.map(l => <option key={l} value={l}>Kelas {l}</option>)}
                      </select>
                    </div>

                    {(formData.type === 'UH' || formData.type === 'PTS') && (
                      <div className="space-y-1">
                        <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Pilih Kelas</label>
                        <select required className="w-full bg-orange-50 dark:bg-orange-900/20 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500" value={formData.class_id} onChange={e => setFormData({...formData, class_id: e.target.value, teacher_id: ''})}>
                          <option value="">-- Pilih Kelas --</option>
                          {availableClasses.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                        </select>
                      </div>
                    )}

                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Mata Pelajaran</label>
                      <select required disabled={!formData.level} className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500 disabled:opacity-50" value={formData.subject_id} onChange={e => setFormData({...formData, subject_id: e.target.value, teacher_id: ''})}>
                        <option value="">-- Pilih Mapel --</option>
                        {availableSubjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                      </select>
                    </div>

                    {userRole === 'admin' && formData.type === 'PTS' && (
                      <div className="space-y-1 md:col-span-3">
                        <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Guru Pengampu</label>
                        <select required disabled={!formData.class_id || !formData.subject_id} className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500 disabled:opacity-50" value={formData.teacher_id} onChange={e => setFormData({...formData, teacher_id: e.target.value})}>
                          <option value="">-- Pilih Guru Penanggung Jawab --</option>
                          {availableTeachersForClass.map(t => <option key={t.id} value={t.id}>{t.full_name}</option>)}
                        </select>
                      </div>
                    )}
                  </div>
                )}

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Waktu Mulai Ujian</label>
                    <input type="datetime-local" required className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500" value={formData.start_time} onChange={e => setFormData({...formData, start_time: e.target.value})} />
                  </div>
                  
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Token Akses</label>
                    <div className="relative">
                      <input className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none font-black tracking-widest text-orange-600 outline-none" value={formData.token} readOnly />
                      <button type="button" onClick={generateToken} className="absolute right-4 top-4 text-zinc-400 hover:text-orange-600 transition-colors"><RefreshCw size={18}/></button>
                    </div>
                  </div>
                </div>

                <div className={`grid ${['PAS/PAT', 'SAJ'].includes(formData.type) ? 'grid-cols-3' : 'grid-cols-2'} gap-4`}>
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Durasi (Menit)</label>
                    <input type="number" required min="1" className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none shadow-inner outline-none focus:ring-2 focus:ring-orange-500" value={formData.duration} onChange={e => setFormData({...formData, duration: e.target.value})} />
                  </div>
                  
                  <div className="space-y-1">
                    <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Target Soal</label>
                    <input type="number" required min="1" className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none shadow-inner outline-none focus:ring-2 focus:ring-orange-500" value={formData.target_question_count} onChange={e => setFormData({...formData, target_question_count: e.target.value})} />
                  </div>
                  
                  {['PAS/PAT', 'SAJ'].includes(formData.type) && (
                    <div className="space-y-1">
                      <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Sesi Ujian</label>
                      <select required className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl border-none outline-none focus:ring-2 focus:ring-orange-500" value={formData.session_no} onChange={e => setFormData({...formData, session_no: e.target.value})}>
                        <option value="Semua Sesi">Semua Sesi</option>
                        <option value="1">Sesi 1</option>
                        <option value="2">Sesi 2</option>
                        <option value="3">Sesi 3</option>
                      </select>
                    </div>
                  )}
                </div>

                <div className="pt-6">
                  <button type="submit" disabled={loading} className="w-full bg-orange-600 text-white py-5 rounded-2xl font-black uppercase tracking-[0.2em] shadow-lg transition-all hover:bg-orange-700 active:scale-[0.98] disabled:opacity-50 flex justify-center items-center gap-2">
                    {loading ? 'MEMPROSES...' : 'SIMPAN JADWAL UJIAN'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Schedules;
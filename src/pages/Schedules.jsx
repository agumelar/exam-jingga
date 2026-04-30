import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { RefreshCw } from 'lucide-react';
import Swal from 'sweetalert2';
import { deleteScheduleById } from '../features/schedules/services/scheduleService';
import { useSchedulesData } from '../features/schedules/hooks/useSchedulesData';
import { useScheduleActions } from '../features/schedules/hooks/useScheduleActions';
import { formatWIB } from '../features/schedules/utils';
import { ScheduleFilters } from '../features/schedules/components/ScheduleFilters';
import { ScheduleCard } from '../features/schedules/components/ScheduleCard';
import { ScheduleFormModal } from '../features/schedules/components/ScheduleFormModal';

const Schedules = () => {
  const navigate = useNavigate();
  const [saving, setSaving] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState(null);

  const {
    loading,
    userRole,
    myTeacherId,
    allAssignments,
    exams,
    refreshSchedules,
  } = useSchedulesData({ supabase, navigate });
  
  // --- STATE UNTUK FITUR PENCARIAN & FILTER ---
  const [searchTerm, setSearchTerm] = useState('');
  const [dateFilter, setDateFilter] = useState('Semua Ujian');

  const initialForm = {
    title: '', subject_id: '', level: '', class_id: '', teacher_id: '', 
    start_time: '', duration: 60, token: '', target_question_count: 40, 
    type: 'UH', session_no: 'Semua Sesi', sub_type: '' 
  };
  const [formData, setFormData] = useState(initialForm);

  const {
    handleVerify,
    handleUnlockUH,
    handleSaveSchedule,
  } = useScheduleActions({
    supabase,
    userRole,
    myTeacherId,
    allAssignments,
    exams,
    refreshSchedules,
    setShowModal,
    setEditingId,
    setFormData,
    initialForm,
    setSaving,
  });

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

  const onVerify = async (examId) => {
    try {
      await handleVerify(examId);
    } catch (error) {
      Swal.fire('Error', error.message, 'error');
    }
  };

  const onUnlockUH = async (exam) => {
    try {
      await handleUnlockUH({
        examId: exam.exams?.id,
        examType: exam.exams?.type,
        currentStatus: exam.exams?.status,
      });
    } catch (error) {
      Swal.fire('Error', error.message, 'error');
    }
  };

  const onSaveSchedule = async (event) => {
    event.preventDefault();
    try {
      await handleSaveSchedule({ editingId, formData });
    } catch (error) {
      Swal.fire('Gagal!', error.message, 'error');
    }
  };

  const handleDelete = async (exam) => {
    const { isConfirmed } = await Swal.fire({
      title: 'Hapus?',
      icon: 'warning',
      showCancelButton: true,
    });

    if (!isConfirmed) return;
    await deleteScheduleById(supabase, exam.id);
    await refreshSchedules();
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
              onClick={refreshSchedules}
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

        <ScheduleFilters
          searchTerm={searchTerm}
          onSearchTermChange={setSearchTerm}
          dateFilter={dateFilter}
          onDateFilterChange={setDateFilter}
        />

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 text-left font-sans">
          {displayedExams.length === 0 ? (
             <div className="col-span-full py-16 text-center text-slate-400 font-bold italic bg-white dark:bg-zinc-900 border-2 border-dashed border-slate-200 dark:border-zinc-800 rounded-[2.5rem]">
                Tidak ada jadwal ujian yang ditemukan.
             </div>
          ) : (
              displayedExams.map((ex, idx) => (
                <ScheduleCard
                  key={`${ex.id}-${idx}`}
                  exam={ex}
                  userRole={userRole}
                  formatWIB={formatWIB}
                  onEdit={handleEdit}
                  onDelete={handleDelete}
                  onOpenSelectQuestions={(scheduleId) =>
                    navigate(`/select-questions/${scheduleId}`)
                  }
                  onVerify={onVerify}
                  onUnlockUH={onUnlockUH}
                  onOpenParticipants={(scheduleId) =>
                    navigate(`/exam-participants/${scheduleId}`)
                  }
                  onOpenResults={(scheduleId) =>
                    navigate(`/exam-results/${scheduleId}`)
                  }
                />
              ))
          )}
        </div>

        {showModal && (
          <ScheduleFormModal
            userRole={userRole}
            editingId={editingId}
            formData={formData}
            setFormData={setFormData}
            availableLevels={availableLevels}
            availableClasses={availableClasses}
            availableSubjects={availableSubjects}
            availableTeachersForClass={availableTeachersForClass}
            generateToken={generateToken}
            onSubmit={onSaveSchedule}
            onClose={() => setShowModal(false)}
            saving={saving}
            loading={loading}
          />
        )}
      </main>
    </div>
  );
};

export default Schedules;

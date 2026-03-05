import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { useNavigate } from 'react-router-dom';
import { 
  Activity, Users, BookOpen, Calendar, 
  AlertCircle, CheckCircle, ArrowRight, UserCheck, LayoutGrid
} from 'lucide-react';

const Dashboard = () => {
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [tasks, setTasks] = useState([]); 
  const [loading, setLoading] = useState(true);
  
  const [stats, setStats] = useState({
    students: 0,
    teachers: 0,
    questions: 0,
    activeExams: 0,
    mySchedules: 0,
    pendingTasks: 0
  });

  useEffect(() => {
    const user = localStorage.getItem('user_session');
    if (user) {
      const userData = JSON.parse(user);
      setProfile(userData);
      
      if (userData.role === 'admin' || userData.role === 'kurikulum') {
        fetchAdminStats();
      } else if (userData.role === 'guru') {
        // userData.id ini ternyata SUDAH ID Guru aslinya bro!
        fetchGuruStats(userData.id); 
      }
    } else {
      window.location.href = '/login';
    }
  }, []);

  const fetchAdminStats = async () => {
    setLoading(true);
    try {
      const [stdRes, tchRes, qstRes, exmRes] = await Promise.all([
        supabase.from('students').select('*', { count: 'exact', head: true }).eq('status', 'aktif'),
        supabase.from('teachers').select('*', { count: 'exact', head: true }).eq('role_level', 'guru'),
        supabase.from('questions').select('*', { count: 'exact', head: true }),
        supabase.from('exams').select('*', { count: 'exact', head: true }).in('status', ['ready', 'validated', 'live'])
      ]);

      setStats({
        students: stdRes.count || 0,
        teachers: tchRes.count || 0,
        questions: qstRes.count || 0,
        activeExams: exmRes.count || 0
      });
    } catch (error) {
      console.error("Gagal narik data admin:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchGuruStats = async (realTeacherId) => {
    setLoading(true);
    try {
      // 1. Hitung total soal di tabel questions (Berdasarkan schema lu: created_by = teacher_id)
      const { count: qstCount } = await supabase
        .from('questions')
        .select('*', { count: 'exact', head: true })
        .eq('created_by', realTeacherId);

      // 2. Hitung total jadwal di tabel schedules
      const { count: schCount } = await supabase
        .from('schedules')
        .select('*', { count: 'exact', head: true })
        .eq('teacher_id', realTeacherId);

      // 3. Tarik data JADWAL (Schedules) yang bener-bener punya relasi EXAM valid dengan status pending_selection
      const { data: pendingExams, error: pendingErr } = await supabase
        .from('schedules')
        .select(`
          id, 
          exams!inner (
            id,
            title,
            level,
            status,
            subjects (name)
          )
        `)
        .eq('teacher_id', realTeacherId)
        .eq('exams.status', 'pending_selection');

      if (pendingErr) throw pendingErr;

      setStats(prev => ({
        ...prev,
        questions: qstCount || 0,
        mySchedules: schCount || 0,
        pendingTasks: pendingExams?.length || 0
      }));
      setTasks(pendingExams || []);

    } catch (error) {
      console.error("Gagal narik data guru:", error);
    } finally {
      setLoading(false);
    }
  };

  if (!profile) return null;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex font-sans text-left">
      <Sidebar role={profile.role} />
      
      <main className="flex-1 lg:ml-64 p-4 lg:p-8 mt-12 lg:mt-0">
        <header className="mb-8 text-left">
          <h2 className="text-2xl lg:text-3xl font-black text-slate-800 dark:text-zinc-100 uppercase italic tracking-tighter">
             Dashboard {profile.role === 'guru' ? 'Pengampu' : 'Sistem'}
          </h2>
          <p className="text-orange-600 font-black text-xl uppercase tracking-tight">{profile.name}</p>
        </header>
  
        {/* TAMPILAN KHUSUS ADMIN / KURIKULUM */}
        {(profile.role === 'admin' || profile.role === 'kurikulum') && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
              <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm">
                <div className="bg-emerald-100 dark:bg-emerald-900/20 text-emerald-600 p-3 rounded-2xl w-fit mb-4"><Users size={24} /></div>
                <h3 className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1">Total Siswa Aktif</h3>
                <p className="text-3xl font-black dark:text-white uppercase italic">
                  {loading ? '...' : stats.students} <span className="text-sm text-slate-400 font-bold not-italic">Siswa</span>
                </p>
              </div>
              <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm">
                <div className="bg-blue-100 dark:bg-blue-900/20 text-blue-600 p-3 rounded-2xl w-fit mb-4"><UserCheck size={24} /></div>
                <h3 className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1">Total Guru</h3>
                <p className="text-3xl font-black dark:text-white uppercase italic">
                  {loading ? '...' : stats.teachers} <span className="text-sm text-slate-400 font-bold not-italic">Guru</span>
                </p>
              </div>
              <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm">
                <div className="bg-purple-100 dark:bg-purple-900/20 text-purple-600 p-3 rounded-2xl w-fit mb-4"><BookOpen size={24} /></div>
                <h3 className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1">Total Bank Soal</h3>
                <p className="text-3xl font-black dark:text-white uppercase italic">
                  {loading ? '...' : stats.questions} <span className="text-sm text-slate-400 font-bold not-italic">Soal</span>
                </p>
              </div>
              <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm">
                <div className="bg-orange-100 dark:bg-orange-900/20 text-orange-600 p-3 rounded-2xl w-fit mb-4"><Activity size={24} /></div>
                <h3 className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1">Ujian Aktif / Siap</h3>
                <p className="text-3xl font-black dark:text-white uppercase italic">
                  {loading ? '...' : stats.activeExams} <span className="text-sm text-slate-400 font-bold not-italic">Jadwal</span>
                </p>
              </div>
            </div>
            
            <div className="bg-slate-900 dark:bg-zinc-900 p-10 rounded-[3rem] text-white border border-slate-800 dark:border-zinc-800 shadow-xl relative overflow-hidden">
                <div className="absolute -right-10 -top-10 text-slate-800/50 dark:text-zinc-800/50">
                  <LayoutGrid size={200} />
                </div>
                <div className="relative z-10">
                  <h3 className="text-2xl font-black uppercase italic text-orange-500 mb-2">Pusat Kendali Ujian</h3>
                  <p className="text-slate-400 text-sm font-bold max-w-lg mb-6">
                    Aplikasi Exam Jingga siap digunakan. Seluruh data logistik, bank soal, dan jadwal ujian saling terintegrasi secara real-time.
                  </p>
                  <button onClick={() => navigate('/schedules')} className="bg-orange-600 text-white px-6 py-3 rounded-2xl font-black text-xs uppercase tracking-widest shadow-lg hover:bg-orange-700 flex items-center gap-2">
                    Pantau Jadwal Sekarang <ArrowRight size={16} />
                  </button>
                </div>
            </div>
          </div>
        )}

        {/* TAMPILAN KHUSUS GURU */}
        {profile.role === 'guru' && (
          <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            {/* STATISTIK GURU */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm flex items-center gap-4">
                <div className="bg-purple-100 dark:bg-purple-900/20 text-purple-600 p-4 rounded-2xl"><BookOpen size={28} /></div>
                <div>
                  <h3 className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1">Soal Saya</h3>
                  <p className="text-2xl font-black dark:text-white uppercase italic">{loading ? '...' : stats.questions} Soal</p>
                </div>
              </div>
              <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm flex items-center gap-4">
                <div className="bg-blue-100 dark:bg-blue-900/20 text-blue-600 p-4 rounded-2xl"><Calendar size={28} /></div>
                <div>
                  <h3 className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1">Jadwal Ujian Saya</h3>
                  <p className="text-2xl font-black dark:text-white uppercase italic">{loading ? '...' : stats.mySchedules} Jadwal</p>
                </div>
              </div>
              <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm flex items-center gap-4 border-l-4 border-l-orange-500">
                <div className="bg-orange-100 dark:bg-orange-900/20 text-orange-600 p-4 rounded-2xl"><AlertCircle size={28} /></div>
                <div>
                  <h3 className="text-slate-500 text-[10px] font-black uppercase tracking-widest mb-1">Tugas Menunggu</h3>
                  <p className="text-2xl font-black text-orange-600 uppercase italic">{loading ? '...' : stats.pendingTasks} Tugas</p>
                </div>
              </div>
            </div>

            {/* TUGAS PILIH SOAL */}
            <div className="pt-4 border-t border-dashed border-slate-200 dark:border-zinc-800">
              <div className="flex items-center gap-3 mb-6">
                <AlertCircle className="text-orange-600" size={24} />
                <h3 className="text-xl font-black dark:text-white uppercase italic tracking-tighter text-left">Tugas Pemilihan Soal</h3>
              </div>

              {loading ? (
                <div className="p-10 text-center animate-pulse text-slate-400 font-bold italic uppercase">Mengecek Tugas...</div>
              ) : tasks.length === 0 ? (
                <div className="bg-white dark:bg-zinc-900 p-12 rounded-[3rem] border-2 border-dashed border-slate-200 dark:border-zinc-800 text-center shadow-sm">
                  <CheckCircle className="mx-auto mb-4 text-emerald-500" size={48} />
                  <p className="font-bold text-slate-400 uppercase italic tracking-tight text-lg mb-2">Semua Tugas Selesai!</p>
                  <p className="text-xs text-slate-400 font-medium">Anda tidak memiliki jadwal ujian yang menunggu pemilihan soal.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {tasks.map(task => (
                    <div key={task.id} className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-orange-500/30 shadow-sm text-left relative overflow-hidden group hover:border-orange-500 transition-colors">
                      <div className="absolute -right-4 -top-4 text-orange-500/10 group-hover:scale-110 transition-transform">
                        <BookOpen size={100} />
                      </div>
                      <div className="relative z-10">
                        <h4 className="text-lg font-black dark:text-white uppercase italic mb-1 truncate pr-4">{task.exams?.title}</h4>
                        <p className="text-orange-600 font-black text-[10px] uppercase mb-6 tracking-widest">{task.exams?.subjects?.name} | KELAS {task.exams?.level}</p>
                        <button 
                          onClick={() => navigate(`/select-questions/${task.id}`)}
                          className="w-full bg-slate-900 dark:bg-white dark:text-black text-white py-4 rounded-2xl font-black uppercase text-[10px] tracking-widest flex items-center justify-center gap-2 hover:opacity-90 transition-opacity shadow-lg"
                        >
                          Pilih Soal Sekarang <ArrowRight size={16}/>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default Dashboard;
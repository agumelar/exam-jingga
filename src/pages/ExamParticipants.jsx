import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { Users, ArrowLeft, LayoutGrid, UserCheck, ShieldAlert, Clock, RefreshCw, Unlock, AlertTriangle, CheckCircle2, Search, Filter } from 'lucide-react';
import Swal from 'sweetalert2';

const ExamParticipants = () => {
  const { examId } = useParams();
  const navigate = useNavigate();
  const [exam, setExam] = useState(null);
  const [schedule, setSchedule] = useState(null);
  const [participants, setParticipants] = useState([]);
  const [sessions, setSessions] = useState({}); 
  const [logisticsMap, setLogisticsMap] = useState({});
  const [rooms, setRooms] = useState([]);
  
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRoom, setSelectedRoom] = useState('');

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [userRole, setUserRole] = useState('');

  useEffect(() => {
    fetchInitialData();
  }, [examId]);

  const fetchInitialData = async () => {
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

      if (schErr || !schData) throw new Error("Jadwal tidak ditemukan");
      
      setSchedule(schData);
      setExam(schData.exams);

      // JEMBATAN LOGIKA GURU (Strict Class Filter)
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
        // Kalau UH, khusus kelas itu aja
        studentQuery = studentQuery.eq('class_id', schData.class_id);
      } else {
        // Kalau PAS/PTS, filter sesuai kelas yang diampu guru
        const { data: allClassIds } = await supabase.from('classes').select('id').like('name', `${schData.exams.level}%`);
        let ids = allClassIds?.map(c => c.id) || [];
        
        if (role === 'guru' && allowedClassIds) {
           ids = ids.filter(id => allowedClassIds.includes(id));
        }

        if (ids.length === 0) {
           setParticipants([]); // Guru ini tidak ngajar mapel ini di level ini
           setLoading(false);
           return; 
        }
        studentQuery = studentQuery.in('class_id', ids);
      }

      const { data: students, error: stdErr } = await studentQuery.eq('status', 'aktif').order('full_name');
      if (stdErr) throw stdErr;
      
      setParticipants(students || []);

      const studentIds = students?.map(s => s.id) || [];
      if (studentIds.length > 0) {
        const { data: logData } = await supabase
          .from('student_logistics')
          .select('student_id, room_name')
          .in('student_id', studentIds);
        
        const lMap = {};
        const uniqueRooms = new Set();
        logData?.forEach(l => { 
          lMap[l.student_id] = l; 
          if(l.room_name) uniqueRooms.add(l.room_name);
        });
        setLogisticsMap(lMap);
        setRooms([...uniqueRooms].sort());
      }

      await fetchLiveSessions();

    } catch (error) {
      console.error(error);
      Swal.fire('Error', error.message, 'error');
      navigate('/schedules');
    } finally {
      setLoading(false);
    }
  };

  const fetchLiveSessions = async () => {
    setRefreshing(true);
    try {
      const { data: sessionData, error: sErr } = await supabase
        .from('exam_sessions')
        .select('*')
        .eq('schedule_id', examId)
        .order('started_at', { ascending: false }); 
      
      if (sErr) throw sErr;

      const sessionMap = {};
      sessionData?.forEach(s => { 
        if (!sessionMap[s.student_id]) {
          sessionMap[s.student_id] = s;
        } else {
          const currentBest = sessionMap[s.student_id];
          if (s.status === 'finished' && currentBest.status !== 'finished') {
            sessionMap[s.student_id] = s;
          } else if (s.status === 'locked' && currentBest.status === 'active') {
            sessionMap[s.student_id] = s;
          }
        }
      });
      
      setSessions(sessionMap);
    } catch (err) {
      console.error("Gagal refresh sesi:", err);
      Swal.fire('Error Load Sesi', err.message, 'error');
    } finally {
      setRefreshing(false);
    }
  };

  const handleUnlock = async (sessionId, studentName) => {
    const { isConfirmed } = await Swal.fire({
      title: 'Buka Kunci Siswa?',
      text: `Sesi ujian atas nama ${studentName} akan dibuka kembali dan peringatan di-reset.`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#10b981',
      cancelButtonColor: '#d33',
      confirmButtonText: 'Ya, Buka Kunci!'
    });

    if (isConfirmed) {
      try {
        await supabase
          .from('exam_sessions')
          .update({ status: 'active', violation_count: 0 })
          .eq('id', sessionId);
        
        Swal.fire('Berhasil!', 'Sesi berhasil dibuka. Siswa bisa lanjut ujian.', 'success');
        fetchLiveSessions(); 
      } catch (error) {
        Swal.fire('Error', 'Gagal membuka kunci.', 'error');
      }
    }
  };

  const getStatusUI = (session) => {
    if (!session) return { label: 'Belum Mulai', color: 'bg-slate-100 text-slate-500 dark:bg-zinc-800', icon: <Clock size={12}/> };
    switch (session.status) {
      case 'active': return { label: 'Mengerjakan', color: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30', icon: <RefreshCw size={12} className="animate-spin"/> };
      case 'locked': return { label: 'Terkunci', color: 'bg-red-100 text-red-600 dark:bg-red-900/30', icon: <AlertTriangle size={12}/> };
      case 'finished': return { label: 'Selesai', color: 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30', icon: <CheckCircle2 size={12}/> };
      default: return { label: session.status, color: 'bg-slate-100 text-slate-500', icon: null };
    }
  };

  const filteredParticipants = participants.filter(p => {
    const matchSearch = p.full_name.toLowerCase().includes(searchTerm.toLowerCase()) || 
                        p.nis.toLowerCase().includes(searchTerm.toLowerCase());
    const matchRoom = selectedRoom ? logisticsMap[p.id]?.room_name === selectedRoom : true;
    return matchSearch && matchRoom;
  });

  if (loading) return <div className="min-h-screen flex items-center justify-center dark:bg-zinc-950 text-orange-600 font-black animate-pulse uppercase italic">Memuat Data Peserta...</div>;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex font-sans text-left">
      <Sidebar role={userRole} />
      <main className="flex-1 lg:ml-64 p-4 lg:p-8 mt-12 lg:mt-0">
        <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b dark:border-zinc-800 pb-6">
          <div className="flex items-center gap-4 text-left">
            <button onClick={() => navigate('/schedules')} className="p-3 bg-white dark:bg-zinc-900 rounded-2xl shadow-sm hover:text-orange-600 transition-all dark:text-white"><ArrowLeft size={20}/></button>
            <div>
              <h2 className="text-2xl font-black text-slate-800 dark:text-zinc-100 uppercase italic tracking-tighter">{exam?.title}</h2>
              <p className="text-orange-600 font-black text-xs uppercase">{exam?.subjects?.name} | {exam?.type === 'UH' ? 'ULANGAN HARIAN' : `JENJANG ${exam?.level}`}</p>
            </div>
          </div>
          
          <button 
            onClick={fetchLiveSessions} 
            disabled={refreshing}
            className="flex items-center gap-2 bg-slate-900 dark:bg-white dark:text-zinc-900 text-white px-6 py-3 rounded-2xl font-black text-xs uppercase tracking-widest hover:scale-105 transition-all shadow-lg disabled:opacity-50"
          >
            <RefreshCw size={16} className={refreshing ? 'animate-spin' : ''} /> 
            {refreshing ? 'Memperbarui...' : 'Refresh Live Data'}
          </button>
        </header>

        {/* INFO RINGKAS */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-8 text-left">
          <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm flex items-center gap-4">
             <div className="p-3 bg-orange-100 dark:bg-orange-900/30 text-orange-600 rounded-2xl"><Users size={24} /></div>
             <div>
               <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Total Peserta</p>
               <p className="text-2xl font-black dark:text-white">{participants.length} Siswa</p>
             </div>
          </div>
          <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm flex items-center gap-4">
             <div className="p-3 bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 rounded-2xl"><ShieldAlert size={24} /></div>
             <div>
               <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Tipe Pelaksanaan</p>
               <p className="text-2xl font-black text-emerald-500 uppercase italic">{exam?.type}</p>
             </div>
          </div>
          <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm flex items-center gap-4">
             <div className="p-3 bg-purple-100 dark:bg-purple-900/30 text-purple-600 rounded-2xl"><Clock size={24} /></div>
             <div>
               <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Durasi Waktu</p>
               <p className="text-2xl font-black text-purple-600 uppercase italic">{exam?.duration} Menit</p>
             </div>
          </div>
          <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-slate-100 dark:border-zinc-800 shadow-sm flex items-center gap-4">
             <div className="p-3 bg-blue-100 dark:bg-blue-900/30 text-blue-600 rounded-2xl"><LayoutGrid size={24} /></div>
             <div>
               <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">Token Aktif</p>
               <p className="text-2xl font-black text-orange-600 tracking-widest uppercase font-mono">{schedule?.token}</p>
             </div>
          </div>
        </div>

        <div className="bg-white dark:bg-zinc-900 p-4 rounded-3xl border border-slate-100 dark:border-zinc-800 shadow-sm mb-6 flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
                <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-slate-400">
                    <Search size={18} />
                </div>
                <input 
                    type="text" 
                    placeholder="Cari nama atau NIS siswa..." 
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-12 pr-4 py-3 bg-slate-50 dark:bg-zinc-950 border-none rounded-2xl outline-none focus:ring-2 focus:ring-orange-500 font-bold dark:text-white"
                />
            </div>
            
            <div className="w-full md:w-64 relative">
                <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-slate-400">
                    <Filter size={18} />
                </div>
                <select 
                    value={selectedRoom}
                    onChange={(e) => setSelectedRoom(e.target.value)}
                    className="w-full pl-12 pr-4 py-3 bg-slate-50 dark:bg-zinc-950 border-none rounded-2xl outline-none focus:ring-2 focus:ring-orange-500 font-bold dark:text-white appearance-none"
                >
                    <option value="">Semua Ruangan</option>
                    {rooms.map(r => (
                        <option key={r} value={r}>Ruang {r}</option>
                    ))}
                </select>
            </div>
        </div>

        {/* DAFTAR PESERTA */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {filteredParticipants.length === 0 ? (
            <div className="col-span-full py-20 text-center bg-white dark:bg-zinc-900 rounded-[3rem] border-2 border-dashed border-slate-200 dark:border-zinc-800">
              <p className="font-bold text-slate-400 italic">Peserta tidak ditemukan di kelas Anda bro.</p>
            </div>
          ) : (
            filteredParticipants.map((p, idx) => {
              const session = sessions[p.id];
              const statusUI = getStatusUI(session);

              return (
                <div key={p.id} className={`bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border-2 transition-all shadow-sm text-left flex flex-col justify-between ${session?.status === 'locked' ? 'border-red-500 shadow-red-500/10' : 'border-slate-100 dark:border-zinc-800 hover:border-orange-500'}`}>
                  
                  <div>
                    <div className="flex justify-between items-start mb-4 border-b border-dashed border-slate-100 dark:border-zinc-800 pb-4">
                      <div className={`px-3 py-1.5 rounded-full text-[10px] font-black uppercase flex items-center gap-2 ${statusUI.color}`}>
                        {statusUI.icon} {statusUI.label}
                      </div>
                      <span className="text-[10px] bg-slate-100 dark:bg-zinc-800 px-2 py-1 rounded-lg font-bold text-slate-400"># {idx + 1}</span>
                    </div>

                    <div className="space-y-4 mb-6">
                      <div>
                          <p className="text-[8px] font-black text-slate-400 uppercase tracking-widest">Nama Peserta</p>
                          <p className="text-sm font-black dark:text-white uppercase truncate">{p.full_name}</p>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                          <div className="bg-slate-50 dark:bg-zinc-800/50 p-3 rounded-xl">
                              <p className="text-[8px] font-black text-slate-400 uppercase">Username (NIS)</p>
                              <p className="text-xs font-bold dark:text-white font-mono mt-1">{p.nis}</p>
                          </div>
                          <div className="bg-slate-50 dark:bg-zinc-800/50 p-3 rounded-xl">
                              <p className="text-[8px] font-black text-slate-400 uppercase">Kelas / Ruang</p>
                              <p className="text-xs font-bold dark:text-white uppercase mt-1">
                                {p.classes?.name} {logisticsMap[p.id]?.room_name ? `• R.${logisticsMap[p.id].room_name}` : ''}
                              </p>
                          </div>
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-slate-100 dark:border-zinc-800">
                    {session?.status === 'locked' && (
                      <>
                        {(userRole === 'admin' || userRole === 'kurikulum') ? (
                          <button 
                            onClick={() => handleUnlock(session.id, p.full_name)}
                            className="w-full bg-red-100 hover:bg-red-600 text-red-600 hover:text-white dark:bg-red-900/30 dark:hover:bg-red-600 transition-colors py-3 rounded-xl font-black text-[10px] uppercase flex items-center justify-center gap-2"
                          >
                            <Unlock size={14}/> Buka Kunci Sesi
                          </button>
                        ) : (
                          <p className="text-[10px] font-bold text-red-500 italic text-center uppercase p-2 bg-red-50 dark:bg-red-900/20 rounded-xl">
                            <AlertTriangle size={12} className="inline mr-1" /> Terkunci (Hubungi Admin)
                          </p>
                        )}
                      </>
                    )}

                    {session?.status === 'active' && session?.violation_count > 0 && (
                      <p className="text-xs font-bold text-orange-500 flex items-center gap-1"><AlertTriangle size={14}/> {session.violation_count}x Peringatan Pelanggaran</p>
                    )}

                    {session?.status === 'finished' && (
                       <div className="flex items-center justify-between mt-4 bg-emerald-50 dark:bg-emerald-900/10 p-3 rounded-xl border border-emerald-100 dark:border-emerald-800/30">
                         <span className="text-xs font-black text-emerald-600 flex items-center gap-1"><CheckCircle2 size={14}/> SELESAI</span>
                         <div className="text-emerald-700 dark:text-emerald-400 font-black text-sm flex items-center gap-2">
                           SKOR: <span className="text-2xl bg-emerald-500 text-white px-3 py-1 rounded-lg shadow-sm">{session.score ?? 0}</span>
                         </div>
                       </div>
                    )}

                    {!session && (
                      <p className="text-[10px] font-bold text-slate-400 italic text-center">Menunggu siswa login...</p>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </main>
    </div>
  );
};

export default ExamParticipants;
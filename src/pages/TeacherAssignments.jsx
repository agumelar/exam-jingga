import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { UserPlus, Trash2, CheckCircle2, UserCheck, BookOpen, School } from 'lucide-react';
import Swal from 'sweetalert2';

const TeacherAssignments = () => {
  const [teachers, setTeachers] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [classes, setClasses] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);

  const [selectedTeacher, setSelectedTeacher] = useState('');
  const [selectedSubject, setSelectedSubject] = useState('');
  const [selectedClasses, setSelectedClasses] = useState([]); // Bisa banyak kelas sekaligus

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    const [t, s, c, a] = await Promise.all([
      supabase.from('teachers').select('*').order('full_name'),
      supabase.from('subjects').select('*').order('name'),
      supabase.from('classes').select('*').order('name'),
      supabase.from('teacher_assignments').select(`
        id,
        teachers(full_name),
        subjects(name),
        classes(name)
      `)
    ]);
    setTeachers(t.data || []);
    setSubjects(s.data || []);
    setClasses(c.data || []);
    setAssignments(a.data || []);
    setLoading(false);
  };

  const handleToggleClass = (classId) => {
    setSelectedClasses(prev => 
      prev.includes(classId) ? prev.filter(id => id !== classId) : [...prev, classId]
    );
  };

  const handleSave = async () => {
    if (!selectedTeacher || !selectedSubject || selectedClasses.length === 0) {
      return Swal.fire('Oops!', 'Pilih Guru, Mapel, dan minimal satu Kelas!', 'warning');
    }

    const newAssignments = selectedClasses.map(classId => ({
      teacher_id: selectedTeacher,
      subject_id: selectedSubject,
      class_id: classId
    }));

    const { error } = await supabase.from('teacher_assignments').insert(newAssignments);

    if (!error) {
      Swal.fire('Berhasil!', 'Penugasan guru telah disimpan.', 'success');
      setSelectedClasses([]);
      fetchInitialData();
    } else {
      Swal.fire('Error!', error.message, 'error');
    }
  };

  const handleDelete = async (id) => {
    const { isConfirmed } = await Swal.fire({
      title: 'Hapus Penugasan?',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#ea580c'
    });
    if (isConfirmed) {
      await supabase.from('teacher_assignments').delete().eq('id', id);
      fetchInitialData();
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex transition-colors duration-300 font-sans text-left">
      <Sidebar role="admin" />
      <main className="flex-1 lg:ml-64 p-4 lg:p-8 text-left">
        <header className="mb-8 text-left">
          <h2 className="text-3xl font-black text-slate-800 dark:text-zinc-100 flex items-center gap-3 italic tracking-tighter uppercase">
            <UserPlus className="text-orange-600" size={32} /> Penugasan Pengampu
          </h2>
          <p className="text-slate-500 dark:text-zinc-400 font-medium">Atur guru yang mengampu mata pelajaran di tiap kelas</p>
        </header>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          {/* FORM INPUT */}
          <div className="bg-white dark:bg-zinc-900 p-8 rounded-[2.5rem] shadow-sm border border-slate-100 dark:border-zinc-800 h-fit">
            <div className="space-y-6">
              <div>
                <label className="text-[10px] font-black uppercase text-slate-400 mb-2 block flex items-center gap-2">
                  <UserCheck size={14}/> Pilih Guru
                </label>
                <select 
                  className="w-full bg-slate-50 dark:bg-zinc-800 p-4 rounded-2xl dark:text-white outline-none focus:ring-2 focus:ring-orange-500 border-none appearance-none cursor-pointer"
                  value={selectedTeacher} onChange={(e) => setSelectedTeacher(e.target.value)}
                >
                  <option value="">-- Pilih Guru --</option>
                  {teachers.map(t => <option key={t.id} value={t.id}>{t.full_name}</option>)}
                </select>
              </div>

              <div>
                <label className="text-[10px] font-black uppercase text-slate-400 mb-2 block flex items-center gap-2">
                  <BookOpen size={14}/> Pilih Mata Pelajaran
                </label>
                <select 
                  className="w-full bg-slate-50 dark:bg-zinc-800 p-4 rounded-2xl dark:text-white outline-none focus:ring-2 focus:ring-orange-500 border-none appearance-none cursor-pointer"
                  value={selectedSubject} onChange={(e) => setSelectedSubject(e.target.value)}
                >
                  <option value="">-- Pilih Mapel --</option>
                  {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>

              <div>
                <label className="text-[10px] font-black uppercase text-slate-400 mb-2 block flex items-center gap-2">
                  <School size={14}/> Pilih Kelas (Bisa pilih banyak)
                </label>
                <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto p-2">
                  {classes.map(c => (
                    <button
                      key={c.id}
                      onClick={() => handleToggleClass(c.id)}
                      className={`p-3 rounded-xl text-xs font-bold transition-all ${
                        selectedClasses.includes(c.id) 
                        ? 'bg-orange-600 text-white' 
                        : 'bg-slate-100 dark:bg-zinc-800 text-slate-500'
                      }`}
                    >
                      {c.name}
                    </button>
                  ))}
                </div>
              </div>

              <button 
                onClick={handleSave}
                className="w-full bg-orange-600 text-white py-5 rounded-2xl font-black shadow-lg hover:bg-orange-700 transition-all active:scale-95 uppercase"
              >
                Simpan Penugasan
              </button>
            </div>
          </div>

          {/* TABLE LIST */}
          <div className="xl:col-span-2 space-y-4">
            <h3 className="font-black dark:text-white uppercase tracking-tighter">Daftar Pengampu Saat Ini</h3>
            <div className="bg-white dark:bg-zinc-900 rounded-[2.5rem] border border-slate-100 dark:border-zinc-800 overflow-hidden shadow-sm">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-50 dark:bg-zinc-800/50">
                    <th className="p-5 text-[10px] font-black uppercase text-slate-400">Guru</th>
                    <th className="p-5 text-[10px] font-black uppercase text-slate-400">Mapel</th>
                    <th className="p-5 text-[10px] font-black uppercase text-slate-400">Kelas</th>
                    <th className="p-5 text-[10px] font-black uppercase text-slate-400 text-center">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-zinc-800">
                  {assignments.map((a) => (
                    <tr key={a.id} className="hover:bg-slate-50/50 dark:hover:bg-zinc-800/30 transition-colors">
                      <td className="p-5 text-sm font-black dark:text-white uppercase tracking-tighter">{a.teachers?.full_name}</td>
                      <td className="p-5 text-sm font-bold text-orange-600 uppercase">{a.subjects?.name}</td>
                      <td className="p-5">
                        <span className="bg-slate-100 dark:bg-zinc-800 px-3 py-1 rounded-lg text-[10px] font-black uppercase">{a.classes?.name}</span>
                      </td>
                      <td className="p-5 text-center">
                        <button onClick={() => handleDelete(a.id)} className="text-slate-300 hover:text-red-500 transition-colors">
                          <Trash2 size={18} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default TeacherAssignments;
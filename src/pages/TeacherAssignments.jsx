import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { UserPlus, Trash2, UserCheck, BookOpen, School, Search, Filter, Edit3, X } from 'lucide-react';
import Swal from 'sweetalert2';

const TeacherAssignments = () => {
  const [teachers, setTeachers] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [classes, setClasses] = useState([]);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);

  // State untuk form
  const [selectedTeacher, setSelectedTeacher] = useState('');
  const [selectedSubject, setSelectedSubject] = useState('');
  const [selectedClasses, setSelectedClasses] = useState([]); 
  const [editingId, setEditingId] = useState(null);

  // State untuk search & filter
  const [searchQuery, setSearchQuery] = useState('');
  const [filterSubject, setFilterSubject] = useState('');

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    // PERBAIKAN: Ambil id untuk foreign key agar bisa dipakai saat mode edit
    const [t, s, c, a] = await Promise.all([
      supabase.from('teachers').select('*').order('full_name'),
      supabase.from('subjects').select('*').order('name'),
      supabase.from('classes').select('*').order('name'),
      supabase.from('teacher_assignments').select(`
        id,
        teacher_id,
        subject_id,
        class_id,
        teachers(id, full_name),
        subjects(id, name),
        classes(id, name)
      `)
    ]);
    setTeachers(t.data || []);
    setSubjects(s.data || []);
    setClasses(c.data || []);
    setAssignments(a.data || []);
    setLoading(false);
  };

  const handleToggleClass = (classId) => {
    // Jika sedang mode edit, batasi hanya 1 kelas saja yang bisa dipilih (karena ngedit spesifik 1 baris)
    if (editingId) {
      setSelectedClasses([classId]);
    } else {
      setSelectedClasses(prev => 
        prev.includes(classId) ? prev.filter(id => id !== classId) : [...prev, classId]
      );
    }
  };

  const handleEdit = (assignment) => {
    setEditingId(assignment.id);
    setSelectedTeacher(assignment.teacher_id);
    setSelectedSubject(assignment.subject_id);
    setSelectedClasses([assignment.class_id]);
    window.scrollTo({ top: 0, behavior: 'smooth' }); // Scroll ke atas biar form kelihatan
  };

  const cancelEdit = () => {
    setEditingId(null);
    setSelectedTeacher('');
    setSelectedSubject('');
    setSelectedClasses([]);
  };

  const handleSave = async () => {
    if (!selectedTeacher || !selectedSubject || selectedClasses.length === 0) {
      return Swal.fire('Oops!', 'Pilih Guru, Mapel, dan minimal satu Kelas!', 'warning');
    }

    if (editingId) {
      // MODE EDIT (Update 1 baris)
      const { error } = await supabase
        .from('teacher_assignments')
        .update({
          teacher_id: selectedTeacher,
          subject_id: selectedSubject,
          class_id: selectedClasses[0] // Ambil index 0 karena mode edit cuma boleh pilih 1 kelas
        })
        .eq('id', editingId);

      if (!error) {
        Swal.fire('Berhasil!', 'Penugasan berhasil diperbarui.', 'success');
        cancelEdit();
        fetchInitialData();
      } else {
        Swal.fire('Error!', error.message, 'error');
      }
    } else {
      // MODE TAMBAH BARU (Insert banyak baris sekaligus)
      const newAssignments = selectedClasses.map(classId => ({
        teacher_id: selectedTeacher,
        subject_id: selectedSubject,
        class_id: classId
      }));

      const { error } = await supabase.from('teacher_assignments').insert(newAssignments);

      if (!error) {
        Swal.fire('Berhasil!', 'Penugasan guru telah disimpan.', 'success');
        cancelEdit(); // Reset form
        fetchInitialData();
      } else {
        Swal.fire('Error!', error.message, 'error');
      }
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
      // Jika yang dihapus sedang diedit, reset formnya
      if (editingId === id) cancelEdit(); 
      fetchInitialData();
    }
  };

  // LOGIKA FILTER: Menyaring data tabel berdasarkan search nama & dropdown mapel
  const filteredAssignments = assignments.filter((a) => {
    const matchName = a.teachers?.full_name?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchSubject = filterSubject ? a.subject_id === filterSubject : true;
    return matchName && matchSubject;
  });

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
          <div className={`p-8 rounded-[2.5rem] shadow-sm border h-fit transition-all ${editingId ? 'bg-blue-50/50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800' : 'bg-white dark:bg-zinc-900 border-slate-100 dark:border-zinc-800'}`}>
            <div className="space-y-6">
              {editingId && (
                <div className="bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-400 px-4 py-3 rounded-2xl flex justify-between items-center text-xs font-bold uppercase tracking-widest">
                  <span>Mode Edit Aktif</span>
                  <button onClick={cancelEdit} className="hover:text-red-500 transition-colors"><X size={16}/></button>
                </div>
              )}

              <div>
                <label className="text-[10px] font-black uppercase text-slate-400 mb-2 flex items-center gap-2">
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
                <label className="text-[10px] font-black uppercase text-slate-400 mb-2 flex items-center gap-2">
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
                <label className="text-[10px] font-black uppercase text-slate-400 mb-2 flex items-center gap-2">
                  <School size={14}/> {editingId ? 'Pilih Kelas (1 Kelas Saja)' : 'Pilih Kelas (Bisa pilih banyak)'}
                </label>
                <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto p-2">
                  {classes.map(c => (
                    <button
                      key={c.id}
                      onClick={() => handleToggleClass(c.id)}
                      className={`p-3 rounded-xl text-xs font-bold transition-all ${
                        selectedClasses.includes(c.id) 
                        ? 'bg-orange-600 text-white' 
                        : 'bg-slate-100 dark:bg-zinc-800 text-slate-500 hover:bg-slate-200 dark:hover:bg-zinc-700'
                      }`}
                    >
                      {c.name}
                    </button>
                  ))}
                </div>
              </div>

              <div className="flex gap-2">
                {editingId && (
                  <button 
                    onClick={cancelEdit}
                    className="flex-1 bg-slate-200 text-slate-700 dark:bg-zinc-800 dark:text-zinc-300 py-5 rounded-2xl font-black shadow-sm hover:bg-slate-300 dark:hover:bg-zinc-700 transition-all active:scale-95 uppercase text-xs"
                  >
                    Batal
                  </button>
                )}
                <button 
                  onClick={handleSave}
                  className={`flex-[2] text-white py-5 rounded-2xl font-black shadow-lg transition-all active:scale-95 uppercase text-xs ${editingId ? 'bg-blue-600 hover:bg-blue-700' : 'bg-orange-600 hover:bg-orange-700'}`}
                >
                  {editingId ? 'Update Penugasan' : 'Simpan Penugasan'}
                </button>
              </div>
            </div>
          </div>

          {/* TABLE LIST & FILTER BAR */}
          <div className="xl:col-span-2 space-y-4">
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-2">
              <h3 className="font-black dark:text-white uppercase tracking-tighter">Daftar Pengampu</h3>
              
              {/* FITUR BARU: SEARCH & FILTER */}
              <div className="flex flex-col sm:flex-row w-full md:w-auto gap-2">
                <div className="relative flex-1 sm:w-64">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Search size={16} />
                  </div>
                  <input
                    type="text"
                    placeholder="Cari nama guru..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 text-sm rounded-2xl pl-10 pr-4 py-3 outline-none focus:border-orange-500 dark:text-white shadow-sm"
                  />
                </div>
                
                <div className="relative flex-1 sm:w-48">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <Filter size={16} />
                  </div>
                  <select
                    value={filterSubject}
                    onChange={(e) => setFilterSubject(e.target.value)}
                    className="w-full bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 text-sm rounded-2xl pl-10 pr-4 py-3 outline-none focus:border-orange-500 dark:text-white shadow-sm appearance-none cursor-pointer"
                  >
                    <option value="">Semua Mapel</option>
                    {subjects.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </div>
              </div>
            </div>

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
                  {filteredAssignments.length > 0 ? (
                    filteredAssignments.map((a) => (
                      <tr key={a.id} className="hover:bg-slate-50/50 dark:hover:bg-zinc-800/30 transition-colors">
                        <td className="p-5 text-sm font-black dark:text-white uppercase tracking-tighter">{a.teachers?.full_name}</td>
                        <td className="p-5 text-sm font-bold text-orange-600 uppercase">{a.subjects?.name}</td>
                        <td className="p-5">
                          <span className="bg-slate-100 dark:bg-zinc-800 px-3 py-1 rounded-lg text-[10px] font-black uppercase">{a.classes?.name}</span>
                        </td>
                        <td className="p-5 text-center">
                          <div className="flex justify-center items-center gap-3">
                            {/* TOMBOL EDIT BARU */}
                            <button onClick={() => handleEdit(a)} className="text-slate-300 hover:text-blue-500 transition-colors" title="Edit Data">
                              <Edit3 size={18} />
                            </button>
                            <button onClick={() => handleDelete(a.id)} className="text-slate-300 hover:text-red-500 transition-colors" title="Hapus Data">
                              <Trash2 size={18} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="4" className="p-8 text-center text-slate-400 text-sm font-bold italic">
                        Tidak ada data penugasan ditemukan.
                      </td>
                    </tr>
                  )}
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
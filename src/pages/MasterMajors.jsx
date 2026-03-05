import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { GraduationCap, Trash2, Plus, LayoutGrid, List } from 'lucide-react';
import Swal from 'sweetalert2';

const MasterMajors = () => {
  const [majors, setMajors] = useState([]);
  const [newMajor, setNewMajor] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMajors();
  }, []);

  const fetchMajors = async () => {
    setLoading(true);
    const { data, error } = await supabase.from('majors').select('*').order('name');
    if (!error) setMajors(data);
    setLoading(false);
  };

  const handleAddMajor = async (e) => {
    e.preventDefault();
    if (!newMajor) return;
    const { error } = await supabase.from('majors').insert([{ name: newMajor }]);
    if (!error) {
      setNewMajor('');
      fetchMajors();
      Swal.fire({ icon: 'success', title: 'Berhasil!', background: document.documentElement.classList.contains('dark') ? '#18181b' : '#fff', color: '#ea580c' });
    }
  };

  const handleDeleteMajor = async (id) => {
    const result = await Swal.fire({
      title: 'Hapus Jurusan?',
      text: "Hati-hati bro, kalau dihapus, kelas dan siswa yang ada di jurusan ini bisa ikut terhapus (Cascade)!",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#ea580c',
      cancelButtonColor: '#64748b',
      confirmButtonText: 'Ya, Hapus Saja!',
      background: document.documentElement.classList.contains('dark') ? '#18181b' : '#fff',
      color: document.documentElement.classList.contains('dark') ? '#fff' : '#000'
    });
  
    if (result.isConfirmed) {
      const { error } = await supabase.from('majors').delete().eq('id', id);
      if (error) {
        Swal.fire('Gagal!', error.message, 'error');
      } else {
        Swal.fire('Terhapus!', 'Jurusan berhasil dibuang.', 'success');
        fetchMajors(); // Refresh daftar jurusannya
      }
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex transition-colors duration-300 text-slate-900 dark:text-zinc-100">
      <Sidebar role="admin" />
      
      <main className="flex-1 lg:ml-64 p-4 lg:p-8">
        <header className="mb-8">
          <h2 className="text-3xl font-bold flex items-center gap-3">
            <GraduationCap className="text-orange-600" size={32} /> Master Jurusan
          </h2>
          <p className="text-slate-500 dark:text-zinc-400">Kelola Jurusan di SMKN 1 Rongga</p>
        </header>

        {/* Input Card */}
        <div className="bg-white dark:bg-zinc-900 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-zinc-800 mb-8">
          <form onSubmit={handleAddMajor} className="flex flex-col md:flex-row gap-4">
            <input 
              type="text" 
              value={newMajor}
              onChange={(e) => setNewMajor(e.target.value)}
              placeholder="Input Jurusan Baru (Contoh: RPL)"
              className="flex-1 bg-slate-50 dark:bg-zinc-800 border border-slate-200 dark:border-zinc-700 p-3 rounded-xl outline-none focus:ring-2 focus:ring-orange-500 transition-all"
            />
            <button className="bg-orange-600 hover:bg-orange-700 text-white px-8 py-3 rounded-xl font-bold flex items-center justify-center gap-2 transition-all">
              <Plus size={20} /> Tambah Jurusan
            </button>
          </form>
        </div>

        {/* Grid Jurusan */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {loading ? (
            <p>Sabar bro, lagi narik data...</p>
          ) : (
            majors.map((m) => (
              <div key={m.id} className="group bg-white dark:bg-zinc-900 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-zinc-800 hover:border-orange-500 dark:hover:border-orange-500 transition-all relative overflow-hidden">
                <div className="absolute -right-4 -top-4 text-orange-600 opacity-10 group-hover:opacity-20 transition-opacity">
                  <GraduationCap size={100} />
                </div>
                <h3 className="text-xl font-bold mb-1">{m.name}</h3>
                <p className="text-sm text-slate-500 dark:text-zinc-400 mb-4 text-orange-600 font-medium">SMKN 1 Rongga</p>
                <div className="flex justify-between items-center relative z-10">
                   <span className="text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-600 px-3 py-1 rounded-full uppercase font-bold tracking-wider">Aktif</span>
                   <button 
                    onClick={() => handleDeleteMajor(m.id)} // <--- Tambahkan onClick ini bro!
                    className="text-slate-400 hover:text-red-500 transition-colors"
                   >
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
};

export default MasterMajors;
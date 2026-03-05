import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { LayoutGrid, Trash2, Plus, School } from 'lucide-react';
import Swal from 'sweetalert2';

const MasterClasses = () => {
  const [classes, setClasses] = useState([]);
  const [majors, setMajors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [formData, setFormData] = useState({ name: '', major_id: '' });

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    // Ambil data kelas beserta nama jurusannya
    const { data: classData } = await supabase.from('classes').select('*, majors(name)').order('name');
    // Ambil data jurusan buat dropdown
    const { data: majorData } = await supabase.from('majors').select('*').order('name');
    
    setClasses(classData || []);
    setMajors(majorData || []);
    setLoading(false);
  };

  const handleAddClass = async (e) => {
    e.preventDefault();
    if (!formData.name || !formData.major_id) return;

    const { error } = await supabase.from('classes').insert([formData]);
    if (!error) {
      setFormData({ name: '', major_id: '' });
      fetchInitialData();
      Swal.fire({ icon: 'success', title: 'Kelas Berhasil Ditambah!', timer: 1500, showConfirmButton: false });
    }
  };
  // fungsi  delete!
const handleDelete = async (id) => {
    const result = await Swal.fire({
      title: 'Yakin mau hapus?',
      text: "Siswa di kelas ini bakal kehilangan relasi kelasnya lho!",
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#ea580c',
      cancelButtonColor: '#64748b',
      confirmButtonText: 'Ya, Hapus!',
      background: document.documentElement.classList.contains('dark') ? '#18181b' : '#fff',
      color: document.documentElement.classList.contains('dark') ? '#fff' : '#000'
    });
  
    if (result.isConfirmed) {
      const { error } = await supabase.from('classes').delete().eq('id', id);
      if (error) {
        Swal.fire('Gagal!', error.message, 'error');
      } else {
        Swal.fire('Terhapus!', 'Kelas berhasil dibuang.', 'success');
        fetchInitialData(); // Refresh listnya
      }
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex transition-colors duration-300">
      <Sidebar role="admin" />
      <main className="flex-1 lg:ml-64 p-4 lg:p-8">
        <header className="mb-8 text-left">
          <h2 className="text-3xl font-bold text-slate-800 dark:text-zinc-100 flex items-center gap-3">
            <School className="text-orange-600" size={32} /> Master Kelas
          </h2>
          <p className="text-slate-500 dark:text-zinc-400">Kelola daftar kelas dan relasi jurusan</p>
        </header>

        {/* Form Tambah Kelas */}
        <div className="bg-white dark:bg-zinc-900 p-6 rounded-2xl shadow-sm border border-slate-200 dark:border-zinc-800 mb-8">
          <form onSubmit={handleAddClass} className="flex flex-col md:flex-row gap-4">
            <input 
              type="text" 
              placeholder="Nama Kelas (Contoh: 10 RPL 1)"
              className="flex-1 bg-slate-50 dark:bg-zinc-800 border-none p-3 rounded-xl outline-none focus:ring-2 focus:ring-orange-500 dark:text-white"
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
            />
            <select 
              className="flex-1 bg-slate-50 dark:bg-zinc-800 border-none p-3 rounded-xl outline-none focus:ring-2 focus:ring-orange-500 dark:text-white"
              value={formData.major_id}
              onChange={(e) => setFormData({...formData, major_id: e.target.value})}
            >
              <option value="">-- Pilih Jurusan --</option>
              {majors.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
            <button className="bg-orange-600 hover:bg-orange-700 text-white px-8 py-3 rounded-xl font-bold flex items-center justify-center gap-2 transition-all">
              <Plus size={20} /> Tambah
            </button>
          </form>
        </div>

        {/* Grid List Kelas */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {loading ? (
            <p className="dark:text-white animate-pulse font-bold italic">Narik data kelas dulu bro...</p>
          ) : (
            classes.map((c) => (
              <div key={c.id} className="bg-white dark:bg-zinc-900 p-6 rounded-2xl border border-slate-200 dark:border-zinc-800 flex justify-between items-center group hover:border-orange-500 transition-all">
                <div className="text-left">
                  <h3 className="text-xl font-bold dark:text-white uppercase">{c.name}</h3>
                  <p className="text-sm text-orange-600 font-medium italic">{c.majors?.name || 'Tanpa Jurusan'}</p>
                </div>
                <button 
                    onClick={() => handleDelete(c.id)} // <--- Tambahkan ini bro!
                    className="text-slate-300 hover:text-red-500 transition-colors"
                >
                 <Trash2 size={20} />
                </button>
              </div>
            ))
          )}
        </div>

      </main>
    </div>
  );
};

export default MasterClasses;
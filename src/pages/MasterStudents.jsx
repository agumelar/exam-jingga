import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { Users, Search, UserPlus, Trash2, Edit, GraduationCap, ArrowUpCircle, X, Download, Upload } from 'lucide-react';
import Swal from 'sweetalert2';
import * as XLSX from 'xlsx';

const MasterStudents = () => {
  const navigate = useNavigate();
  const [students, setStudents] = useState([]);
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterClass, setFilterClass] = useState(''); 
  const [showModal, setShowModal] = useState(false);
  const [showPromoteModal, setShowPromoteModal] = useState(false); 
  const [targetClass, setTargetClass] = useState('');
  const [isEdit, setIsEdit] = useState(false);
  const [currentId, setCurrentId] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

  const [formData, setFormData] = useState({
    nis: '', full_name: '', class_id: '', status: 'aktif'
  });

  useEffect(() => {
    fetchInitialData();
  }, []);

  const fetchInitialData = async () => {
    setLoading(true);
    await fetchStudents();
    const { data: classData } = await supabase.from('classes').select('id, name').order('name');
    setClasses(classData || []);
    setLoading(false);
  };

  const fetchStudents = async () => {
    const { data, error } = await supabase
      .from('students')
      .select(`*, classes (id, name)`)
      .eq('status', 'aktif') 
      .order('full_name');
    if (!error) setStudents(data);
  };

  // --- SUNTIKAN: FUNGSI EXCEL DENGAN PENGELOMPOKKAN KELAS ---
  const exportToExcel = () => {
    if (filteredStudents.length === 0) return Swal.fire('Kosong', 'Tidak ada data untuk di-export', 'warning');

    // 1. Proses Sorting: Urut Kelas Dulu, Baru Urut Nama
    const sortedData = [...filteredStudents].sort((a, b) => {
      const classA = a.classes?.name || '';
      const classB = b.classes?.name || '';
      // Bandingkan Nama Kelas
      if (classA < classB) return -1;
      if (classA > classB) return 1;
      // Jika Kelas Sama, Bandingkan Nama Siswa
      return a.full_name.localeCompare(b.full_name);
    });

    // 2. Mapping data ke format kolom Excel
    const dataForExcel = sortedData.map((s, index) => ({
      'No': index + 1,
      'Nama': s.full_name.toUpperCase(),
      'Kelas': s.classes?.name || '-',
      'NIS': s.nis,
      'Password': s.password_plain || '********'
    }));

    const worksheet = XLSX.utils.json_to_sheet(dataForExcel);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Data Akun Siswa");

    // Atur lebar kolom
    worksheet['!cols'] = [{wch: 5}, {wch: 35}, {wch: 15}, {wch: 15}, {wch: 20}];

    const className = filterClass ? classes.find(c => c.id === filterClass)?.name : "Semua_Kelas";
    XLSX.writeFile(workbook, `Data_Akun_Siswa_${className}.xlsx`);
    
    Swal.fire('Berhasil!', 'Excel sudah dikelompokkan per kelas.', 'success');
  };

  const handleDelete = async (id) => {
    const { isConfirmed } = await Swal.fire({
      title: 'Hapus Siswa?',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#ea580c',
      confirmButtonText: 'Ya, Hapus!'
    });
    if (isConfirmed) {
      const { error } = await supabase.from('students').delete().eq('id', id);
      if (!error) {
        Swal.fire('Terhapus!', 'Data berhasil dibuang.', 'success');
        fetchStudents();
      }
    }
  };

  const handleEdit = (s) => {
    setIsEdit(true);
    setCurrentId(s.id);
    setFormData({ nis: s.nis, full_name: s.full_name, class_id: s.class_id, status: s.status });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    const studentData = { 
        ...formData, 
        email: `${formData.nis}@student.smkn1rongga.sch.id`, 
        password_plain: `jingga${formData.nis}` 
    };
    
    const result = isEdit 
        ? await supabase.from('students').update(studentData).eq('id', currentId) 
        : await supabase.from('students').insert([studentData]);
    
    setIsSaving(false);
    if (!result.error) {
      setShowModal(false);
      fetchStudents();
      resetForm();
      Swal.fire('Berhasil!', 'Data tersimpan.', 'success');
    } else {
      Swal.fire('Gagal!', result.error.message, 'error');
    }
  };

  const resetForm = () => {
    setFormData({ nis: '', full_name: '', class_id: '', status: 'aktif' });
    setIsEdit(false);
    setCurrentId(null);
  };

  const handleMassPromote = async () => {
    if (!filterClass || !targetClass) return Swal.fire('Pilih kelas asal dan tujuan!');
    const studentsInClass = filteredStudents.map(s => s.id);
    const { error } = await supabase.from('students').update({ class_id: targetClass }).in('id', studentsInClass);
    if (!error) {
      Swal.fire('Berhasil!', `Siswa naik kelas.`, 'success');
      setShowPromoteModal(false);
      fetchStudents();
    }
  };

  const handleMassGraduate = async () => {
    if (!filterClass) return Swal.fire('Pilih kelas!');
    const selectedClassName = classes.find(c => c.id === filterClass)?.name;
    if (!selectedClassName?.includes('12')) return Swal.fire('Ops!', 'Hanya kelas 12.', 'warning');
    const { isConfirmed } = await Swal.fire({ title: 'Luluskan?', text: `Siswa di ${selectedClassName} akan lulus.`, icon: 'warning', showCancelButton: true });
    if (isConfirmed) {
      const studentsInClass = filteredStudents.map(s => s.id);
      await supabase.from('students').update({ status: 'Lulus' }).in('id', studentsInClass);
      fetchStudents();
    }
  };

  const filteredStudents = students.filter(s => {
    const matchSearch = s.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) || s.nis?.toString().includes(searchTerm);
    const matchClass = filterClass ? s.class_id === filterClass : true;
    return matchSearch && matchClass;
  });

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex transition-colors duration-300">
      <Sidebar role="admin" />
      <main className="flex-1 lg:ml-64 p-4 lg:p-8 text-left">
        <header className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="text-left">
            <h2 className="text-3xl font-black text-slate-800 dark:text-zinc-100 flex items-center gap-3 italic tracking-tighter uppercase">
              <Users className="text-orange-600" size={32} /> Master Siswa
            </h2>
            <p className="text-slate-500 dark:text-zinc-400 font-bold uppercase text-[10px] tracking-widest leading-relaxed">Database Akun & Manajemen Siswa Jingga</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button onClick={() => navigate('/import-siswa')} className="bg-emerald-600 text-white px-4 py-3 rounded-xl font-black flex items-center gap-2 shadow-lg text-[10px] uppercase tracking-wider"><Upload size={18} /> Import</button>
            <button onClick={exportToExcel} className="bg-blue-600 text-white px-4 py-3 rounded-xl font-black flex items-center gap-2 shadow-lg text-[10px] uppercase tracking-wider"><Download size={18} /> Export Akun</button>
            <button onClick={() => { resetForm(); setShowModal(true); }} className="bg-orange-600 text-white px-6 py-3 rounded-xl font-black flex items-center gap-2 shadow-lg text-[10px] uppercase tracking-wider"><UserPlus size={18} /> Tambah</button>
          </div>
        </header>

        {/* TOOLBAR FILTER */}
        <div className="bg-white dark:bg-zinc-900 p-4 rounded-2xl border border-slate-200 dark:border-zinc-800 mb-6 flex flex-wrap gap-4 items-center">
          <div className="flex-1 min-w-[200px] relative">
            <Search className="absolute left-4 top-3 text-slate-400" size={18} />
            <input type="text" placeholder="Cari nama atau NIS..." className="w-full pl-11 pr-4 py-2.5 bg-slate-50 dark:bg-zinc-800 rounded-xl outline-none dark:text-white font-bold" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
          </div>
          <select className="bg-slate-50 dark:bg-zinc-800 p-2.5 rounded-xl outline-none dark:text-white border-none font-black text-[11px] uppercase tracking-wider" value={filterClass} onChange={(e) => setFilterClass(e.target.value)}>
            <option value="">-- Semua Kelas --</option>
            {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          {filterClass && (
            <div className="flex gap-2">
              <button onClick={() => setShowPromoteModal(true)} className="bg-blue-600/10 text-blue-600 dark:text-blue-400 px-4 py-2.5 rounded-xl font-black text-[10px] uppercase tracking-wider flex items-center gap-2 border border-blue-600/20"><ArrowUpCircle size={16}/> Naik Kelas</button>
              <button onClick={handleMassGraduate} className="bg-green-600/10 text-green-600 dark:text-green-400 px-4 py-2.5 rounded-xl font-black text-[10px] uppercase tracking-wider flex items-center gap-2 border border-green-600/20"><GraduationCap size={16}/> Luluskan</button>
            </div>
          )}
        </div>

        {/* TABEL */}
        <div className="bg-white dark:bg-zinc-900 rounded-[2rem] border border-slate-200 dark:border-zinc-800 overflow-hidden shadow-sm">
          <table className="w-full text-left">
            <thead className="bg-slate-50 dark:bg-zinc-800/50 text-[10px] font-black uppercase text-slate-400 tracking-widest">
              <tr><th className="px-6 py-5">Siswa</th><th className="px-6 py-5">NIS</th><th className="px-6 py-5">Kelas</th><th className="px-6 py-5 text-center">Aksi</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-zinc-800 font-sans">
              {filteredStudents.map((s) => (
                <tr key={s.id} className="hover:bg-slate-50 dark:hover:bg-zinc-800/30 transition-all group">
                  <td className="px-6 py-4"><p className="font-black text-slate-700 dark:text-zinc-100 uppercase text-sm leading-tight">{s.full_name}</p><p className="text-[10px] text-slate-400 italic font-mono mt-1">{s.email}</p></td>
                  <td className="px-6 py-4 font-mono font-black text-sm text-orange-600">{s.nis}</td>
                  <td className="px-6 py-4"><span className="bg-slate-100 dark:bg-zinc-800 px-3 py-1 rounded-lg font-black text-slate-500 text-[10px] uppercase tracking-tighter border border-slate-200 dark:border-zinc-700">{s.classes?.name}</span></td>
                  <td className="px-6 py-4 text-center">
                    <div className="flex justify-center gap-2 opacity-40 group-hover:opacity-100 transition-opacity">
                      <button onClick={() => handleEdit(s)} className="p-2 bg-blue-50 dark:bg-blue-900/20 text-blue-600 rounded-lg hover:bg-blue-600 hover:text-white transition-all"><Edit size={16} /></button>
                      <button onClick={() => handleDelete(s.id)} className="p-2 bg-red-50 dark:bg-red-900/20 text-red-500 rounded-lg hover:bg-red-600 hover:text-white transition-all"><Trash2 size={16} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* MODAL TAMBAH/EDIT */}
        {showModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 text-left">
            <div className="bg-white dark:bg-zinc-950 w-full max-w-md rounded-[2.5rem] p-10 shadow-2xl">
              <div className="flex justify-between items-center mb-8 border-b dark:border-zinc-800 pb-6">
                <h3 className="text-2xl font-black italic tracking-tighter uppercase text-slate-800 dark:text-white">{isEdit ? 'Edit Akun' : 'Tambah Akun'}</h3>
                <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-red-500 transition-colors"><X size={24}/></button>
              </div>
              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label className="text-[10px] font-black uppercase text-slate-400 mb-2 block tracking-widest text-left">Nomor Induk Siswa (NIS)</label>
                  <input type="number" required className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl dark:text-white outline-none ring-2 ring-transparent focus:ring-orange-500 font-black transition-all" value={formData.nis} onChange={(e) => setFormData({...formData, nis: e.target.value})} />
                </div>
                <div>
                  <label className="text-[10px] font-black uppercase text-slate-400 mb-2 block tracking-widest text-left">Nama Lengkap</label>
                  <input type="text" required className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl dark:text-white outline-none ring-2 ring-transparent focus:ring-orange-500 font-black uppercase transition-all" value={formData.full_name} onChange={(e) => setFormData({...formData, full_name: e.target.value})} />
                </div>
                <div>
                  <label className="text-[10px] font-black uppercase text-slate-400 mb-2 block tracking-widest text-left">Penempatan Kelas</label>
                  <select required className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl dark:text-white outline-none ring-2 ring-transparent focus:ring-orange-500 font-black transition-all" value={formData.class_id} onChange={(e) => setFormData({...formData, class_id: e.target.value})}>
                    <option value="">-- Pilih Kelas --</option>
                    {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <button type="submit" disabled={isSaving} className="w-full bg-orange-600 text-white py-5 rounded-2xl font-black uppercase tracking-[0.2em] shadow-xl hover:bg-orange-700 transition-all mt-4 disabled:opacity-50">
                  {isSaving ? "MEMPROSES..." : "TERBITKAN DATA"}
                </button>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default MasterStudents;
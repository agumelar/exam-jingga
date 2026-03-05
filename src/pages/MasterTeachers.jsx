import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { 
  UserCheck, Search, Plus, Trash2, Edit, X, 
  Briefcase, Mail, FileUp, FileDown 
} from 'lucide-react';
import Swal from 'sweetalert2';
import * as XLSX from 'xlsx';

const MasterTeachers = () => {
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [isEdit, setIsEdit] = useState(false);
  const [currentId, setCurrentId] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
    role_level: 'guru',
    password: ''
  });

  useEffect(() => { fetchTeachers(); }, []);

  const fetchTeachers = async () => {
    setLoading(true);
    const { data, error } = await supabase.from('teachers').select('*').order('full_name');
    if (!error) setTeachers(data);
    setLoading(false);
  };

  const downloadTemplate = () => {
    const template = [
      { Nama: 'Guru Jingga, S.Pd', Email: 'guru@smkn1rongga.sch.id', Role: 'guru', Password: 'Jingga123' }
    ];
    const worksheet = XLSX.utils.json_to_sheet(template);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Template Guru");
    XLSX.writeFile(workbook, "Template_Import_Guru_Jingga.xlsx");
  };

  const handleImportExcel = (e) => {
    const file = e.target.files[0];
    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const data = new Uint8Array(event.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        const jsonData = XLSX.utils.sheet_to_json(workbook.Sheets[workbook.SheetNames[0]]);

        const formattedData = jsonData.map(item => ({
          full_name: item.Nama || item.full_name,
          email: item.Email || item.email,
          role_level: (item.Role || item.role_level || 'guru').toLowerCase(),
          password: item.Password || 'Jingga123' 
        }));

        const { error } = await supabase.from('teachers').insert(formattedData);
        if (error) throw error;
        Swal.fire('Berhasil!', `${formattedData.length} Guru diimport.`, 'success');
        fetchTeachers();
      } catch (error) {
        Swal.fire('Gagal!', 'Cek kolom Excel (Nama, Email, Role, Password)', 'error');
      }
    };
    reader.readAsArrayBuffer(file);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    
    const dataToSave = {
      ...formData,
      role_level: formData.role_level.toLowerCase(),
      password: formData.password || 'Jingga123'
    };

    let result;
    if (isEdit) {
      result = await supabase.from('teachers').update(dataToSave).eq('id', currentId);
    } else {
      result = await supabase.from('teachers').insert([dataToSave]);
    }
    
    setIsSaving(false);
    if (result.error) { 
      Swal.fire('Gagal!', result.error.message, 'error'); 
    } else {
      Swal.fire({ title: 'Berhasil!', text: `Password: ${dataToSave.password}`, icon: 'success' });
      setShowModal(false); resetForm(); fetchTeachers();
    }
  };

  const resetForm = () => { 
    setFormData({ full_name: '', email: '', role_level: 'guru', password: '' }); 
    setIsEdit(false); setCurrentId(null); 
  };

  const handleDelete = async (id) => {
    const { isConfirmed } = await Swal.fire({ title: 'Hapus Guru?', icon: 'warning', showCancelButton: true });
    if (isConfirmed) { await supabase.from('teachers').delete().eq('id', id); fetchTeachers(); }
  };

  const filteredTeachers = teachers.filter(t => 
    t.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) || t.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex font-sans text-left">
      <Sidebar role="admin" />
      <main className="flex-1 lg:ml-64 p-4 lg:p-8">
        <header className="mb-8 flex flex-col xl:flex-row xl:items-center justify-between gap-4">
          <div className="text-left">
            <h2 className="text-3xl font-black text-slate-800 dark:text-zinc-100 flex items-center gap-3 italic uppercase tracking-tighter">
              <UserCheck className="text-orange-600" size={32} /> Master Guru
            </h2>
            <p className="text-slate-500 font-medium">Pengelolaan Akun Pengajar</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button onClick={downloadTemplate} className="bg-slate-800 text-white px-5 py-3 rounded-2xl font-black text-xs uppercase"><FileDown size={18} className="inline mr-2"/> Template</button>
            <label className="cursor-pointer bg-emerald-600 text-white px-5 py-3 rounded-2xl font-black text-xs uppercase">
              <FileUp size={18} className="inline mr-2"/> Import
              <input type="file" className="hidden" onChange={handleImportExcel} />
            </label>
            <button onClick={() => { resetForm(); setShowModal(true); }} className="bg-orange-600 text-white px-5 py-3 rounded-2xl font-black text-xs uppercase"><Plus size={18} className="inline mr-2"/> Tambah</button>
          </div>
        </header>

        <div className="mb-8 relative">
          <Search className="absolute left-4 top-4 text-slate-400" size={20} />
          <input type="text" placeholder="Cari guru..." className="w-full pl-12 pr-4 py-4 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-2xl outline-none dark:text-zinc-100 shadow-sm" value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {loading ? (
            <div className="col-span-full py-20 text-center animate-pulse font-bold text-slate-400 italic uppercase">Memuat guru...</div>
          ) : filteredTeachers.map((t) => (
            <div key={t.id} className="bg-white dark:bg-zinc-900 p-6 rounded-[2.5rem] border border-slate-100 dark:border-zinc-800 shadow-sm hover:border-orange-500 transition-all text-left">
              <div className="flex items-start justify-between mb-4">
                <div className={`p-4 rounded-2xl ${t.role_level === 'kurikulum' ? 'bg-purple-100 text-purple-600 dark:bg-purple-900/20' : 'bg-orange-100 text-orange-600 dark:bg-orange-900/20'}`}><Briefcase size={24} /></div>
                <div className="flex gap-1">
                  <button onClick={() => { setIsEdit(true); setCurrentId(t.id); setFormData({full_name: t.full_name, email: t.email, role_level: t.role_level, password: t.password}); setShowModal(true); }} className="p-2 text-slate-300 hover:text-blue-500"><Edit size={18}/></button>
                  <button onClick={() => handleDelete(t.id)} className="p-2 text-slate-300 hover:text-red-500"><Trash2 size={18}/></button>
                </div>
              </div>
              <h3 className="text-xl font-black dark:text-white uppercase leading-tight mb-2 tracking-tighter">{t.full_name}</h3>
              <p className="text-xs text-slate-400 mb-5">{t.email}</p>
              <span className={`px-4 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest ${t.role_level === 'kurikulum' ? 'bg-purple-600 text-white' : 'bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400'}`}>{t.role_level}</span>
            </div>
          ))}
        </div>

        {showModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 text-left">
            <div className="bg-white dark:bg-zinc-950 w-full max-w-md rounded-[3rem] p-10 shadow-2xl animate-in zoom-in-95">
              <div className="flex justify-between items-center mb-8">
                <h3 className="text-2xl font-black dark:text-white italic uppercase tracking-tighter">{isEdit ? 'Edit Guru' : 'Guru Baru'}</h3>
                <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-red-500"><X size={20}/></button>
              </div>
              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label className="text-[10px] font-black uppercase text-slate-400 ml-2 mb-2 block">Nama Lengkap</label>
                  <input type="text" required className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl dark:text-white border-none shadow-inner" value={formData.full_name} onChange={(e) => setFormData({...formData, full_name: e.target.value})} />
                </div>
                <div>
                  <label className="text-[10px] font-black uppercase text-slate-400 ml-2 mb-2 block">Email Login</label>
                  <input type="email" required className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl dark:text-white border-none shadow-inner" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} />
                </div>
                <div>
                  <label className="text-[10px] font-black uppercase text-slate-400 ml-2 mb-2 block">Password</label>
                  <input type="text" className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl dark:text-white border-none shadow-inner font-mono" placeholder="Default: Jingga123" value={formData.password} onChange={(e) => setFormData({...formData, password: e.target.value})} />
                </div>
                <div>
                  <label className="text-[10px] font-black uppercase text-slate-400 ml-2 mb-2 block">Jabatan</label>
                  <select className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl dark:text-white border-none appearance-none" value={formData.role_level} onChange={(e) => setFormData({...formData, role_level: e.target.value})}>
                    <option value="guru">Guru</option>
                    <option value="kurikulum">Kurikulum</option>
                    <option value="admin">Admin</option>
                  </select>
                </div>
                <button type="submit" disabled={isSaving} className="w-full bg-orange-600 text-white py-5 rounded-2xl font-black uppercase shadow-lg shadow-orange-600/30">
                  {isSaving ? "PROSES..." : "SIMPAN"}
                </button>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default MasterTeachers;
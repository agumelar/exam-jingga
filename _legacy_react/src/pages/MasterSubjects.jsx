import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { 
  Book, Search, Plus, Trash2, Edit, X, 
  FileUp, FileDown, Bookmark 
} from 'lucide-react';
import Swal from 'sweetalert2';
import * as XLSX from 'xlsx';

const MasterSubjects = () => {
  const [subjects, setSubjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [isEdit, setIsEdit] = useState(false);
  const [currentId, setCurrentId] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

  // Sesuai skema lu: cuma butuh 'name'
  const [formData, setFormData] = useState({
    name: ''
  });

  useEffect(() => { fetchSubjects(); }, []);

  const fetchSubjects = async () => {
    setLoading(true);
    const { data, error } = await supabase.from('subjects').select('*').order('name');
    if (!error) setSubjects(data);
    setLoading(false);
  };

  // TEMPLATE EXCEL (Hanya 1 Kolom: Nama_Mapel)
  const downloadTemplate = () => {
    const template = [
      { Nama_Mapel: 'Konsentrasi Keahlian RPL' },
      { Nama_Mapel: 'Dasar-Dasar PPLG' },
      { Nama_Mapel: 'Bahasa Indonesia' }
    ];
    const worksheet = XLSX.utils.json_to_sheet(template);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Template Mapel");
    XLSX.writeFile(workbook, "Template_Import_Mapel_Jingga.xlsx");
  };

  // IMPORT EXCEL
  const handleImportExcel = (e) => {
    const file = e.target.files[0];
    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const data = new Uint8Array(event.target.result);
        const workbook = XLSX.read(data, { type: 'array' });
        const sheetName = workbook.SheetNames[0];
        const worksheet = workbook.Sheets[sheetName];
        const jsonData = XLSX.utils.sheet_to_json(worksheet);

        // Mapping ke kolom 'name' sesuai skema lu
        const formattedData = jsonData.map(item => ({
          name: item.Nama_Mapel || item.name
        }));

        const { error } = await supabase.from('subjects').insert(formattedData);
        if (error) throw error;
        Swal.fire('Berhasil!', `${formattedData.length} Mapel berhasil diimport`, 'success');
        fetchSubjects();
      } catch (error) {
        Swal.fire('Gagal!', 'Pastikan kolom Excel bernama: Nama_Mapel', 'error');
      }
    };
    reader.readAsArrayBuffer(file);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSaving(true);
    let error;
    if (isEdit) {
      const { error: err } = await supabase.from('subjects').update(formData).eq('id', currentId);
      error = err;
    } else {
      const { error: err } = await supabase.from('subjects').insert([formData]);
      error = err;
    }
    setIsSaving(false);
    if (error) { 
      Swal.fire('Gagal!', error.message, 'error'); 
    } else {
      Swal.fire({ title: 'Berhasil!', icon: 'success', timer: 1500, showConfirmButton: false });
      setShowModal(false); resetForm(); fetchSubjects();
    }
  };

  const resetForm = () => { 
    setFormData({ name: '' }); 
    setIsEdit(false); 
    setCurrentId(null); 
  };

  const handleDelete = async (id) => {
    const { isConfirmed } = await Swal.fire({ title: 'Hapus Mapel?', text: 'Hapus mata pelajaran ini?', icon: 'warning', showCancelButton: true, confirmButtonColor: '#ea580c' });
    if (isConfirmed) {
      await supabase.from('subjects').delete().eq('id', id);
      fetchSubjects();
    }
  };

  const filteredSubjects = subjects.filter(s => 
    s.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex transition-colors duration-300 font-sans text-left">
      <Sidebar role="admin" />
      <main className="flex-1 lg:ml-64 p-4 lg:p-8 text-left">
        <header className="mb-8 flex flex-col xl:flex-row xl:items-center justify-between gap-4">
          <div>
            <h2 className="text-3xl font-black text-slate-800 dark:text-zinc-100 flex items-center gap-3 italic tracking-tighter uppercase">
              <Book className="text-orange-600" size={32} /> Master Mapel
            </h2>
            <p className="text-slate-500 dark:text-zinc-400 font-medium">Total: {subjects.length} Mata Pelajaran</p>
          </div>
          
          <div className="flex flex-wrap gap-3">
            <button onClick={downloadTemplate} className="bg-slate-800 text-white px-5 py-3 rounded-2xl font-black flex items-center gap-2 shadow-lg hover:bg-black transition-all active:scale-95 text-sm uppercase">
              <FileDown size={18} /> Template
            </button>
            <label className="cursor-pointer bg-emerald-600 text-white px-5 py-3 rounded-2xl font-black flex items-center gap-2 shadow-lg shadow-emerald-600/20 hover:bg-emerald-700 transition-all active:scale-95 text-sm uppercase">
              <FileUp size={18} /> Import
              <input type="file" className="hidden" accept=".xlsx, .xls" onChange={handleImportExcel} />
            </label>
            <button onClick={() => { resetForm(); setShowModal(true); }} className="bg-orange-600 text-white px-5 py-3 rounded-2xl font-black flex items-center gap-2 shadow-lg shadow-orange-600/20 hover:bg-orange-700 transition-all active:scale-95 text-sm uppercase">
              <Plus size={18} /> Tambah
            </button>
          </div>
        </header>

        <div className="mb-8 relative">
          <Search className="absolute left-4 top-4 text-slate-400" size={20} />
          <input 
            type="text" placeholder="Cari mata pelajaran..." 
            className="w-full pl-12 pr-4 py-4 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 rounded-2xl outline-none focus:ring-2 focus:ring-orange-500 dark:text-zinc-100 shadow-sm"
            value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {loading ? (
            <div className="col-span-full py-20 text-center animate-pulse font-bold text-slate-400 italic tracking-tighter">Memuat data mapel...</div>
          ) : filteredSubjects.map((s) => (
            <div key={s.id} className="bg-white dark:bg-zinc-900 p-6 rounded-[2.5rem] border border-slate-100 dark:border-zinc-800 shadow-sm hover:border-orange-500 transition-all group">
              <div className="flex items-start justify-between mb-4">
                <div className="p-4 rounded-2xl bg-orange-100 text-orange-600 dark:bg-orange-900/20">
                  <Bookmark size={24} />
                </div>
                <div className="flex gap-1">
                  <button onClick={() => { setIsEdit(true); setCurrentId(s.id); setFormData({name: s.name}); setShowModal(true); }} className="p-2 text-slate-300 hover:text-blue-500 transition-colors"><Edit size={18}/></button>
                  <button onClick={() => handleDelete(s.id)} className="p-2 text-slate-300 hover:text-red-500 transition-colors"><Trash2 size={18}/></button>
                </div>
              </div>
              <h3 className="text-xl font-black dark:text-white uppercase leading-tight tracking-tighter">{s.name}</h3>
            </div>
          ))}
        </div>

        {showModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
            <div className="bg-white dark:bg-zinc-950 w-full max-w-md rounded-[3rem] p-10 shadow-2xl animate-in zoom-in-95 duration-200">
              <div className="flex justify-between items-center mb-8">
                <h3 className="text-2xl font-black dark:text-white italic uppercase tracking-tighter">{isEdit ? 'EDIT MAPEL' : 'MAPEL BARU'}</h3>
                <button onClick={() => setShowModal(false)} className="bg-slate-100 dark:bg-zinc-900 p-2 rounded-full text-slate-400 hover:text-red-500 transition-all"><X size={20}/></button>
              </div>
              <form onSubmit={handleSubmit} className="space-y-5">
                <div>
                  <label className="text-[10px] font-black uppercase text-slate-400 ml-2 mb-2 block tracking-widest">Nama Mata Pelajaran</label>
                  <input type="text" required placeholder="Contoh: Matematika Wajib" className="w-full bg-slate-50 dark:bg-zinc-900 p-4 rounded-2xl dark:text-white outline-none focus:ring-2 focus:ring-orange-500 border-none shadow-inner" value={formData.name} onChange={(e) => setFormData({ name: e.target.value })} />
                </div>
                <button type="submit" disabled={isSaving} className="w-full bg-orange-600 text-white py-5 rounded-2xl font-black shadow-lg shadow-orange-600/30 hover:bg-orange-700 transition-all active:scale-95 mt-4 uppercase">
                  {isSaving ? "Sedang Menyimpan..." : "Simpan Mapel"}
                </button>
              </form>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default MasterSubjects;
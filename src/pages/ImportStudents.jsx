import React, { useState, useEffect } from 'react';
import Sidebar from '../components/Sidebar';
import { supabase } from '../supabaseClient';
import * as XLSX from 'xlsx';
import { Upload, Users, Loader2, FileDown } from 'lucide-react';
import Swal from 'sweetalert2';

const ImportStudents = () => {
  const [previewData, setPreviewData] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [listClasses, setListClasses] = useState([]);

  useEffect(() => {
    const fetchReferenceData = async () => {
      const { data, error } = await supabase.from('classes').select('id, name, major_id');
      if (!error) setListClasses(data);
    };
    fetchReferenceData();
  }, []);

  // --- TOMBOL DOWNLOAD TEMPLATE YANG TADI ILANG ---
  const downloadTemplate = () => {
    const template = [
      { nis: '252610001', nama: 'CONTOH SISWA BARU', nama_kelas: '10 RPL 1' },
      { nis: '252610002', nama: 'CONTOH SISWA KEDUA', nama_kelas: '11 TSM 2' },
    ];
    const ws = XLSX.utils.json_to_sheet(template);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Template_Siswa");
    XLSX.writeFile(wb, "Template_SIAKAD_Jingga.xlsx");
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (evt) => {
      const bstr = evt.target.result;
      const wb = XLSX.read(bstr, { type: 'binary' });
      const data = XLSX.utils.sheet_to_json(wb.Sheets[wb.SheetNames[0]]);
      setPreviewData(data); 
    };
    reader.readAsBinaryString(file);
  };

  const handleUpload = async () => {
    if (previewData.length === 0) return;
    setIsUploading(true);

    const errorLogs = [];
    const finalData = previewData.map((row, index) => {
      const klsMatch = listClasses.find(
        (k) => k.name.trim().toUpperCase() === row.nama_kelas?.toString().trim().toUpperCase()
      );

      if (!klsMatch) {
        errorLogs.push(`Baris ${index + 2}: ${row.nama} (Kelas "${row.nama_kelas}" gak ketemu)`);
      }

      return {
        nis: row.nis?.toString().trim(),
        full_name: row.nama?.trim(),
        class_id: klsMatch?.id || null,
        major_id: klsMatch?.major_id || null,
        email: `${row.nis}@student.smkn1rongga.sch.id`,
        password_plain: `jingga${row.nis}`,
        status: 'aktif'
      };
    });

    const validData = finalData.filter(d => d.class_id !== null);

    if (errorLogs.length > 0) {
      setIsUploading(false);
      Swal.fire({
        title: 'Ada Kelas Tidak Cocok!',
        html: `<div style="text-align:left; max-height:200px; overflow-y:auto; font-size:11px;">${errorLogs.join('<br/>')}</div>`,
        icon: 'warning'
      });
      return;
    }

    const { error } = await supabase.from('students').upsert(validData, { onConflict: 'nis' });
    setIsUploading(false);

    if (error) {
      Swal.fire('Gagal!', error.message, 'error');
    } else {
      Swal.fire('Berhasil!', `${validData.length} Siswa Berhasil Masuk Database.`, 'success');
      setPreviewData([]);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex transition-colors duration-300">
      <Sidebar role="admin" />
      <main className="flex-1 lg:ml-64 p-4 lg:p-8">
        {/* Header dengan Tombol Download */}
        <header className="mb-8 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="text-left">
            <h2 className="text-3xl font-bold text-slate-800 dark:text-zinc-100">Import Siswa</h2>
            <p className="text-slate-500 dark:text-zinc-400 font-medium italic">Password otomatis: jingga + NIS</p>
          </div>
          
          <button 
            onClick={downloadTemplate}
            className="flex items-center gap-2 bg-white dark:bg-zinc-900 border border-slate-200 dark:border-zinc-800 px-4 py-2.5 rounded-xl text-orange-600 font-bold hover:bg-orange-50 transition-all shadow-sm"
          >
            <FileDown size={20} /> Download Template Excel
          </button>
        </header>
        
        <div className="bg-white dark:bg-zinc-900 p-12 rounded-3xl border-2 border-dashed border-slate-300 dark:border-zinc-800 text-center mb-8">
          <input type="file" id="up-excel" hidden onChange={handleFileChange} accept=".xlsx, .xls" />
          <label htmlFor="up-excel" className="cursor-pointer flex flex-col items-center">
            <Upload size={48} className="text-orange-600 mb-4" />
            <p className="text-lg font-bold dark:text-zinc-100">Upload File Excel Di Sini</p>
            <p className="text-sm text-slate-400">Kolom wajib: nis, nama, nama_kelas</p>
          </label>
        </div>

        {previewData.length > 0 && (
          <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-xl overflow-hidden animate-in fade-in slide-in-from-bottom-4">
            <div className="p-5 flex justify-between items-center border-b dark:border-zinc-800 bg-slate-50/50 dark:bg-zinc-800/50">
              <span className="font-bold dark:text-zinc-100 flex items-center gap-2">
                <Users className="text-orange-600" size={20} /> Preview ({previewData.length} Siswa)
              </span>
              <button onClick={handleUpload} disabled={isUploading} className="bg-orange-600 text-white px-8 py-2.5 rounded-xl font-black flex items-center gap-2 shadow-lg shadow-orange-600/20 active:scale-95 transition-all">
                {isUploading ? <><Loader2 className="animate-spin" /> PROSES...</> : 'GASS IMPORT DATA'}
              </button>
            </div>
            <div className="max-h-96 overflow-y-auto">
              <table className="w-full text-left">
                <thead className="bg-slate-50 dark:bg-zinc-800 text-xs uppercase text-slate-500 sticky top-0">
                  <tr><th className="px-6 py-4">NIS</th><th className="px-6 py-4">Nama</th><th className="px-6 py-4">Kelas</th></tr>
                </thead>
                <tbody className="divide-y dark:divide-zinc-800">
                  {previewData.map((row, i) => (
                    <tr key={i} className="text-sm dark:text-zinc-300 hover:bg-orange-50/30 dark:hover:bg-orange-900/10">
                      <td className="px-6 py-3 font-mono font-bold text-orange-600">{row.nis}</td>
                      <td className="px-6 py-3 uppercase">{row.nama}</td>
                      <td className="px-6 py-3 font-bold">{row.nama_kelas}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default ImportStudents;
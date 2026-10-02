import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { Save, Upload, Image as ImageIcon, CheckCircle, Loader2 } from 'lucide-react';

const Settings = () => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [settings, setSettings] = useState({
    header_1: '', header_2: '', header_3: '',
    school_name: '', school_address: '', school_website: '', school_email: '',
    school_phone: '', school_postal_code: '', 
    school_majors_list: '', academic_year: '', semester: '', exam_name: '',
    headmaster_name: '', headmaster_nip: '', curriculum_vicedir_name: '',
    curriculum_vicedir_nip: '', exam_city: '', exam_date: '', // <--- Ada exam_date
    logo_left_url: '', logo_right_url: '', watermark_url: '', school_seal_url: '',
    headmaster_signature_url: '', curriculum_signature_url: ''
  });

  useEffect(() => { fetchSettings(); }, []);

  const fetchSettings = async () => {
    const { data, error } = await supabase.from('settings').select('*').limit(1);
    if (error) {
      console.error("Gagal narik data:", error);
      return;
    }
    if (data && data.length > 0) {
      // Gabungin data dari database dengan state bawaan biar aman
      setSettings(prev => ({ ...prev, ...data[0] }));
    }
  };

  const compressImage = (file) => {
    return new Promise((resolve) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = (event) => {
        const img = new Image();
        img.src = event.target.result;
        img.onload = () => {
          const canvas = document.createElement('canvas');
          let width = img.width;
          let height = img.height;
          const MAX_SIZE = 800;
          if (width > height) {
            if (width > MAX_SIZE) { height *= MAX_SIZE / width; width = MAX_SIZE; }
          } else {
            if (height > MAX_SIZE) { width *= MAX_SIZE / height; height = MAX_SIZE; }
          }
          canvas.width = width;
          canvas.height = height;
          const ctx = canvas.getContext('2d');
          ctx.drawImage(img, 0, 0, width, height);
          canvas.toBlob((blob) => {
            resolve(new File([blob], file.name, { type: 'image/webp' }));
          }, 'image/webp', 0.7);
        };
      };
    });
  };

  const handleUpload = async (e, column) => {
    try {
      setLoading(true);
      const file = e.target.files[0];
      if (!file) return;

      const compressedFile = await compressImage(file);
      const fileExt = 'webp'; 
      const fileName = `${column}-${Date.now()}.${fileExt}`;
      const filePath = `${fileName}`;

      const { error: uploadError } = await supabase.storage.from('assets').upload(filePath, compressedFile);
      if (uploadError) throw uploadError;

      const { data: { publicUrl } } = supabase.storage.from('assets').getPublicUrl(filePath);

      setSettings({ ...settings, [column]: publicUrl });
      setMessage(`Berhasil upload ${column.replace(/_/g, ' ')}`);
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      alert('Gagal upload: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    const { id, updated_at, ...payload } = settings;

    try {
      if (id) {
        const { error } = await supabase.from('settings').update(payload).eq('id', id);
        if (error) throw error;
      } else {
        const { error } = await supabase.from('settings').insert([payload]);
        if (error) throw error;
        fetchSettings(); 
      }
      
      setMessage('Semua pengaturan berhasil disimpan!');
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      alert("Gagal menyimpan: " + err.message);
    } finally {
      setLoading(false);
    }
  };

  const ImageUploadBox = ({ label, column, value }) => (
    <div className="bg-white dark:bg-zinc-900 p-4 rounded-2xl border border-zinc-200 dark:border-zinc-800">
      <label className="block text-[10px] font-black uppercase tracking-widest text-zinc-400 mb-3">{label}</label>
      <div className="flex items-center gap-4">
        <div className="w-16 h-16 rounded-xl bg-zinc-100 dark:bg-zinc-800 flex items-center justify-center overflow-hidden border border-dashed border-zinc-300 relative">
          {value ? <img src={value} alt="Preview" className="w-full h-full object-contain" /> : <ImageIcon className="text-zinc-400" size={20} />}
          {loading && <div className="absolute inset-0 bg-black/20 flex items-center justify-center backdrop-blur-sm"><Loader2 className="animate-spin text-white" size={16} /></div>}
        </div>
        <div className="flex-1">
          <label className="inline-flex items-center px-4 py-2 bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 text-zinc-900 dark:text-white rounded-lg cursor-pointer transition-all text-[10px] font-bold uppercase tracking-wider">
            <Upload size={12} className="mr-2" /> Upload
            <input type="file" className="hidden" onChange={(e) => handleUpload(e, column)} accept="image/*" />
          </label>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex font-sans">
      <Sidebar role="admin" />
      <main className="flex-1 lg:ml-64 p-8">
        <div className="max-w-5xl mx-auto">
          <header className="mb-8 flex justify-between items-center">
            <div>
              <h2 className="text-4xl font-black italic uppercase tracking-tighter text-zinc-900 dark:text-white">Settings</h2>
              <p className="text-orange-600 font-bold text-[10px] uppercase tracking-[0.3em] mt-1">Konfigurasi Identitas Sekolah (Auto-Sync)</p>
            </div>
            {message && <div className="flex items-center gap-2 bg-green-100 text-green-700 px-4 py-2 rounded-xl text-[10px] font-bold animate-fade-in"><CheckCircle size={14} /> {message}</div>}
          </header>

          <form onSubmit={handleSubmit} className="space-y-8 pb-20">
            {/* KOP SURAT / HEADER TEXT */}
            <div className="bg-white dark:bg-zinc-900 p-8 rounded-[2.5rem] border border-zinc-200 dark:border-zinc-800 shadow-sm grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="md:col-span-3 flex items-center gap-2 mb-2 text-orange-600">
                <div className="h-1 w-8 bg-orange-600 rounded-full"></div>
                <h3 className="text-xs font-black uppercase tracking-widest">Teks Kop Surat (Header)</h3>
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Header Baris 1</label>
                <input type="text" placeholder="Cth: Pemerintah Daerah Provinsi..." className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm focus:ring-2 focus:ring-orange-500 transition-all" 
                  value={settings.header_1 || ''} onChange={(e) => setSettings({...settings, header_1: e.target.value})} />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Header Baris 2</label>
                <input type="text" placeholder="Cth: Dinas Pendidikan" className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm focus:ring-2 focus:ring-orange-500 transition-all" 
                  value={settings.header_2 || ''} onChange={(e) => setSettings({...settings, header_2: e.target.value})} />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Header Baris 3</label>
                <input type="text" placeholder="Cth: Cabang Dinas Pendidikan..." className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm focus:ring-2 focus:ring-orange-500 transition-all" 
                  value={settings.header_3 || ''} onChange={(e) => setSettings({...settings, header_3: e.target.value})} />
              </div>
            </div>

            {/* INFORMASI SEKOLAH */}
            <div className="bg-white dark:bg-zinc-900 p-8 rounded-[2.5rem] border border-zinc-200 dark:border-zinc-800 shadow-sm grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="md:col-span-2 flex items-center gap-2 mb-2 text-orange-600">
                <div className="h-1 w-8 bg-orange-600 rounded-full"></div>
                <h3 className="text-xs font-black uppercase tracking-widest">Identitas Dasar</h3>
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Nama Sekolah</label>
                <input type="text" className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm focus:ring-2 focus:ring-orange-500 transition-all" 
                  value={settings.school_name || ''} onChange={(e) => setSettings({...settings, school_name: e.target.value})} />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Daftar Jurusan</label>
                <input type="text" className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm focus:ring-2 focus:ring-orange-500 transition-all" 
                  value={settings.school_majors_list || ''} onChange={(e) => setSettings({...settings, school_majors_list: e.target.value})} />
              </div>
              <div className="md:col-span-2 space-y-1">
                <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Alamat Lengkap</label>
                <textarea className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm" rows="2"
                  value={settings.school_address || ''} onChange={(e) => setSettings({...settings, school_address: e.target.value})} />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Telepon</label>
                <input type="text" className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm focus:ring-2 focus:ring-orange-500 transition-all" 
                  value={settings.school_phone || ''} onChange={(e) => setSettings({...settings, school_phone: e.target.value})} />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Kode Pos / Area</label>
                <input type="text" placeholder="Cth: Bandung Barat 40565" className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm focus:ring-2 focus:ring-orange-500 transition-all" 
                  value={settings.school_postal_code || ''} onChange={(e) => setSettings({...settings, school_postal_code: e.target.value})} />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Website</label>
                <input type="text" className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm focus:ring-2 focus:ring-orange-500 transition-all" 
                  value={settings.school_website || ''} onChange={(e) => setSettings({...settings, school_website: e.target.value})} />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Email</label>
                <input type="text" className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm focus:ring-2 focus:ring-orange-500 transition-all" 
                  value={settings.school_email || ''} onChange={(e) => setSettings({...settings, school_email: e.target.value})} />
              </div>
            </div>

            {/* ASSETS DIGITAL */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
               <ImageUploadBox label="Logo Pemda (Kiri)" column="logo_left_url" value={settings.logo_left_url} />
               <ImageUploadBox label="Logo Sekolah (Kanan)" column="logo_right_url" value={settings.logo_right_url} />
               <ImageUploadBox label="Watermark" column="watermark_url" value={settings.watermark_url} />
               <ImageUploadBox label="Cap Stempel" column="school_seal_url" value={settings.school_seal_url} />
               <ImageUploadBox label="TTD Kepala Sekolah" column="headmaster_signature_url" value={settings.headmaster_signature_url} />
               <ImageUploadBox label="TTD Wakasek Kurikulum" column="curriculum_signature_url" value={settings.curriculum_signature_url} />
            </div>

            {/* PEJABAT TTD */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white dark:bg-zinc-900 p-8 rounded-[2.5rem] border border-zinc-200 dark:border-zinc-800">
                <h3 className="text-xs font-black uppercase tracking-widest text-orange-600 mb-6 flex items-center gap-2">
                  <span className="w-2 h-2 bg-orange-600 rounded-full"></span> Kepala Sekolah
                </h3>
                <div className="space-y-4">
                  <input type="text" placeholder="Nama & Gelar" className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm" 
                    value={settings.headmaster_name || ''} onChange={(e) => setSettings({...settings, headmaster_name: e.target.value})} />
                  <input type="text" placeholder="NIP" className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm" 
                    value={settings.headmaster_nip || ''} onChange={(e) => setSettings({...settings, headmaster_nip: e.target.value})} />
                </div>
              </div>
              <div className="bg-white dark:bg-zinc-900 p-8 rounded-[2.5rem] border border-zinc-200 dark:border-zinc-800">
                <h3 className="text-xs font-black uppercase tracking-widest text-orange-600 mb-6 flex items-center gap-2">
                  <span className="w-2 h-2 bg-orange-600 rounded-full"></span> Wakasek Kurikulum
                </h3>
                <div className="space-y-4">
                  <input type="text" placeholder="Nama & Gelar" className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm" 
                    value={settings.curriculum_vicedir_name || ''} onChange={(e) => setSettings({...settings, curriculum_vicedir_name: e.target.value})} />
                  <input type="text" placeholder="NIP" className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm" 
                    value={settings.curriculum_vicedir_nip || ''} onChange={(e) => setSettings({...settings, curriculum_vicedir_nip: e.target.value})} />
                </div>
              </div>
            </div>

            {/* DETAIL PELAKSANAAN & TITIMANGSA */}
            <div className="bg-white dark:bg-zinc-900 p-8 rounded-[2.5rem] border border-zinc-200 dark:border-zinc-800 shadow-sm grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
               <div className="space-y-1">
                 <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Kota (Titimangsa)</label>
                 <input type="text" placeholder="Cth: Rongga" className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm" 
                   value={settings.exam_city || ''} onChange={(e) => setSettings({...settings, exam_city: e.target.value})} />
               </div>
               
               {/* INPUT TANGGAL TITIMANGSA */}
               <div className="space-y-1">
                 <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Tanggal (Titimangsa)</label>
                 <input type="text" placeholder="Cth: 10 Maret 2025" className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm" 
                   value={settings.exam_date || ''} onChange={(e) => setSettings({...settings, exam_date: e.target.value})} />
               </div>

               <div className="space-y-1">
                 <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Tahun Ajaran</label>
                 <select 
                   className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm focus:ring-2 focus:ring-orange-500 transition-all outline-none"
                   value={settings.academic_year || ''} 
                   onChange={(e) => setSettings({...settings, academic_year: e.target.value})}
                 >
                   <option value="">Pilih Tahun</option>
                   <option value="2023/2024">2023/2024</option>
                   <option value="2024/2025">2024/2025</option>
                   <option value="2025/2026">2025/2026</option>
                   <option value="2026/2027">2026/2027</option>
                 </select>
               </div>

               <div className="space-y-1">
                 <label className="text-[10px] font-bold text-zinc-500 uppercase ml-1">Nama Ujian</label>
                 <input type="text" className="w-full bg-zinc-50 dark:bg-zinc-800 text-zinc-900 dark:text-white border-none rounded-xl p-3 text-sm" 
                   value={settings.exam_name || ''} onChange={(e) => setSettings({...settings, exam_name: e.target.value})} />
               </div>
            </div>

            <button type="submit" disabled={loading} className="fixed bottom-8 right-8 bg-orange-600 text-white px-8 py-4 rounded-3xl font-black uppercase tracking-widest shadow-2xl hover:bg-orange-700 transition-all flex items-center gap-3 active:scale-95 disabled:opacity-50 z-50">
              <Save size={20} /> {loading ? 'Processing...' : 'Simpan Semua'}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
};

export default Settings;
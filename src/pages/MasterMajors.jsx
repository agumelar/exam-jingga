import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { GraduationCap, RefreshCw, ShieldCheck, Database } from 'lucide-react';
import Swal from 'sweetalert2';
import { masterDataSyncService } from '../services/masterDataSync';
import M3Button from '../components/ui/M3Button';
import M3Card from '../components/ui/M3Card';
import M3Badge from '../components/ui/M3Badge';

const MasterMajors = () => {
  const [majors, setMajors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    fetchMajors();
  }, []);

  const fetchMajors = async () => {
    setLoading(true);
    const { data, error } = await supabase.from('majors').select('*').order('name');
    if (!error) setMajors(data || []);
    setLoading(false);
  };

  const handleSyncMajors = async () => {
    setSyncing(true);
    Swal.fire({
      title: 'Menyinkronkan Data Jurusan...',
      text: 'Menghubungkan ke data.smkn1rongga.sch.id...',
      allowOutsideClick: false,
      didOpen: () => Swal.showLoading()
    });

    const res = await masterDataSyncService.syncMajors();
    setSyncing(false);

    if (res.success) {
      await fetchMajors();
      Swal.fire('Berhasil!', `Data Kompetensi Keahlian / Jurusan tersinkronisasi.`, 'success');
    } else {
      Swal.fire('Gagal!', res.error, 'error');
    }
  };

  return (
    <div className="flex h-screen bg-stone-50 dark:bg-stone-950 font-sans text-left transition-colors duration-300">
      <Sidebar />
      <div className="flex-1 lg:ml-64 flex flex-col overflow-hidden">
        
        {/* M3 Header */}
        <header className="bg-white/90 dark:bg-stone-900/90 backdrop-blur-md border-b border-stone-200 dark:border-stone-800 p-4 lg:p-6 flex justify-between items-center z-10">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-orange-100 dark:bg-orange-950/60 text-orange-600 dark:text-orange-400 rounded-2xl">
              <GraduationCap size={22} />
            </div>
            <div>
              <h1 className="text-xl font-black text-stone-900 dark:text-white uppercase italic tracking-tight">
                Data Konsentrasi Keahlian / Jurusan
              </h1>
              <p className="text-[10px] font-bold text-stone-500 dark:text-stone-400 uppercase tracking-widest">
                Total Terdaftar: {majors.length} Jurusan
              </p>
            </div>
          </div>

          <M3Button 
            variant="filled"
            size="sm"
            onClick={handleSyncMajors} 
            loading={syncing}
            icon={RefreshCw}
            iconPosition="left"
            className="shadow-md shadow-orange-600/20"
          >
            Tarik Data Jurusan
          </M3Button>
        </header>

        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-6">
          
          {/* M3 Master Data Truth Banner */}
          <M3Card variant="filled" className="bg-orange-50/80 dark:bg-orange-950/30 border border-orange-200/80 dark:border-orange-900/40 p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="p-2.5 bg-orange-600 text-white rounded-2xl shrink-0 shadow-md shadow-orange-600/20">
                <ShieldCheck size={22} />
              </div>
              <div>
                <h4 className="text-xs font-black uppercase tracking-wider text-stone-900 dark:text-white flex items-center gap-2">
                  <span>Single Source of Truth: data.smkn1rongga.sch.id</span>
                  <M3Badge variant="success" size="sm">SYNCED REPLICA</M3Badge>
                </h4>
                <p className="text-[11px] text-stone-600 dark:text-stone-400 mt-0.5 font-medium">
                  Daftar Program & Konsentrasi Keahlian resmi SMKN 1 Rongga disinkronkan otomatis dari Master Data Sekolah.
                </p>
              </div>
            </div>
            <a 
              href="https://data.smkn1rongga.sch.id" 
              target="_blank" 
              rel="noopener noreferrer"
              className="shrink-0 text-xs font-black uppercase text-orange-600 dark:text-orange-400 hover:text-orange-700 bg-white dark:bg-stone-800 px-4 py-2 rounded-full border border-orange-200 dark:border-stone-700 shadow-xs flex items-center gap-1.5 transition"
            >
              <Database size={14} /> Kelola di Pusat
            </a>
          </M3Card>

          {/* M3 Majors Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {loading ? (
              <div className="col-span-full p-12 text-center text-stone-400 font-bold uppercase tracking-wider animate-pulse">
                Memuat data jurusan...
              </div>
            ) : majors.length === 0 ? (
              <div className="col-span-full p-12 text-center text-stone-400 italic">
                Belum ada data jurusan tersimpan.
              </div>
            ) : (
              majors.map(m => (
                <M3Card 
                  key={m.id} 
                  variant="elevated" 
                  className="p-6 border border-stone-200 dark:border-stone-800 hover:border-orange-500/50 transition-all flex items-center justify-between"
                >
                  <div>
                    <span className="px-2.5 py-0.5 rounded-full bg-orange-100 dark:bg-orange-950/60 text-orange-600 dark:text-orange-300 text-[10px] font-black uppercase tracking-widest block w-fit mb-2">
                      Kode: {m.code}
                    </span>
                    <h3 className="text-xl font-black text-stone-900 dark:text-white uppercase italic">
                      {m.name}
                    </h3>
                  </div>
                  <div className="p-3 bg-stone-100 dark:bg-stone-800 text-stone-600 dark:text-stone-400 rounded-2xl">
                    <GraduationCap size={28} />
                  </div>
                </M3Card>
              ))
            )}
          </div>

        </main>
      </div>
    </div>
  );
};

export default MasterMajors;
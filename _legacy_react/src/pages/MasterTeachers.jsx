import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { 
  UserCheck, Search, ShieldCheck, Database, RefreshCw, Download, Mail, Briefcase 
} from 'lucide-react';
import Swal from 'sweetalert2';
import * as XLSX from 'xlsx';
import { masterDataSyncService } from '../services/masterDataSync';
import M3Button from '../components/ui/M3Button';
import M3Card from '../components/ui/M3Card';
import M3Badge from '../components/ui/M3Badge';

const MasterTeachers = () => {
  const [teachers, setTeachers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => { 
    fetchTeachers(); 
  }, []);

  const fetchTeachers = async () => {
    setLoading(true);
    const { data, error } = await supabase.from('teachers').select('*').order('full_name');
    if (!error) setTeachers(data || []);
    setLoading(false);
  };

  const handleSyncTeachers = async () => {
    setSyncing(true);
    Swal.fire({
      title: 'Menyinkronkan Data Guru...',
      text: 'Menghubungkan ke data.smkn1rongga.sch.id/v1/staff...',
      allowOutsideClick: false,
      didOpen: () => Swal.showLoading()
    });

    const res = await masterDataSyncService.syncTeachers();
    setSyncing(false);

    if (res.success) {
      await fetchTeachers();
      Swal.fire('Berhasil!', `Data ${res.count} Guru & GTK tersinkronisasi.`, 'success');
    } else {
      Swal.fire('Gagal!', res.error, 'error');
    }
  };

  const exportTeacherAccounts = () => {
    const dataToExport = filteredTeachers.map((t, idx) => ({
      No: idx + 1,
      Nama: t.full_name || '-',
      NIP: t.nip || '-',
      Email: t.email || '-',
      Role: (t.role_level || t.role || 'guru').toUpperCase()
    }));

    if (dataToExport.length === 0) {
      Swal.fire('Tidak ada data', 'Belum ada data guru yang bisa diexport.', 'info');
      return;
    }

    const worksheet = XLSX.utils.json_to_sheet(dataToExport);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Data Guru CBT");
    XLSX.writeFile(workbook, "Data_Guru_CBT_Jingga.xlsx");
  };

  const filteredTeachers = teachers.filter(t => 
    (t.full_name || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (t.email || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
    (t.nip || '').includes(searchTerm)
  );

  return (
    <div className="flex h-screen bg-stone-50 dark:bg-stone-950 font-sans text-left transition-colors duration-300">
      <Sidebar />
      <div className="flex-1 lg:ml-64 flex flex-col overflow-hidden">
        
        {/* M3 Header */}
        <header className="bg-white/90 dark:bg-stone-900/90 backdrop-blur-md border-b border-stone-200 dark:border-stone-800 p-4 lg:p-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 z-10">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-orange-100 dark:bg-orange-950/60 text-orange-600 dark:text-orange-400 rounded-2xl">
              <UserCheck size={22} />
            </div>
            <div>
              <h1 className="text-xl font-black text-stone-900 dark:text-white uppercase italic tracking-tight">
                Data Guru & Pembuat Soal
              </h1>
              <p className="text-[10px] font-bold text-stone-500 dark:text-stone-400 uppercase tracking-widest">
                Total Terdaftar: {teachers.length} Guru / GTK
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            <M3Button 
              variant="outlined"
              size="sm"
              onClick={exportTeacherAccounts} 
              icon={Download}
              iconPosition="left"
              className="flex-1 sm:flex-none"
            >
              Export Excel
            </M3Button>

            <M3Button 
              variant="filled"
              size="sm"
              onClick={handleSyncTeachers} 
              loading={syncing}
              icon={RefreshCw}
              iconPosition="left"
              className="flex-1 sm:flex-none shadow-md shadow-orange-600/20"
            >
              Tarik Data Guru
            </M3Button>
          </div>
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
                  Seluruh akun PTK terhubung ke Keycloak SSO. Data NIP, Nama, dan Hak Akses otomatis terbarui saat sinkronisasi.
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

          {/* M3 Search Bar */}
          <M3Card variant="elevated" className="p-4 border border-stone-200 dark:border-stone-800 flex items-center">
            <div className="relative w-full">
              <Search className="absolute left-4 top-3 text-stone-400" size={18}/>
              <input 
                type="text" 
                placeholder="Cari Nama Guru, NIP, atau Email..." 
                value={searchTerm} 
                onChange={(e) => setSearchTerm(e.target.value)} 
                className="w-full pl-11 pr-4 py-2 bg-stone-100 dark:bg-stone-800 rounded-full text-xs font-bold text-stone-900 dark:text-white border-0 outline-none focus:ring-2 focus:ring-orange-500 transition-all placeholder:text-stone-400"
              />
            </div>
          </M3Card>

          {/* M3 Teachers Table Surface */}
          <M3Card variant="elevated" className="border border-stone-200 dark:border-stone-800 overflow-hidden m3-elevation-1">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-stone-200 dark:border-stone-800 text-[10px] font-black uppercase tracking-widest text-stone-500 dark:text-stone-400 bg-stone-100/60 dark:bg-stone-900/60">
                    <th className="p-4 pl-6">No</th>
                    <th className="p-4">Nama Lengkap</th>
                    <th className="p-4">NIP</th>
                    <th className="p-4">Email SSO</th>
                    <th className="p-4 pr-6 text-center">Peran</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100 dark:divide-stone-800 text-xs font-bold text-stone-800 dark:text-stone-300">
                  {loading ? (
                    <tr>
                      <td colSpan="5" className="p-12 text-center text-stone-400 font-bold uppercase tracking-wider animate-pulse">
                        Memuat data guru CBT...
                      </td>
                    </tr>
                  ) : filteredTeachers.length === 0 ? (
                    <tr>
                      <td colSpan="5" className="p-12 text-center text-stone-400 italic">
                        Tidak ada data guru ditemukan.
                      </td>
                    </tr>
                  ) : (
                    filteredTeachers.map((t, idx) => (
                      <tr key={t.id} className="hover:bg-stone-50 dark:hover:bg-stone-800/50 transition-colors">
                        <td className="p-4 pl-6 text-stone-400 font-mono text-[11px]">{idx + 1}</td>
                        <td className="p-4 font-black uppercase text-stone-900 dark:text-white">{t.full_name}</td>
                        <td className="p-4 font-mono font-bold text-stone-500 dark:text-stone-400">{t.nip || '-'}</td>
                        <td className="p-4 font-mono text-[11px] text-stone-500 dark:text-stone-400">{t.email}</td>
                        <td className="p-4 pr-6 text-center">
                          <M3Badge variant={t.role_level === 'admin' ? 'primary' : 'default'} size="sm">
                            {(t.role_level || t.role || 'GURU').toUpperCase()}
                          </M3Badge>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </M3Card>

        </main>
      </div>
    </div>
  );
};

export default MasterTeachers;

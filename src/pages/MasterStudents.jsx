import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { Users, Search, GraduationCap, Download, RefreshCw, ShieldCheck, Database } from 'lucide-react';
import Swal from 'sweetalert2';
import * as XLSX from 'xlsx';
import { masterDataSyncService } from '../services/masterDataSync';
import M3Button from '../components/ui/M3Button';
import M3Card from '../components/ui/M3Card';
import M3Badge from '../components/ui/M3Badge';

const MasterStudents = () => {
  const [students, setStudents] = useState([]);
  const [classes, setClasses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterClass, setFilterClass] = useState(''); 

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
    if (!error) setStudents(data || []);
  };

  const handleSyncDataMaster = async () => {
    setSyncing(true);
    const success = await masterDataSyncService.syncAllMasterData();
    if (success) {
      await fetchInitialData();
    }
    setSyncing(false);
  };

  // Export Data Siswa ke Excel
  const exportToExcel = () => {
    if (filteredStudents.length === 0) return Swal.fire('Kosong', 'Tidak ada data untuk di-export', 'warning');

    const sortedData = [...filteredStudents].sort((a, b) => {
      const classA = a.classes?.name || '';
      const classB = b.classes?.name || '';
      if (classA < classB) return -1;
      if (classA > classB) return 1;
      return a.full_name.localeCompare(b.full_name);
    });

    const dataForExcel = sortedData.map((s, index) => ({
      'No': index + 1,
      'Nama': s.full_name.toUpperCase(),
      'Kelas': s.classes?.name || '-',
      'NIS': s.nis,
      'Email': s.email || `${s.nis}@student.smkn1rongga.sch.id`,
      'Status': s.status || 'aktif'
    }));

    const worksheet = XLSX.utils.json_to_sheet(dataForExcel);
    const workbook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workbook, worksheet, "Data Siswa CBT");

    worksheet['!cols'] = [{wch: 5}, {wch: 35}, {wch: 15}, {wch: 15}, {wch: 30}, {wch: 10}];

    const className = filterClass ? classes.find(c => c.id === filterClass)?.name : "Semua_Kelas";
    XLSX.writeFile(workbook, `Data_Siswa_CBT_${className}.xlsx`);
    
    Swal.fire('Berhasil!', 'Data siswa berhasil di-export ke Excel.', 'success');
  };

  const filteredStudents = students.filter(s => {
    const matchesSearch = (s.full_name || '').toLowerCase().includes(searchTerm.toLowerCase()) || 
                          (s.nis || '').includes(searchTerm);
    const matchesClass = filterClass ? s.class_id === filterClass : true;
    return matchesSearch && matchesClass;
  });

  return (
    <div className="flex h-screen bg-stone-50 dark:bg-stone-950 font-sans text-left transition-colors duration-300">
      <Sidebar />
      <div className="flex-1 lg:ml-64 flex flex-col overflow-hidden">
        
        {/* M3 Header Bar */}
        <header className="bg-white/90 dark:bg-stone-900/90 backdrop-blur-md border-b border-stone-200 dark:border-stone-800 p-4 lg:p-6 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 z-10">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-orange-100 dark:bg-orange-950/60 text-orange-600 dark:text-orange-400 rounded-2xl">
              <Users size={22} />
            </div>
            <div>
              <h1 className="text-xl font-black text-stone-900 dark:text-white uppercase italic tracking-tight">
                Data Siswa Peserta CBT
              </h1>
              <p className="text-[10px] font-bold text-stone-500 dark:text-stone-400 uppercase tracking-widest">
                Total Terdaftar: {students.length} Siswa
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2.5 w-full sm:w-auto">
            <M3Button
              variant="outlined"
              size="sm"
              onClick={exportToExcel}
              icon={Download}
              iconPosition="left"
              className="flex-1 sm:flex-none"
            >
              Export Excel
            </M3Button>

            <M3Button
              variant="filled"
              size="sm"
              onClick={handleSyncDataMaster}
              loading={syncing}
              icon={RefreshCw}
              iconPosition="left"
              className="flex-1 sm:flex-none shadow-md shadow-orange-600/20"
            >
              Tarik Data Master
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
                  <span>Single Source of Truth: data-master.smkn1rongga.sch.id</span>
                  <M3Badge variant="success" size="sm">SYNCED REPLICA</M3Badge>
                </h4>
                <p className="text-[11px] text-stone-600 dark:text-stone-400 mt-0.5 font-medium">
                  Pengelolaan data siswa (tambah, mutasi kelas, ganti nama) dikelola terpusat di Master Data Sekolah & Akun SSO Keycloak. Data di CBT otomatis tersinkron saat penarikan atau saat siswa login.
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

          {/* M3 Search & Filter Card */}
          <M3Card variant="elevated" className="p-4 border border-stone-200 dark:border-stone-800 flex flex-col md:flex-row gap-4 justify-between items-center">
            <div className="relative w-full md:w-96">
              <Search className="absolute left-4 top-3 text-stone-400" size={18}/>
              <input 
                type="text" 
                placeholder="Cari NIS atau Nama Siswa..." 
                value={searchTerm} 
                onChange={(e) => setSearchTerm(e.target.value)} 
                className="w-full pl-11 pr-4 py-2 bg-stone-100 dark:bg-stone-800 rounded-full text-xs font-bold text-stone-900 dark:text-white border-0 outline-none focus:ring-2 focus:ring-orange-500 transition-all placeholder:text-stone-400"
              />
            </div>
            
            <div className="flex items-center gap-3 w-full md:w-auto">
              <GraduationCap size={18} className="text-orange-600 shrink-0"/>
              <select 
                value={filterClass} 
                onChange={(e) => setFilterClass(e.target.value)} 
                className="w-full md:w-64 py-2 px-4 bg-stone-100 dark:bg-stone-800 rounded-full text-xs font-bold text-stone-900 dark:text-white border-0 outline-none focus:ring-2 focus:ring-orange-500 cursor-pointer"
              >
                <option value="">Semua Kelas ({students.length} Siswa)</option>
                {classes.map(c => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
          </M3Card>

          {/* M3 Student Table Surface */}
          <M3Card variant="elevated" className="border border-stone-200 dark:border-stone-800 overflow-hidden m3-elevation-1">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="border-b border-stone-200 dark:border-stone-800 text-[10px] font-black uppercase tracking-widest text-stone-500 dark:text-stone-400 bg-stone-100/60 dark:bg-stone-900/60">
                    <th className="p-4 pl-6">No</th>
                    <th className="p-4">NIS</th>
                    <th className="p-4">Nama Lengkap</th>
                    <th className="p-4">Kelas</th>
                    <th className="p-4">Email SSO</th>
                    <th className="p-4 pr-6 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100 dark:divide-stone-800 text-xs font-bold text-stone-800 dark:text-stone-300">
                  {loading ? (
                    <tr>
                      <td colSpan="6" className="p-12 text-center text-stone-400 font-bold uppercase tracking-wider animate-pulse">
                        Memuat data siswa CBT...
                      </td>
                    </tr>
                  ) : filteredStudents.length === 0 ? (
                    <tr>
                      <td colSpan="6" className="p-12 text-center text-stone-400 italic">
                        Tidak ada data siswa ditemukan.
                      </td>
                    </tr>
                  ) : (
                    filteredStudents.map((s, idx) => (
                      <tr key={s.id} className="hover:bg-stone-50 dark:hover:bg-stone-800/50 transition-colors">
                        <td className="p-4 pl-6 text-stone-400 font-mono text-[11px]">{idx + 1}</td>
                        <td className="p-4 font-mono font-black text-orange-600 dark:text-orange-400">{s.nis}</td>
                        <td className="p-4 font-black uppercase text-stone-900 dark:text-white">{s.full_name}</td>
                        <td className="p-4">
                          <span className="px-2.5 py-1 rounded-full bg-stone-100 dark:bg-stone-800 text-stone-700 dark:text-stone-300 text-[10px] font-black uppercase tracking-wider border border-stone-200 dark:border-stone-700">
                            {s.classes?.name || '-'}
                          </span>
                        </td>
                        <td className="p-4 font-mono text-[11px] text-stone-400">{s.email || `${s.nis}@student.smkn1rongga.sch.id`}</td>
                        <td className="p-4 pr-6 text-center">
                          <M3Badge variant="success" size="sm">
                            {s.status || 'aktif'}
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

export default MasterStudents;
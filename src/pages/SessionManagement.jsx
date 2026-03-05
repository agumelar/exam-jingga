import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { RefreshCw, ShieldCheck, Trash2, Users, Download, Filter, Printer } from 'lucide-react';
import Swal from 'sweetalert2';
import * as XLSX from 'xlsx';

const SessionManagement = () => {
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState({ roomCount: 1, capacity: 36, sessions: 2, levels: [10, 11, 12] });
  const [logistics, setLogistics] = useState([]);
  const [totalActiveStudents, setTotalActiveStudents] = useState(0);
  const [schoolSettings, setSchoolSettings] = useState(null); // State baru untuk setting

  // Filter State
  const [filterRoom, setFilterRoom] = useState('all');
  const [filterSession, setFilterSession] = useState('all');

  useEffect(() => { fetchInitialData(); }, []);

  const fetchInitialData = async () => {
    await fetchCurrentLogistics();
    await fetchSettings(); // Ambil data setting sekolah
    const { count } = await supabase.from('students').select('*', { count: 'exact', head: true }).eq('status', 'aktif');
    setTotalActiveStudents(count || 0);
  };

  const fetchSettings = async () => {
    const { data } = await supabase.from('settings').select('*').single();
    if (data) setSchoolSettings(data);
  };

  const fetchCurrentLogistics = async () => {
    const { data } = await supabase.from('student_logistics').select(`*, students(full_name, nis, classes(name))`);
    setLogistics(data || []);
  };

  // --- FUNGSI CETAK DAFTAR HADIR TERFILTER (SUDAH DISUNTIK SETTINGS) ---
  const printAttendance = () => {
    if (filterRoom === 'all') return Swal.fire('Ops!', 'Pilih ruangan spesifik dulu.', 'warning');
    
    const dataToPrint = filteredLogistics;
    const sessionText = filterSession === 'all' ? 'SEMUA SESI' : filterSession;

    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html>
        <head>
          <title>Absensi - ${filterRoom}</title>
          <style>
            body { font-family: 'Arial', sans-serif; padding: 30px; color: #000; }
            .header { text-align: center; margin-bottom: 20px; border-bottom: 3px double #000; padding-bottom: 10px; }
            .info { margin-bottom: 15px; font-weight: bold; font-size: 14px; text-transform: uppercase; }
            table { width: 100%; border-collapse: collapse; }
            th, td { border: 1px solid #000; padding: 10px; text-align: left; font-size: 11px; }
            th { background: #f0f0f0; text-align: center; }
            .ttd-box { height: 35px; vertical-align: top; padding-top: 5px; font-size: 10px; }
            .footer { margin-top: 40px; display: grid; grid-template-columns: 1fr 1fr; gap: 50px; text-align: center; font-size: 13px; }
          </style>
        </head>
        <body>
          <div class="header">
            <h2 style="margin:0; text-transform: uppercase;">${schoolSettings?.school_name || 'NAMA SEKOLAH BELUM DISET'}</h2>
            <p style="margin:5px; font-weight: bold; text-transform: uppercase;">
                DAFTAR HADIR ${schoolSettings?.exam_name || 'UJIAN'} - SEMESTER ${schoolSettings?.semester || ''}
            </p>
            <p style="margin:5px">TAHUN PELAJARAN ${schoolSettings?.academic_year || '..../....'}</p>
          </div>
          <div class="info">
            RUANGAN: ${filterRoom} &nbsp;&nbsp; | &nbsp;&nbsp; SESI: ${sessionText}
          </div>
          <table>
            <thead>
              <tr>
                <th width="30">NO</th>
                <th>NAMA LENGKAP SISWA</th>
                <th width="80">NIS</th>
                <th width="100">KELAS</th>
                <th width="180">TANDA TANGAN</th>
              </tr>
            </thead>
            <tbody>
              ${dataToPrint.map((s, i) => `
                <tr>
                  <td align="center">${i + 1}</td>
                  <td style="text-transform:uppercase"><b>${s.students.full_name}</b></td>
                  <td align="center">${s.students.nis}</td>
                  <td align="center">${s.students.classes.name}</td>
                  <td class="ttd-box">${i + 1}. ...........................</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
          <div class="footer">
            <div><br>Ketua Panitia,<br><br><br><br><b>( ${schoolSettings?.committee_chairman || '............................'} )</b></div>
            <div>Kab. Bandung Barat, ___________<br>Pengawas Ruang,<br><br><br><br>( ............................ )</div>
          </div>
          <script>window.print();</script>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  const handleGenerate = async () => {
    if (config.levels.length === 0) return Swal.fire('Ops!', 'Pilih minimal satu jenjang.', 'warning');
    setLoading(true);
    try {
      let { data: allStudents } = await supabase.from('students').select(`id, full_name, classes(name)`).eq('status', 'aktif');
      allStudents = allStudents.filter(s => config.levels.includes(parseInt(s.classes.name.split(' ')[0])));
      
      const shuffled = [...allStudents].sort(() => Math.random() - 0.5);
      const results = [];
      let studentIdx = 0;

      for (let s = 1; s <= config.sessions; s++) {
        for (let r = 1; r <= config.roomCount; r++) {
          for (let c = 1; c <= config.capacity; c++) {
            if (studentIdx < shuffled.length) {
              results.push({
                student_id: shuffled[studentIdx].id,
                room_name: `RUANG ${r.toString().padStart(2, '0')}`,
                session_name: `SESI ${s}`,
              });
              studentIdx++;
            }
          }
        }
      }
      await supabase.from('student_logistics').delete().neq('room_name', '');
      await supabase.from('student_logistics').insert(results);
      Swal.fire('Berhasil!', `Berhasil mengocok ${results.length} siswa.`, 'success');
      fetchCurrentLogistics();
    } catch (err) { Swal.fire('Gagal!', err.message, 'error'); } 
    finally { setLoading(false); }
  };

  const exportExcel = () => {
    const data = filteredLogistics.map((l, idx) => ({
      'No': idx + 1, 'Nama': l.students?.full_name?.toUpperCase(), 'NIS': l.students?.nis, 'Kelas': l.students?.classes?.name, 'Ruangan': l.room_name, 'Sesi': l.session_name
    }));
    const ws = XLSX.utils.json_to_sheet(data);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, "Logistik");
    XLSX.writeFile(wb, `Logistik_${filterRoom}_${filterSession}.xlsx`);
  };

  const filteredLogistics = logistics.filter(l => {
    const matchRoom = filterRoom === 'all' || l.room_name === filterRoom;
    const matchSession = filterSession === 'all' || l.session_name === filterSession;
    return matchRoom && matchSession;
  });

  const unassignedCount = totalActiveStudents - logistics.length;

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex font-sans text-left text-slate-900 dark:text-zinc-100 transition-colors duration-300">
      <Sidebar role="admin" />
      <main className="flex-1 lg:ml-64 p-4 lg:p-8">
        <header className="mb-8 flex flex-col md:flex-row justify-between items-start md:items-end gap-4">
          <div className="text-left">
            <h2 className="text-4xl font-black italic uppercase tracking-tighter">Session Manager</h2>
            <p className="text-orange-600 font-bold text-[10px] uppercase tracking-[0.3em] mt-1">Otomatisasi Penempatan Ruang & Sesi Ujian</p>
          </div>
          <button onClick={exportExcel} className="bg-emerald-600 text-white px-6 py-3 rounded-2xl font-black text-[10px] uppercase tracking-widest shadow-lg hover:bg-emerald-700 transition-all flex items-center gap-2">
            <Download size={16}/> Export Excel
          </button>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border-b-4 border-blue-500 shadow-sm">
            <p className="text-[10px] font-black uppercase text-zinc-500 mb-1">Peserta Aktif</p>
            <h4 className="text-3xl font-black">{totalActiveStudents}</h4>
          </div>
          <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border-b-4 border-emerald-500 shadow-sm">
            <p className="text-[10px] font-black uppercase text-zinc-500 mb-1">Teralokasi</p>
            <h4 className="text-3xl font-black text-emerald-600">{logistics.length}</h4>
          </div>
          <div className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border-b-4 border-red-500 shadow-sm">
            <p className="text-[10px] font-black uppercase text-zinc-500 mb-1">Belum Terbagi</p>
            <h4 className={`text-3xl font-black ${unassignedCount > 0 ? 'text-red-500' : 'text-zinc-300'}`}>{unassignedCount}</h4>
          </div>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
          <div className="bg-white dark:bg-zinc-900 p-8 rounded-[2.5rem] shadow-sm border border-zinc-200 dark:border-zinc-800 h-fit text-left">
            <h3 className="font-black uppercase italic text-xs mb-8 flex items-center gap-2 text-zinc-400">
              <RefreshCw size={16} /> Konfigurasi Acakan
            </h3>
            <div className="space-y-6">
              <div>
                <label className="text-[10px] font-black uppercase mb-3 block opacity-60">Jenjang Peserta</label>
                <div className="flex gap-2">
                  {[10, 11, 12].map(l => (
                    <button key={l} onClick={() => { const nl = config.levels.includes(l) ? config.levels.filter(x => x !== l) : [...config.levels, l]; setConfig({...config, levels: nl})}} 
                    className={`flex-1 py-4 rounded-2xl font-black text-xs transition-all ${config.levels.includes(l) ? 'bg-orange-600 text-white shadow-lg' : 'bg-zinc-100 dark:bg-zinc-800 text-zinc-500'}`}>KLS {l}</button>
                  ))}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 text-left">
                <div>
                  <label className="text-[10px] font-black uppercase mb-2 block opacity-60">Jml Ruang</label>
                  <input type="number" className="w-full bg-zinc-100 dark:bg-zinc-800 p-4 rounded-xl font-black outline-none focus:ring-2 focus:ring-orange-500" value={config.roomCount} onChange={(e) => setConfig({...config, roomCount: parseInt(e.target.value)})} />
                </div>
                <div>
                  <label className="text-[10px] font-black uppercase mb-2 block opacity-60">Kapasitas</label>
                  <input type="number" className="w-full bg-zinc-100 dark:bg-zinc-800 p-4 rounded-xl font-black outline-none focus:ring-2 focus:ring-orange-500" value={config.capacity} onChange={(e) => setConfig({...config, capacity: parseInt(e.target.value)})} />
                </div>
              </div>
              <button onClick={handleGenerate} disabled={loading} className="w-full bg-zinc-900 dark:bg-white dark:text-black text-white py-5 rounded-2xl font-black uppercase tracking-widest shadow-xl hover:scale-[1.01] transition-all disabled:opacity-50">
                {loading ? 'MENGOCOK...' : 'GENERATE SEKARANG'}
              </button>
            </div>
          </div>

          <div className="xl:col-span-2 bg-white dark:bg-zinc-900 rounded-[2.5rem] border border-zinc-200 dark:border-zinc-800 overflow-hidden shadow-sm flex flex-col text-left">
            <div className="p-6 border-b dark:border-zinc-800 flex flex-wrap justify-between items-center gap-4 text-left">
              <h3 className="font-black text-[10px] uppercase tracking-widest text-zinc-400 flex items-center gap-2"><Filter size={14}/> Filter Logistik</h3>
              
              <div className="flex flex-wrap gap-2 w-full md:w-auto">
                <select className="bg-zinc-100 dark:bg-zinc-800 p-3 rounded-xl font-black text-[10px] uppercase outline-none min-w-[120px]" value={filterRoom} onChange={(e) => setFilterRoom(e.target.value)}>
                  <option value="all">Semua Ruang</option>
                  {[...new Set(logistics.map(l => l.room_name))].sort().map(rm => <option key={rm} value={rm}>{rm}</option>)}
                </select>

                <select className="bg-zinc-100 dark:bg-zinc-800 p-3 rounded-xl font-black text-[10px] uppercase outline-none min-w-[120px]" value={filterSession} onChange={(e) => setFilterSession(e.target.value)}>
                  <option value="all">Semua Sesi</option>
                  <option value="SESI 1">Sesi 1</option>
                  <option value="SESI 2">Sesi 2</option>
                  <option value="SESI 3">Sesi 3</option>
                </select>

                {filterRoom !== 'all' && (
                  <button onClick={printAttendance} className="bg-orange-600 text-white px-4 py-3 rounded-xl font-black text-[10px] uppercase flex items-center gap-2 hover:bg-orange-700 shadow-md transition-all active:scale-95">
                    <Printer size={16}/> Print Absen
                  </button>
                )}
              </div>
            </div>

            <div className="overflow-x-auto max-h-[500px]">
              <table className="w-full text-left">
                <thead className="bg-zinc-50 dark:bg-zinc-800/50 sticky top-0 z-10 text-left">
                  <tr className="text-zinc-400 text-[9px] font-black uppercase tracking-[0.2em]">
                    <th className="p-5 text-left">Nama Siswa</th>
                    <th className="p-5 text-center">Kelas</th>
                    <th className="p-5 text-center">Ruang</th>
                    <th className="p-5 text-center">Sesi</th>
                  </tr>
                </thead>
                <tbody className="divide-y dark:divide-zinc-800">
                  {filteredLogistics.map(l => (
                    <tr key={l.id} className="transition-colors">
                      <td className="p-5">
                        <p className="font-black text-sm uppercase leading-none mb-1">{l.students?.full_name}</p>
                        <p className="text-[10px] font-mono text-zinc-500">{l.students?.nis}</p>
                      </td>
                      <td className="p-5 text-center">
                        <span className="text-[10px] font-black px-2 py-1 bg-zinc-100 dark:bg-zinc-800 rounded-md text-zinc-500 uppercase">{l.students?.classes?.name}</span>
                      </td>
                      <td className="p-5 text-center font-black text-blue-500 text-xs italic">{l.room_name}</td>
                      <td className="p-5 text-center">
                        <span className="bg-orange-600/10 text-orange-600 px-3 py-1 rounded-lg font-black text-[10px] uppercase border border-orange-600/20">{l.session_name}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default SessionManagement;
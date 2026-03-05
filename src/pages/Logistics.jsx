import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { Users, Printer, ShieldCheck, MapPin, Clock, Search } from 'lucide-react';
import Swal from 'sweetalert2';

const Logistics = () => {
  const [classes, setClasses] = useState([]);
  const [selectedClass, setSelectedClass] = useState('');
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [userRole, setUserRole] = useState('');
  const [sessionData, setSessionData] = useState({ session_no: 1, room_name: '' });

  useEffect(() => {
    const userSession = localStorage.getItem('user_session');
    if (userSession) {
      const userData = JSON.parse(userSession);
      setUserRole(userData.role?.toLowerCase() || '');
    }
    fetchClasses();
  }, []);

  const fetchClasses = async () => {
    const { data } = await supabase.from('classes').select('*').order('name');
    setClasses(data || []);
  };

  const fetchStudents = async (classId) => {
    if (!classId) return;
    setLoading(true);
    const { data } = await supabase
      .from('students')
      .select('*')
      .eq('class_id', classId)
      .order('full_name');
    setStudents(data || []);
    setLoading(false);
  };

  const printCards = async () => {
    if (students.length === 0) return Swal.fire('Gagal', 'Pilih kelas yang ada siswanya dulu bro.', 'error');

    const { value: type } = await Swal.fire({
      title: 'Pilih Format Kartu',
      input: 'select',
      inputOptions: {
        'simple': 'UH & PTS (Hanya Akun)',
        'full': 'PAS, PAT & SAJ (Akun + Sesi + Ruang)'
      },
      inputPlaceholder: 'Pilih jenis ujian',
      showCancelButton: true,
      confirmButtonColor: '#f97316',
      confirmButtonText: 'Lanjut Cetak'
    });

    if (!type) return;

    const className = classes.find(c => c.id === selectedClass)?.name || '';
    const printWindow = window.open('', '_blank');
    
    printWindow.document.write(`
      <html>
        <head>
          <title>Cetak Kartu - ${className}</title>
          <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');
            body { font-family: 'Inter', sans-serif; padding: 10px; background: #fff; }
            .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }
            .card { 
              border: 2px solid #000; 
              padding: 15px; 
              border-radius: 12px; 
              display: flex;
              flex-direction: column;
              min-height: 200px;
              page-break-inside: avoid;
            }
            .header { 
              border-bottom: 2px solid #000; 
              margin-bottom: 12px; 
              padding-bottom: 8px; 
              text-align: center;
            }
            .header h2 { margin: 0; font-size: 14px; font-weight: 900; text-transform: uppercase; }
            .header small { font-size: 10px; font-weight: 700; color: #666; }
            .info { font-size: 11px; flex-grow: 1; }
            .info div { display: flex; margin-bottom: 5px; border-bottom: 1px solid #f1f5f9; padding-bottom: 3px; }
            .info b { width: 100px; text-transform: uppercase; color: #475569; }
            .logistics-box { 
              margin-top: 10px; 
              padding: 10px; 
              background: #f8fafc; 
              border: 1px solid #e2e8f0; 
              border-radius: 8px;
              display: grid;
              grid-template-columns: 1fr 1fr;
              gap: 10px;
            }
            .logistics-item { text-align: center; }
            .logistics-item small { font-size: 8px; font-weight: 800; color: #94a3b8; text-transform: uppercase; display: block; }
            .logistics-item p { margin: 0; font-size: 11px; font-weight: 900; color: #0f172a; }
            .footer { 
              margin-top: 12px; 
              font-size: 9px; 
              font-weight: 900; 
              text-align: center; 
              color: #f97316;
              text-transform: uppercase;
              border-top: 1px dashed #cbd5e1;
              padding-top: 8px;
            }
            @media print {
              body { padding: 0; }
              .card { border-width: 1px; }
            }
          </style>
        </head>
        <body>
          <div class="grid">
            ${students.map(s => `
              <div class="card">
                <div class="header">
                  <h2>KARTU LOGIN SISWA</h2>
                  <small>SMK NEGERI PERDANA JINGGA</small>
                </div>
                <div class="info">
                  <div><b>Nama Lengkap</b> : ${s.full_name}</div>
                  <div><b>NIS / User</b> : ${s.nis}</div>
                  <div><b>Password</b> : ${s.password_plain || '********'}</div>
                  <div><b>Kelas</b> : ${className}</div>
                  
                  ${type === 'full' ? `
                  <div class="logistics-box">
                    <div class="logistics-item">
                      <small>Ruangan Ujian</small>
                      <p>${sessionData.room_name || 'BELUM DIATUR'}</p>
                    </div>
                    <div class="logistics-item">
                      <small>Sesi</small>
                      <p>Sesi ${sessionData.session_no}</p>
                    </div>
                  </div>
                  ` : ''}
                </div>
                <div class="footer">
                  ${type === 'full' ? 'Valid untuk PAS / PAT / SAJ' : 'Valid untuk UH & PTS'}
                </div>
              </div>
            `).join('')}
          </div>
          <script>
            window.onload = () => { window.print(); window.close(); };
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex font-sans text-left">
      <Sidebar role={userRole} />
      <main className="flex-1 lg:ml-64 p-4 lg:p-8">
        <header className="mb-8">
          <h2 className="text-3xl font-black italic uppercase tracking-tighter">Logistik & Kartu</h2>
          <p className="text-slate-400 font-bold text-xs uppercase tracking-widest">Cetak Kredensial & Atur Sesi Ruangan Siswa</p>
        </header>

        <div className="bg-white dark:bg-zinc-900 p-8 rounded-[3rem] shadow-sm border border-slate-100 dark:border-zinc-800 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-end">
            <div className="space-y-2 text-left">
              <label className="text-[10px] font-black uppercase text-slate-400 ml-2">Pilih Target Kelas</label>
              <select 
                className="w-full bg-slate-50 dark:bg-zinc-800 p-4 rounded-2xl font-bold border-none text-slate-900 dark:text-white"
                value={selectedClass}
                onChange={(e) => { setSelectedClass(e.target.value); fetchStudents(e.target.value); }}
              >
                <option value="">-- Pilih Kelas --</option>
                {classes.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            
            <div className="space-y-2 text-left">
              <label className="text-[10px] font-black uppercase text-slate-400 ml-2">Sesi (Hanya untuk PAS/PAT)</label>
              <select 
                className="w-full bg-slate-50 dark:bg-zinc-800 p-4 rounded-2xl font-bold border-none text-slate-900 dark:text-white"
                value={sessionData.session_no}
                onChange={(e) => setSessionData({...sessionData, session_no: e.target.value})}
              >
                <option value="1">Sesi 1</option>
                <option value="2">Sesi 2</option>
                <option value="3">Sesi 3</option>
              </select>
            </div>

            <div className="space-y-2 text-left">
              <label className="text-[10px] font-black uppercase text-slate-400 ml-2">Nama Ruangan / Lab</label>
              <input 
                className="w-full bg-slate-50 dark:bg-zinc-800 p-4 rounded-2xl font-bold border-none text-slate-900 dark:text-white"
                placeholder="Contoh: Lab Komputer 1"
                value={sessionData.room_name}
                onChange={(e) => setSessionData({...sessionData, room_name: e.target.value})}
              />
            </div>
          </div>
          
          <div className="mt-8 flex flex-col md:flex-row gap-4">
            <button 
              onClick={printCards} 
              disabled={students.length === 0}
              className="bg-orange-600 text-white px-10 py-4 rounded-2xl font-black text-xs uppercase tracking-widest flex items-center justify-center gap-3 shadow-lg hover:scale-105 transition-all disabled:opacity-50"
            >
              <Printer size={18}/> Cetak Kartu Login
            </button>
          </div>
        </div>

        {/* Preview List */}
        <div className="bg-white dark:bg-zinc-900 rounded-[2.5rem] border border-slate-100 dark:border-zinc-800 overflow-hidden">
          <div className="p-6 border-b dark:border-zinc-800 flex justify-between items-center">
            <h3 className="font-black text-xs uppercase tracking-widest flex items-center gap-2"><Users size={16} className="text-orange-600"/> Daftar Siswa ({students.length})</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-slate-50 dark:bg-zinc-800/50">
                  <th className="p-6 text-[10px] font-black uppercase text-slate-400">Nama Lengkap</th>
                  <th className="p-6 text-[10px] font-black uppercase text-slate-400">NIS / Username</th>
                  <th className="p-6 text-[10px] font-black uppercase text-slate-400">Password Plain</th>
                </tr>
              </thead>
              <tbody className="divide-y dark:divide-zinc-800">
                {students.length > 0 ? students.map(s => (
                  <tr key={s.id} className="hover:bg-slate-50/50 dark:hover:bg-zinc-800/30 transition-colors">
                    <td className="p-6 font-bold text-slate-700 dark:text-zinc-200">{s.full_name}</td>
                    <td className="p-6 font-mono font-bold text-orange-600">{s.nis}</td>
                    <td className="p-6 font-mono text-slate-400 text-sm">{s.password_plain || 'N/A'}</td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan="3" className="p-20 text-center text-slate-300 font-bold italic">Pilih kelas untuk melihat daftar siswa</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </div>
  );
};

export default Logistics;
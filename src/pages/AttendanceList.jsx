import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { Printer, ClipboardList, Loader2, Users } from 'lucide-react'; // <-- Tambah icon Users

const AttendanceList = () => {
  const [students, setStudents] = useState([]);
  const [settings, setSettings] = useState(null);
  const [filterRoom, setFilterRoom] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const { data: logData } = await supabase.from('student_logistics').select(`
        *, 
        students(full_name, nis, password_plain, classes(name))
      `);
      const { data: setData } = await supabase.from('settings').select('*').limit(1);
      
      const sortedData = (logData || []).sort((a, b) => 
        a.students.full_name.localeCompare(b.students.full_name)
      );

      setStudents(sortedData);
      if (setData && setData.length > 0) {
        setSettings(setData[0]);
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  // 1. FUNGSI CETAK DAFTAR HADIR (PENGAWAS / ZIG-ZAG)
  const printAttendance = () => {
    let filtered = students;
    if (filterRoom !== 'all') filtered = filtered.filter(s => s.room_name === filterRoom);

    const groups = {};
    filtered.forEach(s => {
      const key = `${s.room_name}_${s.session_name}`;
      if (!groups[key]) groups[key] = { room: s.room_name, session: s.session_name, students: [] };
      groups[key].students.push(s);
    });

    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html>
        <head>
          <title>Daftar Hadir - ${settings?.school_name}</title>
          <style>
            @page { size: A4 portrait; margin: 15mm; }
            body { font-family: 'Times New Roman', Times, serif; margin: 0; padding: 0; background: #fff; color: #000; }
            .page { page-break-after: always; padding-bottom: 20px; }
            .page:last-child { page-break-after: auto; }
            .header { display: flex; align-items: center; justify-content: space-between; border-bottom: 3pt double #000; padding-bottom: 8px; margin-bottom: 15px; }
            .header-logo { width: 22mm; height: 22mm; object-fit: contain; }
            .header-text { text-align: center; flex: 1; padding: 0 10px; }
            .header-text h4 { margin: 0; font-size: 11pt; font-weight: bold; text-transform: uppercase; line-height: 1.2; }
            .header-text h3 { margin: 3px 0; font-size: 14pt; font-weight: bold; color: #000; }
            .header-text p { margin: 0; font-size: 8pt; font-style: italic; line-height: 1.3; }
            .header-text .info { font-style: normal; }
            .title-area { text-align: center; margin-bottom: 15px; }
            .title-area h2 { margin: 0; font-size: 12pt; text-decoration: underline; text-transform: uppercase; }
            .title-area p { margin: 5px 0 0 0; font-size: 11pt; font-weight: bold; }
            .meta-info { display: flex; justify-content: space-between; margin-bottom: 10px; font-size: 11pt; font-weight: bold; }
            .meta-table td { padding: 3px 0; font-size: 11pt; font-weight: bold; }
            .table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
            .table th, .table td { border: 1pt solid #000; padding: 8px 6px; font-size: 10pt; vertical-align: middle; }
            .table th { background-color: #f0f0f0; text-align: center; font-weight: bold; -webkit-print-color-adjust: exact; }
            .sig-left { border-right: none !important; }
            .sig-right { border-left: none !important; }
            .footer { display: flex; justify-content: space-between; margin-top: 10px; font-size: 11pt; }
            .signature-box { width: 65mm; text-align: center; position: relative; }
            .sig-space { height: 22mm; position: relative; display: flex; justify-content: center; align-items: center; margin: 5px 0; }
            .img-ttd { max-height: 20mm; object-fit: contain; z-index: 2; position: relative; }
          </style>
        </head>
        <body>
          ${Object.values(groups).map((g) => `
            <div class="page">
              <div class="header">
                ${settings?.logo_left_url ? `<img src="${settings.logo_left_url}" class="header-logo" />` : '<div style="width:22mm"></div>'}
                <div class="header-text">
                  ${settings?.header_1 ? `<h4>${settings.header_1}</h4>` : ''}
                  ${settings?.header_2 ? `<h4>${settings.header_2}</h4>` : ''}
                  ${settings?.header_3 ? `<h4>${settings.header_3}</h4>` : ''}
                  <h3>${settings?.school_name || 'NAMA SEKOLAH'}</h3>
                  <p>Program Keahlian: ${settings?.school_majors_list || '-'}</p>
                  <p class="info">Alamat: ${settings?.school_address || '-'} Telp. ${settings?.school_phone || '-'}</p>
                  <p class="info">Website: ${settings?.school_website || '-'} Email: ${settings?.school_email || '-'}</p>
                  <p class="info">${settings?.school_postal_code || '-'}</p>
                </div>
                ${settings?.logo_right_url ? `<img src="${settings.logo_right_url}" class="header-logo" />` : '<div style="width:22mm"></div>'}
              </div>

              <div class="title-area">
                <h2>DAFTAR HADIR  ${settings?.exam_name || 'UJIAN'}</h2>
                <p>TAHUN AJARAN ${settings?.academic_year || '2024/2025'}</p>
              </div>

              <div class="meta-info">
                <table class="meta-table">
                  <tr><td width="120">Mata Pelajaran</td><td>: ...........................................................</td></tr>
                  <tr><td>Hari / Tanggal</td><td>: ...........................................................</td></tr>
                </table>
                <table class="meta-table">
                  <tr><td width="60">Ruang</td><td>: <b>${g.room}</b></td></tr>
                  <tr><td>Sesi</td><td>: <b>${g.session}</b></td></tr>
                </table>
              </div>

              <table class="table">
                <thead>
                  <tr>
                    <th width="5%">No</th>
                    <th width="20%">NIS</th>
                    <th width="35%">Nama Peserta</th>
                    <th colspan="2" width="25%">Tanda Tangan</th>
                    <th width="15%">KET</th>
                  </tr>
                </thead>
                <tbody>
                  ${g.students.map((s, index) => `
                    <tr>
                      <td align="center">${index + 1}</td>
                      <td align="center">${s.students.nis}</td>
                      <td>&nbsp;${s.students.full_name.toUpperCase()}</td>
                      ${index % 2 === 0
                        ? `<td width="12.5%" class="sig-left">&nbsp;${index + 1}.</td><td width="12.5%" class="sig-right"></td>`
                        : `<td width="12.5%" class="sig-left"></td><td width="12.5%" class="sig-right">&nbsp;${index + 1}.</td>`
                      }
                      <td></td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>

              <div class="footer">
                <div class="signature-box">
                  Mengetahui,<br>
                  Wakasek Bidang Kurikulum,
                  <div class="sig-space">
                    ${settings?.curriculum_signature_url ? `<img src="${settings.curriculum_signature_url}" class="img-ttd" />` : ''}
                  </div>
                  <b><u>${settings?.curriculum_vicedir_name || '.......................'}</u></b><br>
                  NIP. ${settings?.curriculum_vicedir_nip || '.......................'}
                </div>
                
                <div class="signature-box">
                  ${settings?.exam_city || '.................'}, .............................. 202..<br>
                  Pengawas Ruangan,
                  <div class="sig-space"></div>
                  <b><u>...................................................</u></b><br>
                  NIP. ..........................................
                </div>
              </div>
            </div>
          `).join('')}
        </body>
      </html>
    `);
    printWindow.document.close();
    setTimeout(() => { printWindow.print(); }, 1000); 
  };

  // 2. FUNGSI CETAK PESERTA RUANGAN (TEMPELAN PINTU)
  const printParticipants = () => {
    let filtered = students;
    if (filterRoom !== 'all') filtered = filtered.filter(s => s.room_name === filterRoom);

    const groups = {};
    filtered.forEach(s => {
      const key = `${s.room_name}_${s.session_name}`;
      if (!groups[key]) groups[key] = { room: s.room_name, session: s.session_name, students: [] };
      groups[key].students.push(s);
    });

    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html>
        <head>
          <title>Daftar Peserta - ${settings?.school_name}</title>
          <style>
            @page { size: A4 portrait; margin: 15mm; }
            body { font-family: 'Times New Roman', Times, serif; margin: 0; padding: 0; background: #fff; color: #000; }
            .page { page-break-after: always; padding-bottom: 20px; }
            .page:last-child { page-break-after: auto; }
            .header { display: flex; align-items: center; justify-content: space-between; border-bottom: 3pt double #000; padding-bottom: 8px; margin-bottom: 15px; }
            .header-logo { width: 22mm; height: 22mm; object-fit: contain; }
            .header-text { text-align: center; flex: 1; padding: 0 10px; }
            .header-text h4 { margin: 0; font-size: 11pt; font-weight: bold; text-transform: uppercase; line-height: 1.2; }
            .header-text h3 { margin: 3px 0; font-size: 14pt; font-weight: bold; color: #000; }
            .header-text p { margin: 0; font-size: 8pt; font-style: italic; line-height: 1.3; }
            .header-text .info { font-style: normal; }
            .title-area { text-align: center; margin-bottom: 15px; }
            .title-area h2 { margin: 0; font-size: 14pt; text-decoration: underline; text-transform: uppercase; font-weight: 900; }
            .title-area p { margin: 5px 0 0 0; font-size: 12pt; font-weight: bold; }
            
            /* Ruang dan Sesi ditengahin biar jelas buat tempelan */
            .meta-info { text-align: center; margin-bottom: 15px; }
            .meta-info span { font-size: 14pt; font-weight: bold; padding: 5px 20px; border: 2pt solid #000; display: inline-block; margin: 0 5px; border-radius: 5px;}
            
            /* Font lebih besar untuk tabel tempelan */
            .table { width: 100%; border-collapse: collapse; margin-bottom: 30px; }
            .table th, .table td { border: 1pt solid #000; padding: 10px 8px; font-size: 12pt; vertical-align: middle; }
            .table th { background-color: #f0f0f0; text-align: center; font-weight: bold; -webkit-print-color-adjust: exact; font-size: 11pt;}
            .student-name { font-weight: bold; font-size: 12pt; }
            .student-nis { font-weight: bold; font-size: 11pt; }
            
            .footer { display: flex; justify-content: space-between; margin-top: 10px; font-size: 11pt; }
            .signature-box { width: 70mm; text-align: center; position: relative; }
            .sig-space { height: 22mm; position: relative; display: flex; justify-content: center; align-items: center; margin: 5px 0; }
            .img-ttd { max-height: 20mm; object-fit: contain; z-index: 2; position: relative; }
            .img-cap { height: 25mm; object-fit: contain; position: absolute; left: 10%; top: -3mm; z-index: 3; opacity: 0.8; mix-blend-mode: multiply; }
          </style>
        </head>
        <body>
          ${Object.values(groups).map((g) => `
            <div class="page">
              <div class="header">
                ${settings?.logo_left_url ? `<img src="${settings.logo_left_url}" class="header-logo" />` : '<div style="width:22mm"></div>'}
                <div class="header-text">
                  ${settings?.header_1 ? `<h4>${settings.header_1}</h4>` : ''}
                  ${settings?.header_2 ? `<h4>${settings.header_2}</h4>` : ''}
                  ${settings?.header_3 ? `<h4>${settings.header_3}</h4>` : ''}
                  <h3>${settings?.school_name || 'NAMA SEKOLAH'}</h3>
                  <p>Program Keahlian: ${settings?.school_majors_list || '-'}</p>
                  <p class="info">Alamat: ${settings?.school_address || '-'} Telp. ${settings?.school_phone || '-'}</p>
                  <p class="info">Website: ${settings?.school_website || '-'} Email: ${settings?.school_email || '-'}</p>
                  <p class="info">${settings?.school_postal_code || '-'}</p>
                </div>
                ${settings?.logo_right_url ? `<img src="${settings.logo_right_url}" class="header-logo" />` : '<div style="width:22mm"></div>'}
              </div>

              <div class="title-area">
                <h2>DAFTAR PESERTA ${settings?.exam_name || 'UJIAN'}</h2>
                <p>TAHUN AJARAN ${settings?.academic_year || '2024/2025'}</p>
              </div>

              <div class="meta-info">
                <span>RUANG : ${g.room}</span>
                <span>SESI : ${g.session}</span>
              </div>

              <table class="table">
                <thead>
                  <tr>
                    <th width="5%">No</th>
                    <th width="20%">NIS</th>
                    <th width="40%">Nama Peserta</th>
                    <th width="20%">Kelas</th>
                    <th width="15%">Keterangan</th>
                  </tr>
                </thead>
                <tbody>
                  ${g.students.map((s, index) => `
                    <tr>
                      <td align="center">${index + 1}</td>
                      <td align="center" class="student-nis">${s.students.nis}</td>
                      <td class="student-name">&nbsp;${s.students.full_name.toUpperCase()}</td>
                      <td align="center">${s.students.classes.name}</td>
                      <td></td>
                    </tr>
                  `).join('')}
                </tbody>
              </table>

              <div class="footer">
                <div class="signature-box">
                  Mengetahui,<br>
                  Kepala Sekolah,
                  <div class="sig-space">
                    ${settings?.headmaster_signature_url ? `<img src="${settings.headmaster_signature_url}" class="img-ttd" />` : ''}
                    ${settings?.school_seal_url ? `<img src="${settings.school_seal_url}" class="img-cap" />` : ''}
                  </div>
                  <b><u>${settings?.headmaster_name || '.......................'}</u></b><br>
                  NIP. ${settings?.headmaster_nip || '.......................'}
                </div>
                
                <div class="signature-box">
                  ${settings?.exam_city || '.................'}, ${settings?.exam_date || '.............................. 202..'}<br>
                  Wakasek Bidang Kurikulum,
                  <div class="sig-space">
                    ${settings?.curriculum_signature_url ? `<img src="${settings.curriculum_signature_url}" class="img-ttd" />` : ''}
                  </div>
                  <b><u>${settings?.curriculum_vicedir_name || '.......................'}</u></b><br>
                  NIP. ${settings?.curriculum_vicedir_nip || '.......................'}
                </div>
              </div>
            </div>
          `).join('')}
        </body>
      </html>
    `);
    printWindow.document.close();
    setTimeout(() => { printWindow.print(); }, 1000); 
  };

  if (loading) return (
    <div className="h-screen flex items-center justify-center bg-zinc-950">
      <Loader2 className="animate-spin text-orange-600" size={48} />
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex font-sans">
      <Sidebar role="admin" />
      <main className="flex-1 lg:ml-64 p-8">
        <header className="mb-8 flex flex-col md:flex-row md:justify-between md:items-end gap-4">
          <div className="text-left">
            <h2 className="text-4xl font-black italic uppercase tracking-tighter text-zinc-900 dark:text-white">Attendance List</h2>
            <p className="text-orange-600 font-bold text-[10px] uppercase tracking-[0.3em] mt-1">Cetak Daftar Hadir & Peserta</p>
          </div>
          
          <div className="flex flex-wrap items-center gap-3">
            <select 
              className="bg-white dark:bg-zinc-900 text-zinc-900 dark:text-white px-4 py-3 rounded-2xl font-bold text-xs border border-zinc-200 dark:border-zinc-700 outline-none focus:ring-2 focus:ring-orange-500 transition-all cursor-pointer shadow-sm"
              onChange={(e) => setFilterRoom(e.target.value)}
            >
              <option value="all">Semua Ruangan</option>
              {[...new Set(students.map(s => s.room_name))].map(r => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
            
            {/* TOMBOL CETAK PESERTA (TEMPELAN PINTU) */}
            <button onClick={printParticipants} className="bg-zinc-800 dark:bg-zinc-100 text-white dark:text-zinc-900 px-6 py-3 rounded-2xl font-black text-[10px] uppercase tracking-widest flex items-center gap-2 shadow-lg hover:opacity-90 transition-all active:scale-95 cursor-pointer">
              <Users size={16} /> Cetak Peserta
            </button>
            
            {/* TOMBOL CETAK DAFTAR HADIR (PENGAWAS) */}
            <button onClick={printAttendance} className="bg-orange-600 text-white px-6 py-3 rounded-2xl font-black text-[10px] uppercase tracking-widest flex items-center gap-2 shadow-lg hover:bg-orange-700 transition-all active:scale-95 cursor-pointer">
              <Printer size={16} /> Daftar Hadir
            </button>
          </div>
        </header>

        <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-3xl p-8 shadow-sm">
          <div className="flex items-center gap-4 mb-6 text-zinc-500">
            <ClipboardList size={32} className="text-orange-600" />
            <div>
              <h3 className="text-lg font-bold text-zinc-900 dark:text-white">Preview Data Siswa</h3>
              <p className="text-xs">Pilih ruangan dan klik salah satu tombol cetak di atas sesuai kebutuhan.</p>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-zinc-200 dark:border-zinc-800 text-xs uppercase tracking-wider text-zinc-500">
                  <th className="p-4 font-bold">Ruang & Sesi</th>
                  <th className="p-4 font-bold">NIS</th>
                  <th className="p-4 font-bold">Nama Lengkap</th>
                  <th className="p-4 font-bold">Kelas</th>
                </tr>
              </thead>
              <tbody>
                {students.filter(s => filterRoom === 'all' || s.room_name === filterRoom).slice(0, 10).map((s, idx) => (
                  <tr key={idx} className="border-b border-zinc-100 dark:border-zinc-800/50 hover:bg-slate-50 dark:hover:bg-zinc-800/50">
                    <td className="p-4">
                      <span className="text-[10px] font-black text-zinc-900 dark:text-white bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 px-3 py-1 rounded-full uppercase italic shadow-sm">
                        {s.room_name} - Sesi {s.session_name}
                      </span>
                    </td>
                    <td className="p-4 font-medium text-sm text-zinc-700 dark:text-zinc-300">{s.students.nis}</td>
                    <td className="p-4 font-bold text-sm text-zinc-900 dark:text-white">{s.students.full_name}</td>
                    <td className="p-4 text-sm text-zinc-500">{s.students.classes.name}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {students.length > 10 && (
              <p className="text-center text-xs text-zinc-500 mt-6 italic">Menampilkan 10 data pertama sebagai preview...</p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export default AttendanceList;
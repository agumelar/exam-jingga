import React, { useEffect, useState } from 'react';
import { supabase } from '../supabaseClient';
import Sidebar from '../components/Sidebar';
import { Printer, QrCode, Loader2 } from 'lucide-react';

const ExamCards = () => {
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
      
      setStudents(logData || []);
      if (setData && setData.length > 0) {
        setSettings(setData[0]);
      }
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const printCards = () => {
    const dataToPrint = filterRoom === 'all' ? students : students.filter(s => s.room_name === filterRoom);
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html>
        <head>
          <title>Cetak Kartu - ${settings?.school_name}</title>
          <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
          <style>
            @page { size: A4; margin: 10mm 5mm; }
            body { font-family: 'Arial', sans-serif; margin: 0; padding: 0; background: #fff; }
            
            .card-container { 
              display: grid; 
              grid-template-columns: 1fr 1fr; 
              gap: 10px; 
              width: 100%;
            }

            .card { 
              width: 95mm; 
              min-height: 65mm; 
              border: 1pt solid #000; 
              padding: 3mm;
              box-sizing: border-box;
              position: relative;
              background: #fff;
              page-break-inside: avoid;
              overflow: hidden;
            }

            .watermark {
              position: absolute;
              top: 55%; left: 50%;
              transform: translate(-50%, -50%);
              width: 35mm;
              opacity: 0.1;
              z-index: 0;
              pointer-events: none;
            }

            .card-content { position: relative; z-index: 1; }

            .header { 
              display: flex;
              align-items: center;
              justify-content: space-between;
              border-bottom: 2pt solid #000;
              padding-bottom: 2px;
              margin-bottom: 4px;
            }
            .header-logo { width: 14mm; height: 14mm; object-fit: contain; }
            .header-text { text-align: center; flex: 1; padding: 0 3px; }
            .header-text h4 { margin: 0; font-size: 5.5pt; font-weight: bold; text-transform: uppercase; line-height: 1.1; }
            .header-text h3 { margin: 1px 0; font-size: 8pt; font-weight: bold; color: #000; }
            .header-text p { margin: 0; font-size: 4.2pt; line-height: 1.2; font-style: italic; }
            .header-text .info { font-style: normal; }

            .title { 
              text-align: center; 
              font-weight: bold; 
              font-size: 7.5pt; 
              margin: 4px 0; 
              text-transform: uppercase; 
              text-decoration: underline;
            }

            .info-table { width: 100%; font-size: 7.5pt; border-collapse: collapse; margin-bottom: 4px; }
            .info-table td { padding: 1.5px 0; vertical-align: top; }
            .label { width: 20mm; font-weight: normal; }

            .footer { 
              display: flex; 
              justify-content: space-between; 
              align-items: flex-end; 
              margin-top: 5px;
            }
            .photo-box { 
              width: 18mm; height: 24mm; 
              border: 1pt solid #000; 
              display: flex; align-items: center; justify-content: center; 
              font-size: 6pt; background: #eee;
            }
            
            .qr-box { width: 15mm; height: 15mm; }

            .signature-area { 
              position: relative;
              text-align: center; 
              font-size: 6.5pt; 
              width: 42mm;
            }
            .sig-space { height: 12mm; position: relative; }
            
            .img-ttd { height: 12mm; object-fit: contain; position: absolute; left: 50%; transform: translateX(-50%); z-index: 2; }
            .img-cap { 
              height: 15mm; 
              object-fit: contain; 
              position: absolute; 
              left: 5%; 
              top: -2mm; 
              z-index: 3; 
              opacity: 0.8;
              mix-blend-mode: multiply;
            }
          </style>
        </head>
        <body>
          <div class="card-container">
            ${dataToPrint.map((s, index) => `
              <div class="card">
                ${settings?.watermark_url ? `<img src="${settings.watermark_url}" class="watermark" />` : ''}
                <div class="card-content">
                  <div class="header">
                    ${settings?.logo_left_url ? `<img src="${settings.logo_left_url}" class="header-logo" />` : '<div style="width:14mm"></div>'}
                    <div class="header-text">
                      ${settings?.header_1 ? `<h4>${settings.header_1}</h4>` : ''}
                      ${settings?.header_2 ? `<h4>${settings.header_2}</h4>` : ''}
                      ${settings?.header_3 ? `<h4>${settings.header_3}</h4>` : ''}
                      <h3>${settings?.school_name || 'NAMA SEKOLAH'}</h3>
                      <p>Program Keahlian: ${settings?.school_majors_list || '-'}</p>
                      <p class="info">alamat ${settings?.school_address || '-'} Telp. ${settings?.school_phone || '-'}</p>
                      <p class="info">Website: ${settings?.school_website || '-'} Email: ${settings?.school_email || '-'}</p>
                      <p class="info">${settings?.school_postal_code || '-'}</p>
                    </div>
                    ${settings?.logo_right_url ? `<img src="${settings.logo_right_url}" class="header-logo" />` : '<div style="width:14mm"></div>'}
                  </div>
                  
                  <div class="title">KARTU PESERTA ${settings?.exam_name || 'UJIAN'}<br>TAHUN ${settings?.academic_year || '2024/2025'}</div>

                  <table class="info-table">
                    <tr><td class="label">NIS</td><td>: ${s.students.nis}</td></tr>
                    <tr><td class="label">Password</td><td>: <b>${s.students.password_plain}</b></td></tr>
                    <tr><td class="label">Nama</td><td>: <b>${s.students.full_name.toUpperCase()}</b></td></tr>
                    <tr><td class="label">Kelas</td><td>: ${s.students.classes.name}</td></tr>
                    <tr><td class="label">Ruang / Sesi</td><td>: ${s.room_name} / ${s.session_name}</td></tr>
                  </table>

                  <div class="footer">
                    <div class="photo-box">FOTO 3X4</div>
                    <div id="qrcode-${index}" class="qr-box"></div>
                    <div class="signature-area">
                      ${settings?.exam_city || 'Kota'}, ${settings?.exam_date || 'Tanggal Titimangsa'}<br>
                      Kepala Sekolah,
                      <div class="sig-space">
                        ${settings?.headmaster_signature_url ? `<img src="${settings.headmaster_signature_url}" class="img-ttd" />` : ''}
                        ${settings?.school_seal_url ? `<img src="${settings.school_seal_url}" class="img-cap" />` : ''}
                      </div>
                      <b>${settings?.headmaster_name || '.......................'}</b><br>
                      NIP. ${settings?.headmaster_nip || '.......................'}
                    </div>
                  </div>
                </div>
              </div>
            `).join('')}
          </div>
          <script>
            ${dataToPrint.map((s, index) => `
              new QRCode(document.getElementById("qrcode-${index}"), {
                text: "${s.students.nis}",
                width: 50,
                height: 50
              });
            `).join('')}
            setTimeout(() => { window.print(); }, 1200);
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
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
        <header className="mb-8 flex justify-between items-end">
          <div className="text-left">
            <h2 className="text-4xl font-black italic uppercase tracking-tighter text-zinc-900 dark:text-white">Print Cards</h2>
            <p className="text-orange-600 font-bold text-[10px] uppercase tracking-[0.3em] mt-1">Ready for {settings?.academic_year}</p>
          </div>
          
          <div className="flex gap-4">
            {/* PERBAIKAN 1: Filter Dropdown sekarang pakai text-zinc-900 dark:text-white */}
            <select 
              className="bg-white dark:bg-zinc-900 text-zinc-900 dark:text-white px-4 py-2 rounded-xl font-bold text-xs border border-zinc-200 dark:border-zinc-700 outline-none focus:ring-2 focus:ring-orange-500 transition-all cursor-pointer"
              onChange={(e) => setFilterRoom(e.target.value)}
            >
              <option value="all">Semua Ruangan</option>
              {[...new Set(students.map(s => s.room_name))].map(r => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
            <button onClick={printCards} className="bg-orange-600 text-white px-8 py-3 rounded-2xl font-black text-[10px] uppercase tracking-widest flex items-center gap-2 shadow-lg hover:bg-orange-700 transition-all active:scale-95 cursor-pointer">
              <Printer size={16} /> Cetak Masal
            </button>
          </div>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {students.filter(s => filterRoom === 'all' || s.room_name === filterRoom).map(s => (
            <div key={s.id} className="bg-white dark:bg-zinc-900 p-6 rounded-[2rem] border border-zinc-200 dark:border-zinc-800 text-left shadow-sm hover:border-orange-500 transition-all group">
              <div className="flex justify-between items-start mb-4">
                <div className="bg-orange-100 dark:bg-orange-900/30 p-2 rounded-lg text-orange-600 group-hover:scale-110 transition-transform">
                  <QrCode size={20} />
                </div>
                {/* PERBAIKAN 2: Keterangan Ruang (Badge) ditambahkan text-zinc-900 dark:text-white dan border */}
                <span className="text-[10px] font-black text-zinc-900 dark:text-white bg-zinc-100 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 px-3 py-1 rounded-full uppercase italic shadow-sm">
                  {s.room_name}
                </span>
              </div>
              <h3 className="font-black text-lg uppercase truncate text-zinc-900 dark:text-white">{s.students.full_name}</h3>
              <p className="text-zinc-500 text-sm font-medium italic">NIS: {s.students.nis} • {s.students.classes.name}</p>
              <div className="mt-4 pt-4 border-t border-dashed border-zinc-200 dark:border-zinc-800 flex justify-between items-center">
                <span className="text-[10px] font-bold text-zinc-400">SESSION {s.session_name}</span>
                <span className="text-[10px] font-bold text-orange-600">READY TO PRINT</span>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
};

export default ExamCards;
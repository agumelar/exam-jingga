import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Users, 
  Sun, 
  Moon, 
  LogOut, 
  Menu, 
  X, 
  Upload, 
  GraduationCap, 
  School, 
  UserCheck, 
  Book, 
  UserPlus, 
  FileText, 
  CalendarDays, 
  LayoutGrid, 
  Settings, 
  CreditCard, 
  ClipboardList,
  Sparkles
} from 'lucide-react';
import { logoutKeycloak } from '../services/keycloakAuth';
import { useAuth } from '../context/AuthContext';
import { isDarkMode, toggleTheme } from '../utils/theme';

const Sidebar = ({ role: propRole }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isDark, setIsDark] = useState(isDarkMode());

  // Ambil role secara otomatis dan tangguh dari context / storage
  let authRole = null;
  try {
    const auth = useAuth();
    authRole = auth?.role;
  } catch (e) {
    // Abaikan jika dipanggil di luar AuthProvider
  }

  let sessionRole = null;
  try {
    const raw = localStorage.getItem('user_session');
    if (raw) {
      const parsed = JSON.parse(raw);
      sessionRole = parsed?.role;
    }
  } catch (e) {}

  const activeRole = String(propRole || authRole || sessionRole || 'admin').toLowerCase();

  useEffect(() => {
    const handleThemeChange = (e) => {
      setIsDark(e.detail.theme === 'dark');
    };
    window.addEventListener('exam-jingga-theme-change', handleThemeChange);
    return () => window.removeEventListener('exam-jingga-theme-change', handleThemeChange);
  }, []);

  const handleToggleTheme = () => {
    const nextDark = toggleTheme();
    setIsDark(nextDark);
  };

  const handleLogout = () => {
    logoutKeycloak();
  };

  const linkStyle = ({ isActive }) => `
    flex items-center gap-3.5 px-4 py-3 rounded-full font-bold text-xs tracking-wide transition-all duration-200 select-none m3-state-layer
    ${isActive 
      ? 'bg-orange-600 text-white font-black shadow-md shadow-orange-600/30' 
      : 'text-stone-400 hover:bg-stone-800/60 hover:text-stone-100'}
  `;

  return (
    <>
      {/* Mobile Drawer Trigger FAB */}
      <button 
        className="lg:hidden fixed top-4 left-4 z-50 p-3 bg-orange-600 text-white rounded-2xl shadow-lg shadow-orange-600/30 m3-elevation-2 active:scale-95 transition-all cursor-pointer"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Buka Navigasi"
      >
        {isOpen ? <X size={22} /> : <Menu size={22} />}
      </button>

      {/* M3 Navigation Drawer Container */}
      <aside className={`
        fixed inset-y-0 left-0 z-40 w-64 bg-stone-900 dark:bg-stone-950 text-stone-200 transform transition-transform duration-300 ease-out
        ${isOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 border-r border-stone-800/80 flex flex-col m3-elevation-2
      `}>
        {/* M3 Drawer Header (Logo Brand) */}
        <div className="p-6 pb-4 flex items-center gap-3">
          <div className="p-2 bg-orange-600 text-white rounded-2xl shadow-md shadow-orange-600/20">
            <Sparkles size={20} />
          </div>
          <div>
            <h1 className="text-xl font-black text-white italic tracking-tight uppercase">
              EXAM <span className="text-orange-500">JINGGA</span>
            </h1>
            <p className="text-[9px] font-black text-stone-500 uppercase tracking-widest">
              CBT SMKN 1 Rongga
            </p>
          </div>
        </div>
        
        {/* Scrollable Navigation Items */}
        <nav className="flex-1 overflow-y-auto px-4 py-2 space-y-1.5 scrollbar-thin scrollbar-thumb-stone-800">
          <NavLink to="/dashboard" className={linkStyle} onClick={() => setIsOpen(false)}>
            <LayoutDashboard size={18} /> <span>Dashboard</span>
          </NavLink>

          {/* MASTER DATA (ADMIN & KURIKULUM) */}
          {(activeRole === 'admin' || activeRole === 'kurikulum') && (
            <>
              <div className="pt-5 pb-2 text-left">
                <p className="text-[10px] font-black text-stone-500 uppercase tracking-[0.2em] px-4">Master Data</p>
              </div>
              <NavLink to="/master" className={linkStyle} onClick={() => setIsOpen(false)}>
                <GraduationCap size={18} /> <span>Jurusan</span>
              </NavLink>
              <NavLink to="/master-kelas" className={linkStyle} onClick={() => setIsOpen(false)}>
                <School size={18} /> <span>Kelas</span>
              </NavLink>
              <NavLink to="/master-guru" className={linkStyle} onClick={() => setIsOpen(false)}>
                <UserCheck size={18} /> <span>Guru & GTK</span>
              </NavLink>
              <NavLink to="/master-mapel" className={linkStyle} onClick={() => setIsOpen(false)}>
                <Book size={18} /> <span>Mata Pelajaran</span>
              </NavLink>
              <NavLink to="/penugasan-guru" className={linkStyle} onClick={() => setIsOpen(false)}>
                <UserPlus size={18} /> <span>Penugasan Guru</span>
              </NavLink>
            </>
          )}

          {/* AKADEMIK (ADMIN, KURIKULUM, GURU) */}
          {(activeRole === 'admin' || activeRole === 'kurikulum' || activeRole === 'guru' || activeRole === 'pengawas') && (
            <>
              <div className="pt-5 pb-2 text-left">
                 <p className="text-[10px] font-black text-stone-500 uppercase tracking-[0.2em] px-4">Akademik</p>
              </div>
              <NavLink to="/bank-soal" className={linkStyle} onClick={() => setIsOpen(false)}>
                <FileText size={18} /> <span>Bank Soal</span>
              </NavLink>
              <NavLink to="/schedules" className={linkStyle} onClick={() => setIsOpen(false)}>
                <CalendarDays size={18} /> <span>Jadwal Ujian</span>
              </NavLink>
              {(activeRole === 'admin' || activeRole === 'kurikulum') && (
                <NavLink to="/settings" className={linkStyle} onClick={() => setIsOpen(false)}>
                  <Settings size={18} /> <span>Pengaturan Sistem</span>
                </NavLink>
              )}
            </>
          )}

          {/* SISWA & LOGISTIK (ADMIN ONLY) */}
          {(activeRole === 'admin' || activeRole === 'kurikulum') && (
            <>
              <div className="pt-5 pb-2 text-left">
                <p className="text-[10px] font-black text-stone-500 uppercase tracking-[0.2em] px-4">Siswa & Logistik</p>
              </div>
              <NavLink to="/data-siswa" className={linkStyle} onClick={() => setIsOpen(false)}>
                <Users size={18} /> <span>Data Siswa</span>
              </NavLink>
              <NavLink to="/import-siswa" className={linkStyle} onClick={() => setIsOpen(false)}>
                <Upload size={18} /> <span>Import Siswa</span>
              </NavLink>
              <NavLink to="/session-management" className={linkStyle} onClick={() => setIsOpen(false)}>
                <LayoutGrid size={18} /> <span>Sesi & Ruangan</span>
              </NavLink>
              <NavLink to="/exam-cards" className={linkStyle} onClick={() => setIsOpen(false)}>
                <CreditCard size={18} /> <span>Kartu Peserta</span>
              </NavLink>
              <NavLink to="/attendance-list" className={linkStyle} onClick={() => setIsOpen(false)}>
                <ClipboardList size={18} /> <span>Daftar Hadir</span>
              </NavLink>
            </>
          )}
          
          <div className="h-6"></div>
        </nav>

        {/* M3 Drawer Footer (Theme & Logout) */}
        <div className="p-4 bg-stone-900/90 dark:bg-stone-950 border-t border-stone-800/80 space-y-2">
          <button 
            onClick={handleToggleTheme}
            className="flex items-center justify-between w-full px-4 py-2.5 bg-stone-800/60 hover:bg-stone-800 rounded-full border border-stone-700/60 transition-all text-xs font-bold uppercase tracking-wider text-stone-300 hover:text-white cursor-pointer"
          >
            <span>{isDark ? 'Mode Gelap' : 'Mode Terang'}</span>
            {isDark ? <Moon size={16} className="text-orange-400" /> : <Sun size={16} className="text-amber-400" />}
          </button>

          <button 
            onClick={handleLogout} 
            className="flex items-center justify-center gap-2 text-red-400 hover:text-red-300 hover:bg-red-950/30 font-bold transition w-full py-2.5 rounded-full text-xs uppercase tracking-wider cursor-pointer"
          >
            <LogOut size={16} /> <span>Keluar Akun</span>
          </button>
        </div>
      </aside>

      {/* Scrim Overlay on Mobile */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-30 lg:hidden transition-opacity" 
          onClick={() => setIsOpen(false)} 
        />
      )}
    </>
  );
};

export default Sidebar;
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
  ClipboardList
} from 'lucide-react';
import { supabase } from '../supabaseClient';

const Sidebar = ({ role }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [isDark, setIsDark] = useState(localStorage.getItem('theme') === 'dark');

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    }
  }, [isDark]);

  const handleLogout = async () => {
    localStorage.removeItem('user_session');
    supabase.auth.signOut();
    window.location.href = '/login';
  };

  const linkStyle = ({ isActive }) => `
    flex items-center gap-3 px-4 py-3 rounded-xl font-bold transition-all duration-200
    ${isActive 
      ? 'bg-orange-600 text-white shadow-lg shadow-orange-600/30' 
      : 'text-slate-400 hover:bg-slate-800 hover:text-white'}
  `;

  return (
    <>
      <button 
        className="lg:hidden fixed top-4 left-4 z-50 p-2 bg-orange-600 text-white rounded-md"
        onClick={() => setIsOpen(!isOpen)}
      >
        {isOpen ? <X size={24} /> : <Menu size={24} />}
      </button>

      <div className={`
        fixed inset-y-0 left-0 z-40 w-64 bg-slate-900 dark:bg-black text-white transform transition-all duration-300
        ${isOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0 border-r border-slate-800 flex flex-col
      `}>
        {/* LOGO SECTION (Fixed di atas) */}
        <div className="p-6">
          <h1 className="text-2xl font-black text-orange-500 italic tracking-tighter uppercase text-left">
            Exam <span className="text-white">Jingga</span>
          </h1>
          <div className="h-1 w-10 bg-orange-500 mt-1"></div>
        </div>
        
        {/* WRAPPER SCROLLABLE MENU (SUNTIKAN SCROLL DI SINI) */}
        <nav className="flex-1 overflow-y-auto px-6 space-y-1 scrollbar-thin scrollbar-thumb-slate-700">
          <NavLink to="/dashboard" className={linkStyle}>
            <LayoutDashboard size={20} /> Dashboard
          </NavLink>

          {/* MASTER DATA */}
          {(role === 'admin' || role === 'kurikulum') && (
            <>
              <div className="pt-4 pb-2 text-left">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-4">Master Data</p>
              </div>
              <NavLink to="/master" className={linkStyle}>
                <GraduationCap size={20} /> Jurusan
              </NavLink>
              <NavLink to="/master-kelas" className={linkStyle}>
                <School size={20} /> Kelas
              </NavLink>
              <NavLink to="/master-guru" className={linkStyle}>
                <UserCheck size={20} /> Guru
              </NavLink>
              <NavLink to="/master-mapel" className={linkStyle}>
                <Book size={20} /> Mapel
              </NavLink>
              <NavLink to="/penugasan-guru" className={linkStyle}>
                <UserPlus size={20} /> Penugasan Guru
              </NavLink>
            </>
          )}

          {/* AKADEMIK */}
          {(role === 'admin' || role === 'kurikulum' || role === 'guru') && (
            <>
              <div className="pt-4 pb-2 text-left">
                 <p className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-4">Akademik</p>
              </div>
              <NavLink to="/bank-soal" className={linkStyle}>
                <FileText size={20} /> Bank Soal
              </NavLink>
              <NavLink to="/schedules" className={linkStyle}>
                <CalendarDays size={20} /> Jadwal Ujian
              </NavLink>
              {/* Sprint 1: Hide Settings from Guru */}
              {(role === 'admin' || role === 'kurikulum') && (
                  <NavLink to="/settings" className={linkStyle}>
                    <Settings size={20} /> Pengaturan Sistem
                  </NavLink>
              )}
            </>
          )}

          {/* SISWA & LOGISTIK */}
          {role === 'admin' && (
            <>
              <div className="pt-4 pb-2 text-left">
                <p className="text-[10px] font-black text-slate-500 uppercase tracking-[0.2em] px-4">Siswa & Logistik</p>
              </div>
              <NavLink to="/data-siswa" className={linkStyle}>
                <Users size={20} /> Data Siswa
              </NavLink>
              <NavLink to="/import-siswa" className={linkStyle}>
                <Upload size={20} /> Import Siswa
              </NavLink>
              <NavLink to="/session-management" className={linkStyle}>
                <LayoutGrid size={20} /> Sesi & Ruangan
              </NavLink>
              <NavLink to="/exam-cards" className={linkStyle}>
                <CreditCard size={20} /> Kartu Peserta
              </NavLink>
              <NavLink to="/attendance-list" className={linkStyle}>
                <ClipboardList size={20} /> Daftar Hadir
              </NavLink>
            </>
          )}
          
          <div className="h-10"></div>
        </nav>

        {/* BOTTOM SECTION (Fixed di bawah) */}
        <div className="p-6 bg-slate-900 dark:bg-black border-t border-slate-800 space-y-4">
          <button 
            onClick={() => setIsDark(!isDark)}
            className="flex items-center justify-between w-full px-4 py-3 bg-slate-800/50 dark:bg-zinc-900/50 rounded-xl border border-slate-800 hover:border-orange-500 transition-all"
          >
            <span className="text-xs font-bold uppercase tracking-wider">{isDark ? 'Night' : 'Light'}</span>
            {isDark ? <Moon size={18} className="text-orange-400" /> : <Sun size={18} className="text-yellow-400" />}
          </button>

          <button onClick={handleLogout} className="flex items-center gap-3 text-red-400 hover:text-red-300 font-bold transition w-full px-4 text-sm uppercase">
            <LogOut size={20} /> Keluar
          </button>
        </div>
      </div>

      {isOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-30 lg:hidden" onClick={() => setIsOpen(false)} />
      )}
    </>
  );
};

export default Sidebar;
import React, { useState, useEffect } from 'react';
import { LogIn, Sun, Moon, Sparkles, UserCog, BookOpen, Users, School } from 'lucide-react';
import Swal from 'sweetalert2';
import logoSekolah from '../assets/logo_sekolah.png';
import { mockUsers } from '../demoData';

const StandaloneDemoLogin = () => {
  const [loading, setLoading] = useState(false);
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    // Set initial theme
    if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      setIsDark(true);
      document.documentElement.classList.add('dark');
    }
  }, []);

  const toggleDarkMode = () => {
    if (isDark) {
      document.documentElement.classList.remove('dark');
      localStorage.theme = 'light';
      setIsDark(false);
    } else {
      document.documentElement.classList.add('dark');
      localStorage.theme = 'dark';
      setIsDark(true);
    }
  };

  const handleQuickLogin = async (role) => {
    setLoading(true);

    try {
      // Simulate network delay untuk feel realistic
      await new Promise(resolve => setTimeout(resolve, 800));

      const userData = mockUsers[role];

      if (!userData) {
        throw new Error(`Role ${role} tidak tersedia!`);
      }

      // Tambah flag demo mode
      const sessionData = {
        ...userData,
        isDemoMode: true,
        loginTime: new Date().toISOString()
      };

      localStorage.setItem('user_session', JSON.stringify(sessionData));

      let redirectPath = '/dashboard';
      if (role === 'siswa') {
        redirectPath = '/student-dashboard';
      }

      Swal.fire({
        title: '🎉 Login Demo Berhasil!',
        html: `
          <p class="text-lg mb-2">Selamat datang sebagai <strong>${role.toUpperCase()}</strong></p>
          <p class="text-sm text-gray-600 dark:text-gray-400">${userData.fullName}</p>
          <div class="mt-4 p-3 bg-blue-50 dark:bg-blue-900/30 rounded-lg">
            <p class="text-xs text-blue-700 dark:text-blue-300">
              ✨ Mode Demo - Semua data adalah simulasi
            </p>
          </div>
        `,
        icon: 'success',
        timer: 2000,
        showConfirmButton: false,
        customClass: {
          popup: 'rounded-3xl'
        }
      }).then(() => {
        window.location.href = redirectPath;
      });
    } catch (error) {
      Swal.fire({
        title: 'Login Demo Gagal',
        text: error.message,
        icon: 'error',
        confirmButtonColor: '#ea580c',
        customClass: {
          popup: 'rounded-3xl'
        }
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex flex-col justify-center items-center p-6 transition-colors duration-500 font-sans text-left relative overflow-hidden">

      {/* Decorative Blur Orbs */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-orange-500/10 rounded-full -ml-20 -mt-20 blur-3xl animate-pulse"></div>
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-orange-600/10 rounded-full -mr-20 -mb-20 blur-3xl"></div>

      {/* Dark Mode Toggle */}
      <button onClick={toggleDarkMode} className="absolute top-6 right-6 p-3 rounded-2xl bg-white/80 dark:bg-zinc-900/80 backdrop-blur-md shadow-lg text-slate-500 dark:text-orange-400 hover:scale-110 transition-all border border-slate-100 dark:border-zinc-800 z-20">
        {isDark ? <Sun size={20} /> : <Moon size={20} />}
      </button>

      <div className="w-full max-w-2xl bg-white/90 dark:bg-zinc-900/90 backdrop-blur-xl p-10 rounded-[3rem] shadow-2xl shadow-slate-200/50 dark:shadow-black/50 border border-white/20 dark:border-zinc-800 transition-colors duration-500 relative z-10 animate-in fade-in slide-in-from-bottom-8 duration-700">

        {/* Header / Logo */}
        <div className="text-center mb-10">
          {/* Logo Sekolah */}
          <div className="relative inline-block mb-6">
             <div className="absolute inset-0 bg-orange-500 blur-xl opacity-20 rounded-full"></div>
             <img src={logoSekolah} alt="Logo SMKN 1 Rongga" className="w-24 h-24 mx-auto relative z-10 object-contain drop-shadow-xl hover:scale-105 transition-transform duration-500" />
          </div>

          <div className="flex items-center justify-center gap-2 mb-2">
            <div className="bg-orange-600 text-white p-2.5 rounded-2xl shadow-lg shadow-orange-600/30">
              <Sparkles size={24} className="animate-pulse" />
            </div>
            <h1 className="text-3xl font-black text-slate-900 dark:text-white uppercase italic tracking-tighter">
              EXAM <span className="text-orange-600">JINGGA</span>
            </h1>
          </div>
          <p className="text-[10px] text-slate-500 dark:text-zinc-400 font-black uppercase tracking-widest mt-2">Sistem CBT SMKN 1 Rongga</p>

          {/* Demo Badge */}
          <div className="mt-4 inline-block px-6 py-2.5 bg-gradient-to-r from-blue-600/20 to-purple-600/20 border-2 border-blue-600/30 rounded-full">
            <p className="text-sm text-blue-600 dark:text-blue-400 font-black uppercase tracking-wider flex items-center gap-2">
              <span className="animate-pulse">✨</span>
              Demo Standalone Mode
              <span className="animate-pulse">✨</span>
            </p>
          </div>

          {/* Info Box */}
          <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-2xl">
            <p className="text-xs text-blue-700 dark:text-blue-300 leading-relaxed">
              <strong>Mode Demo Mandiri:</strong> Tidak memerlukan koneksi database.<br/>
              Semua data adalah simulasi untuk demonstrasi fitur aplikasi.
            </p>
          </div>
        </div>

        {/* Quick Login Buttons */}
        <div className="space-y-4 mb-6">
          <h2 className="text-center text-sm font-black text-slate-400 dark:text-zinc-500 uppercase tracking-widest mb-6">
            Pilih Role untuk Login Demo
          </h2>

          {/* Admin Button */}
          <button
            onClick={() => handleQuickLogin('admin')}
            disabled={loading}
            className="w-full bg-gradient-to-r from-orange-600 to-orange-700 text-white py-5 px-6 rounded-2xl font-black uppercase text-sm tracking-wide flex items-center justify-between hover:shadow-xl hover:shadow-orange-600/30 transition-all active:scale-[0.98] disabled:opacity-70 group"
          >
            <div className="flex items-center gap-3">
              <div className="bg-white/20 p-2 rounded-xl">
                <UserCog size={24} />
              </div>
              <div className="text-left">
                <div className="text-xs opacity-75">Login sebagai</div>
                <div className="text-lg font-black">ADMINISTRATOR</div>
              </div>
            </div>
            <LogIn size={20} className="group-hover:translate-x-1 transition-transform" />
          </button>

          {/* Kurikulum Button */}
          <button
            onClick={() => handleQuickLogin('kurikulum')}
            disabled={loading}
            className="w-full bg-gradient-to-r from-blue-600 to-blue-700 text-white py-5 px-6 rounded-2xl font-black uppercase text-sm tracking-wide flex items-center justify-between hover:shadow-xl hover:shadow-blue-600/30 transition-all active:scale-[0.98] disabled:opacity-70 group"
          >
            <div className="flex items-center gap-3">
              <div className="bg-white/20 p-2 rounded-xl">
                <BookOpen size={24} />
              </div>
              <div className="text-left">
                <div className="text-xs opacity-75">Login sebagai</div>
                <div className="text-lg font-black">KURIKULUM</div>
              </div>
            </div>
            <LogIn size={20} className="group-hover:translate-x-1 transition-transform" />
          </button>

          {/* Guru Button */}
          <button
            onClick={() => handleQuickLogin('guru')}
            disabled={loading}
            className="w-full bg-gradient-to-r from-green-600 to-green-700 text-white py-5 px-6 rounded-2xl font-black uppercase text-sm tracking-wide flex items-center justify-between hover:shadow-xl hover:shadow-green-600/30 transition-all active:scale-[0.98] disabled:opacity-70 group"
          >
            <div className="flex items-center gap-3">
              <div className="bg-white/20 p-2 rounded-xl">
                <Users size={24} />
              </div>
              <div className="text-left">
                <div className="text-xs opacity-75">Login sebagai</div>
                <div className="text-lg font-black">GURU</div>
              </div>
            </div>
            <LogIn size={20} className="group-hover:translate-x-1 transition-transform" />
          </button>

          {/* Siswa Button */}
          <button
            onClick={() => handleQuickLogin('siswa')}
            disabled={loading}
            className="w-full bg-gradient-to-r from-purple-600 to-purple-700 text-white py-5 px-6 rounded-2xl font-black uppercase text-sm tracking-wide flex items-center justify-between hover:shadow-xl hover:shadow-purple-600/30 transition-all active:scale-[0.98] disabled:opacity-70 group"
          >
            <div className="flex items-center gap-3">
              <div className="bg-white/20 p-2 rounded-xl">
                <School size={24} />
              </div>
              <div className="text-left">
                <div className="text-xs opacity-75">Login sebagai</div>
                <div className="text-lg font-black">SISWA</div>
              </div>
            </div>
            <LogIn size={20} className="group-hover:translate-x-1 transition-transform" />
          </button>
        </div>

        {/* Features Info */}
        <div className="mt-8 p-4 bg-slate-100 dark:bg-zinc-800/50 rounded-2xl">
          <p className="text-xs text-slate-600 dark:text-zinc-400 text-center leading-relaxed">
            <strong className="text-orange-600 dark:text-orange-400">Demo Features:</strong><br/>
            Dashboard interaktif • Data simulasi • Tanpa database • Responsive UI
          </p>
        </div>

        <footer className="mt-10 text-center text-xs border-t border-slate-100 dark:border-zinc-800 pt-6">
          <p className="text-slate-400 dark:text-zinc-600 font-bold uppercase tracking-widest text-[8px]">© 2026 SMKN 1 RONGGA</p>
          <p className="text-slate-400 dark:text-zinc-600 text-[8px] mt-1">Demo Version - No Database Required</p>
        </footer>
      </div>
    </div>
  );
};

export default StandaloneDemoLogin;

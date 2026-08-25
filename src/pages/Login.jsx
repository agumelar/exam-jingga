import React, { useState, useEffect } from 'react';
import { LogIn, Sun, Moon, Sparkles, ShieldCheck, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import logoSekolah from '../assets/logo_sekolah.png';
import M3Button from '../components/ui/M3Button';
import M3Card from '../components/ui/M3Card';

const Login = () => {
  const { loginWithSSO } = useAuth();
  const [isDark, setIsDark] = useState(false);
  const [loadingSSO, setLoadingSSO] = useState(false);

  useEffect(() => {
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

  const handleSSOLogin = () => {
    setLoadingSSO(true);
    loginWithSSO();
  };

  return (
    <div className="min-h-screen bg-stone-50 dark:bg-stone-950 flex flex-col justify-center items-center p-4 sm:p-6 transition-colors duration-300 font-sans relative overflow-hidden text-left">
      
      {/* Decorative M3 Tonal Glow Orbs */}
      <div className="absolute top-0 left-0 w-96 h-96 bg-orange-500/10 dark:bg-orange-500/5 rounded-full -ml-20 -mt-20 blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-0 right-0 w-96 h-96 bg-orange-600/10 dark:bg-orange-600/5 rounded-full -mr-20 -mb-20 blur-3xl pointer-events-none"></div>

      {/* Dark/Light Mode FAB */}
      <button 
        onClick={toggleDarkMode} 
        aria-label="Toggle Theme"
        className="absolute top-6 right-6 p-3 rounded-full bg-white/90 dark:bg-stone-900/90 backdrop-blur-md shadow-md text-stone-600 dark:text-orange-400 hover:scale-105 transition-all border border-stone-200 dark:border-stone-800 z-20 cursor-pointer"
      >
        {isDark ? <Sun size={20} /> : <Moon size={20} />}
      </button>

      {/* M3 Elevated Login Surface Card */}
      <M3Card variant="elevated" className="w-full max-w-md p-8 sm:p-10 relative z-10 border border-stone-200 dark:border-stone-800 m3-elevation-3">
        
        {/* Header / Logo */}
        <div className="text-center mb-8">
          <div className="relative inline-block mb-4">
             <div className="absolute inset-0 bg-orange-500 blur-2xl opacity-20 rounded-full"></div>
             <img 
               src={logoSekolah} 
               alt="Logo SMKN 1 Rongga" 
               className="w-24 h-24 mx-auto relative z-10 object-contain drop-shadow-xl hover:scale-105 transition-transform duration-300" 
             />
          </div>

          <div className="flex items-center justify-center gap-2 mb-1">
            <div className="bg-orange-600 text-white p-2 rounded-2xl shadow-md shadow-orange-600/30">
              <Sparkles size={18} />
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-stone-900 dark:text-white uppercase italic tracking-tighter">
              EXAM <span className="text-orange-600 dark:text-orange-500">JINGGA</span>
            </h1>
          </div>
          <p className="text-[10px] text-stone-500 dark:text-stone-400 font-black uppercase tracking-[0.25em]">
            Sistem CBT SMKN 1 Rongga
          </p>
        </div>

        {/* SSO Information Banner */}
        <div className="mb-8 p-4 rounded-2xl bg-orange-50 dark:bg-orange-950/40 border border-orange-200 dark:border-orange-900/40 text-center">
          <div className="inline-flex p-2 bg-orange-600 text-white rounded-xl shadow-xs mb-2">
            <ShieldCheck size={18} />
          </div>
          <h2 className="text-xs font-black text-orange-950 dark:text-orange-300 uppercase tracking-wider mb-1">
            Single Sign-On (SSO) Terpusat
          </h2>
          <p className="text-[11px] text-stone-600 dark:text-stone-400 leading-relaxed font-medium">
            Silakan masuk menggunakan Akun Belajar resmi SMKN 1 Rongga (Keycloak SSO).
          </p>
        </div>

        {/* Primary Action Button */}
        <div className="space-y-4">
          <M3Button
            variant="filled"
            size="lg"
            fullWidth
            loading={loadingSSO}
            onClick={handleSSOLogin}
            className="h-14 font-black uppercase tracking-wider text-xs justify-between px-6 shadow-xl shadow-orange-600/20"
          >
            <span className="flex items-center gap-3">
              <span className="p-1.5 bg-white/20 rounded-xl">
                <LogIn size={18} />
              </span>
              <span>Masuk dengan SSO SMKN 1 Rongga</span>
            </span>
            <ArrowRight size={18} />
          </M3Button>

          <p className="text-center text-[10px] text-stone-500 dark:text-stone-500 font-bold uppercase tracking-wider">
            Didukung oleh Single Sign-On SMKN 1 Rongga
          </p>
        </div>

      </M3Card>

      <footer className="mt-8 text-center text-xs font-bold text-stone-400 dark:text-stone-600 uppercase tracking-widest relative z-10">
        &copy; {new Date().getFullYear()} SMKN 1 Rongga &bull; CBT Exam Jingga
      </footer>
    </div>
  );
};

export default Login;

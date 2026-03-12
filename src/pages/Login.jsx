import React, { useState, useEffect } from 'react';
import { Lock, LogIn, Sun, Moon, GraduationCap, User as UserIcon, Eye, EyeOff, Sparkles } from 'lucide-react';
import { supabase } from '../supabaseClient';
import Swal from 'sweetalert2';
import logoSekolah from '../assets/logo_sekolah.png'; 

const Login = () => {
  const [identifier, setIdentifier] = useState(''); // Bisa Email Guru atau NIS Siswa
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [isDark, setIsDark] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

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

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    
    try {
        // --- JALUR 1: ADMIN / GURU (NON-AUTH SAKTI) ---
        const { data: staff, error: staffError } = await supabase
          .from('teachers')
          .select('*')
          .eq('email', identifier)
          .eq('password', password)
          .maybeSingle();

        if (staff) {
          localStorage.setItem('user_session', JSON.stringify({
            id: staff.id,
            uid: staff.user_id || staff.id,
            fullName: staff.full_name,
            role: staff.role_level ? staff.role_level.toLowerCase() : 'guru',
            email: staff.email
          }));

          Swal.fire({
            title: 'Akses Diterima!',
            text: `Selamat datang, ${staff.full_name}`,
            icon: 'success',
            timer: 1500,
            showConfirmButton: false
          }).then(() => {
            // Arahkan ke dashboard admin/guru sesuai setting routing lu
            window.location.href = '/dashboard'; 
          });
          return;
        }

        // --- JALUR 2: SISWA (NON-AUTH SAKTI) ---
        const { data: student, error: studentError } = await supabase
          .from('students')
          .select('*')
          .eq('nis', identifier)
          .eq('password_plain', password) 
          .maybeSingle();

        if (student) {
          if (student.status !== 'aktif' && student.status !== "'aktif'") {
             throw new Error("Akun Anda dinonaktifkan. Silakan lapor pengawas!");
          }

          localStorage.setItem('user_session', JSON.stringify({
            id: student.id,
            uid: student.user_id || student.id,
            fullName: student.full_name,
            nis: student.nis,
            role: 'siswa'
          }));

          Swal.fire({
            title: 'Login Berhasil!',
            text: `Selamat mengerjakan ujian, ${student.full_name}`,
            icon: 'success',
            timer: 1500,
            showConfirmButton: false
          }).then(() => {
            window.location.href = '/student-dashboard';
          });
          return;
        }

        // Kalau gagal keduanya
        throw new Error("Email/NIS atau Kata Sandi tidak cocok!");

    } catch (error) {
        Swal.fire({
            title: 'Akses Ditolak',
            text: error.message,
            icon: 'error',
            confirmButtonColor: '#ea580c'
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

      <div className="w-full max-w-md bg-white/90 dark:bg-zinc-900/90 backdrop-blur-xl p-10 rounded-[3rem] shadow-2xl shadow-slate-200/50 dark:shadow-black/50 border border-white/20 dark:border-zinc-800 transition-colors duration-500 relative z-10 animate-in fade-in slide-in-from-bottom-8 duration-700">
        
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
        </div>

        {/* Form Login */}
        <form onSubmit={handleLogin} className="space-y-6">
          
          <div className="space-y-1 group">
            <label className="text-[10px] font-black text-slate-400 dark:text-zinc-500 uppercase tracking-widest ml-2 group-focus-within:text-orange-600 transition-colors">Email Guru / NIS Siswa</label>
            <div className="relative">
              <UserIcon className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-orange-600 transition-colors" size={20} />
              <input 
                  type="text" 
                  required 
                  value={identifier} 
                  onChange={(e) => setIdentifier(e.target.value)} 
                  placeholder="NIS atau Email" 
                  className="w-full pl-14 pr-6 py-4 bg-slate-50 dark:bg-zinc-950/50 border-2 border-transparent focus:border-orange-500 rounded-2xl outline-none font-bold text-slate-900 dark:text-white transition-all shadow-inner" 
              />
            </div>
          </div>

          <div className="space-y-1 group">
            <label className="text-[10px] font-black text-slate-400 dark:text-zinc-500 uppercase tracking-widest ml-2 group-focus-within:text-orange-600 transition-colors">Kata Sandi</label>
            <div className="relative">
              <Lock className="absolute left-5 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-orange-600 transition-colors" size={20} />
              <input 
                  type={showPassword ? "text" : "password"} 
                  required 
                  value={password} 
                  onChange={(e) => setPassword(e.target.value)} 
                  placeholder="••••••••" 
                  className="w-full pl-14 pr-14 py-4 bg-slate-50 dark:bg-zinc-950/50 border-2 border-transparent focus:border-orange-500 rounded-2xl outline-none font-bold text-slate-900 dark:text-white transition-all shadow-inner" 
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-orange-600 transition-colors focus:outline-none"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
          </div>

          <button type="submit" disabled={loading} className="w-full bg-orange-600 text-white py-5 rounded-2xl font-black uppercase text-xs tracking-[0.2em] flex items-center justify-center gap-3 hover:bg-orange-700 hover:shadow-xl hover:shadow-orange-600/30 transition-all active:scale-[0.98] disabled:opacity-70 mt-4">
            {loading ? (
              <RefreshCw size={18} className="animate-spin" />
            ) : (
              <LogIn size={18} />
            )}
            {loading ? 'MEMVERIFIKASI...' : 'MASUK KE SISTEM'}
          </button>
        </form>

        <footer className="mt-10 text-center text-xs border-t border-slate-100 dark:border-zinc-800 pt-6">
          <p className="text-slate-400 dark:text-zinc-600 font-bold uppercase tracking-widest text-[8px]">© 2026 SMKN 1 RONGGA</p>
        </footer>
      </div>
    </div>
  );
};

export default Login;
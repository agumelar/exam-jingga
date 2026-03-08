import React, { useState } from 'react';
import { Mail, Lock, LogIn, Sun, Moon, GraduationCap, School } from 'lucide-react'; // Tambah icon School buat alt
import { supabase } from '../supabaseClient';
import Swal from 'sweetalert2';

// 1. IMPORT LOGO NYA DI SINI BRO
import logoSekolah from '../assets/logo_sekolah.png'; 

const Login = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [isDark, setIsDark] = useState(localStorage.theme === 'dark');

  // Logic Dark Mode (Tetep Aman)
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
    // ... logic login lu tetep sama, nggak ada yang diubah ...
    try {
        const { data, error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        
        // Cek Role (Asumsi tabel 'teachers' dan 'students' ada kolom role_level/role)
        let role = '';
        let fullName = '';
        let id = '';

        // Cek ke tabel Guru dulu
        const { data: teacherData } = await supabase.from('teachers').select('*').eq('user_id', data.user.id).single();
        if(teacherData) {
            role = teacherData.role_level; // admin/kurikulum/guru
            fullName = teacherData.full_name;
            id = teacherData.id;
        } else {
            // Cek ke tabel Siswa
            const { data: studentData } = await supabase.from('students').select('*').eq('user_id', data.user.id).single();
            if(studentData) {
                role = 'siswa';
                fullName = studentData.full_name;
                id = studentData.id;
            }
        }

        if(!role) throw new Error("Role pengguna tidak ditemukan!");

        localStorage.setItem('user_session', JSON.stringify({
            id: id,
            uid: data.user.id,
            email: data.user.email,
            fullName: fullName,
            role: role
        }));

        Swal.fire({
            title: 'Login Berhasil!',
            text: `Selamat datang, ${fullName}`,
            icon: 'success',
            timer: 1500,
            showConfirmButton: false
        }).then(() => {
            window.location.href = '/dashboard'; // Sesuaikan route dashboard lu
        });

    } catch (error) {
        Swal.fire('Gagal Login', error.message, 'error');
    } finally {
        setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex flex-col justify-center items-center p-4 transition-colors duration-500 font-sans text-left">
      
      {/* Tombol Dark Mode Di Pojok */}
      <button onClick={toggleDarkMode} className="absolute top-4 right-4 p-3 rounded-2xl bg-white dark:bg-zinc-900 shadow-lg text-slate-500 dark:text-orange-400 hover:scale-110 transition-all border dark:border-zinc-800">
        {isDark ? <Sun size={20} /> : <Moon size={20} />}
      </button>

      <div className="w-full max-w-md bg-white dark:bg-zinc-900 p-10 rounded-[2.5rem] shadow-xl border border-slate-100 dark:border-zinc-800 transition-colors duration-500 relative overflow-hidden">
        
        {/* Dekorasi Latar Belakang */}
        <div className="absolute -top-10 -right-10 w-32 h-32 bg-orange-500/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-orange-500/10 rounded-full blur-3xl"></div>

        <div className="text-center mb-10 relative z-10">
          
          {/* 2. INI LOGO SEKOLAHNYA BRO! */}
          <img 
            src={logoSekolah} 
            alt="Logo SMKN 1 Rongga" 
            className="w-24 h-24 mx-auto mb-6 object-contain drop-shadow-md animate-in fade-in zoom-in duration-1000"
          />

          <div className="flex items-center justify-center gap-2 mb-2">
            <div className="bg-orange-600 text-white p-2.5 rounded-2xl shadow-md shadow-orange-500/30">
              <GraduationCap size={24} className="italic" />
            </div>
            <h1 className="text-3xl font-black text-slate-900 dark:text-white uppercase italic tracking-tighter">
              EXAM <span className="text-orange-600">JINGGA</span>
            </h1>
          </div>
          <p className="text-sm text-slate-500 dark:text-zinc-400 font-bold uppercase tracking-widest mt-3">Sistem CBT SMKN 1 Rongga</p>
          <div className="w-16 h-1.5 bg-orange-500 mx-auto mt-4 rounded-full"></div>
        </div>

        <form onSubmit={handleLogin} className="space-y-6 relative z-10">
          <div className="space-y-1">
            <label className="text-[10px] font-black text-slate-500 dark:text-zinc-400 uppercase tracking-widest ml-2">Username</label>
            <div className="relative">
              <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 dark:text-zinc-600" size={20} />
              <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="nama@smkn1rongga.sch.id" className="w-full pl-12 pr-4 py-4 bg-slate-50 dark:bg-zinc-950 border-none rounded-2xl outline-none focus:ring-2 focus:ring-orange-500 font-bold dark:text-white transition-all shadow-inner" />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-black text-slate-500 dark:text-zinc-400 uppercase tracking-widest ml-2">Kata Sandi (Password)</label>
            <div className="relative">
              <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 dark:text-zinc-600" size={20} />
              <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" className="w-full pl-12 pr-4 py-4 bg-slate-50 dark:bg-zinc-950 border-none rounded-2xl outline-none focus:ring-2 focus:ring-orange-500 font-bold dark:text-white transition-all shadow-inner" />
            </div>
          </div>

          <button type="submit" disabled={loading} className="w-full bg-slate-900 dark:bg-white text-white dark:text-black py-5 rounded-2xl font-black uppercase text-xs tracking-widest flex items-center justify-center gap-3 hover:scale-[1.03] transition-all shadow-lg shadow-slate-900/10 dark:shadow-white/5 active:scale-95 disabled:opacity-50">
            {loading ? (
              <div className="w-5 h-5 border-2 border-white dark:border-black border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <LogIn size={18} />
            )}
            {loading ? 'Memverifikasi...' : 'MASUK KE RUANG UJIAN'}
          </button>
        </form>

        <footer className="mt-12 text-center text-xs border-t dark:border-zinc-800 pt-6 relative z-10">
          <p className="text-slate-400 dark:text-zinc-600 font-medium">© 2026 SMKN 1 Rongga. All rights reserved.</p>
          <p className="text-orange-600 font-bold mt-1">UP RPL JINGGA</p>
        </footer>
      </div>
    </div>
  );
};

export default Login;
import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { handleKeycloakCallback } from '../services/keycloakAuth';
import { useAuth } from '../context/AuthContext';
import { Sparkles, AlertCircle } from 'lucide-react';

const AuthCallback = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { updateUserSession } = useAuth();
  const [error, setError] = useState(null);

  useEffect(() => {
    const code = searchParams.get('code');
    const state = searchParams.get('state');
    const errorParam = searchParams.get('error_description') || searchParams.get('error');

    if (errorParam) {
      setError(errorParam);
      return;
    }

    if (!code) {
      setError('Kode otorisasi tidak ditemukan pada URL redirect.');
      return;
    }

    handleKeycloakCallback(code, state)
      .then(({ userSession, targetPath }) => {
        updateUserSession(userSession);
        
        // Arahkan ke dashboard sesuai role
        if (userSession.role === 'siswa') {
          navigate('/student-dashboard', { replace: true });
        } else {
          const destination = targetPath && targetPath !== '/login' ? targetPath : '/';
          navigate(destination, { replace: true });
        }
      })
      .catch((err) => {
        console.error('Error saat proses callback Keycloak:', err);
        setError(err.message || 'Gagal memproses otentikasi login SSO.');
      });
  }, [searchParams, navigate, updateUserSession]);

  if (error) {
    return (
      <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex items-center justify-center p-6 text-left">
        <div className="max-w-md w-full bg-white dark:bg-zinc-900 p-8 rounded-3xl shadow-xl border border-red-200 dark:border-red-900/50">
          <div className="flex items-center gap-3 text-red-600 dark:text-red-400 mb-4">
            <AlertCircle size={28} />
            <h2 className="text-xl font-black uppercase tracking-tight">Otentikasi Gagal</h2>
          </div>
          <p className="text-sm text-slate-600 dark:text-zinc-400 mb-6 font-medium leading-relaxed">
            {error}
          </p>
          <button
            onClick={() => navigate('/login', { replace: true })}
            className="w-full py-4 bg-orange-600 hover:bg-orange-700 text-white rounded-2xl font-black uppercase text-xs tracking-widest transition-all"
          >
            Kembali ke Halaman Login
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 flex flex-col items-center justify-center p-6">
      <div className="flex flex-col items-center gap-6 max-w-sm text-center">
        <div className="relative">
          <div className="absolute inset-0 bg-orange-500 blur-2xl opacity-30 rounded-full animate-pulse"></div>
          <div className="w-16 h-16 bg-orange-600 text-white rounded-3xl flex items-center justify-center shadow-2xl shadow-orange-600/40 relative z-10 animate-bounce">
            <Sparkles size={32} />
          </div>
        </div>
        <div className="space-y-2">
          <h2 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight uppercase">
            Memverifikasi Akun SSO...
          </h2>
          <p className="text-xs text-slate-500 dark:text-zinc-400 font-bold uppercase tracking-widest">
            Menghubungkan profil sekolah Anda ke sistem CBT
          </p>
        </div>
        <div className="w-48 h-1.5 bg-slate-200 dark:bg-zinc-800 rounded-full overflow-hidden">
          <div className="w-full h-full bg-orange-600 rounded-full animate-indeterminate"></div>
        </div>
      </div>
    </div>
  );
};

export default AuthCallback;

import React, { createContext, useContext, useState, useEffect } from 'react';
import { initiateKeycloakLogin, logoutKeycloak, parseJwt } from '../services/keycloakAuth';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Muat sesi pengguna dari localStorage
    try {
      const savedSession = localStorage.getItem('user_session');
      const token = localStorage.getItem('kc_access_token');
      
      if (savedSession) {
        const parsed = JSON.parse(savedSession);
        
        // Periksa apakah token JWT masih valid (belum kedaluwarsa)
        if (token) {
          const payload = parseJwt(token);
          if (payload && payload.exp && payload.exp * 1000 < Date.now()) {
            console.warn('Sesi SSO kedaluwarsa, silakan login ulang.');
            // Biarkan user_session jika offline, atau hapus jika strict
          }
        }
        setUser(parsed);
      }
    } catch (e) {
      console.error('Gagal membaca sesi pengguna', e);
      localStorage.removeItem('user_session');
    } finally {
      setLoading(false);
    }
  }, []);

  const loginWithSSO = (targetPath = '/') => {
    return initiateKeycloakLogin(targetPath);
  };

  const logout = () => {
    setUser(null);
    logoutKeycloak();
  };

  const updateUserSession = (newSession) => {
    setUser(newSession);
    localStorage.setItem('user_session', JSON.stringify(newSession));
  };

  return (
    <AuthContext.Provider value={{
      user,
      role: user?.role || null,
      isAuthenticated: !!user,
      isStudent: user?.role === 'siswa',
      isTeacher: user?.role === 'guru' || user?.role === 'pengawas',
      isAdmin: user?.role === 'admin' || user?.role === 'kurikulum',
      loading,
      loginWithSSO,
      logout,
      updateUserSession
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth harus digunakan di dalam <AuthProvider>');
  }
  return context;
};

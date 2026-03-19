import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import StandaloneDemoLogin from './pages/StandaloneDemoLogin';
import DemoDashboard from './pages/DemoDashboard';

function DemoApp() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Cek session dari localStorage
    const user = localStorage.getItem('user_session');
    if (user) {
      try {
        const userData = JSON.parse(user);
        // Hanya terima session dengan flag demo mode
        if (userData.isDemoMode) {
          setSession(userData);
        }
      } catch (e) {
        localStorage.removeItem('user_session');
      }
    }
    setLoading(false);
  }, []);

  if (loading) return (
    <div className="h-screen flex items-center justify-center bg-slate-50 dark:bg-zinc-950">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-600"></div>
    </div>
  );

  return (
    <Router>
      <Routes>
        {/* Rute Login Demo */}
        <Route path="/" element={!session ? <StandaloneDemoLogin /> : <Navigate to="/dashboard" />} />
        <Route path="/login" element={!session ? <StandaloneDemoLogin /> : <Navigate to="/dashboard" />} />
        <Route path="/demo" element={!session ? <StandaloneDemoLogin /> : <Navigate to="/dashboard" />} />

        {/* Rute Dashboard Demo */}
        <Route path="/dashboard" element={session ? <DemoDashboard /> : <Navigate to="/" />} />
        <Route path="/student-dashboard" element={session?.role === 'siswa' ? <DemoDashboard /> : <Navigate to="/" />} />

        {/* Redirect semua route lain ke login */}
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Router>
  );
}

export default DemoApp;

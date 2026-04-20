import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import DemoLogin from './pages/DemoLogin';
import Dashboard from './pages/Dashboard';
import MasterMajors from './pages/MasterMajors'; 
import ImportStudents from './pages/ImportStudents';
import MasterStudents from './pages/MasterStudents';
import MasterClasses from './pages/MasterClasses';
import StudentDashboard from './pages/StudentDashboard';
import MasterTeachers from './pages/MasterTeachers';
import MasterSubjects from './pages/MasterSubjects';
import TeacherAssignments from './pages/TeacherAssignments';
import BankSoal from './pages/BankSoal';
import Schedules from './pages/Schedules';
import SelectQuestions from './pages/SelectQuestions';
import ExamParticipants from './pages/ExamParticipants';
import ExamInterface from './pages/ExamInterface';
import Logistics from './pages/Logistics';
import SessionManagement from './pages/SessionManagement';
import Settings from './pages/Settings';
import ExamCards from './pages/ExamCards';
import AttendanceList from './pages/AttendanceList';
import ExamResults from './pages/ExamResults';

function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // SUNTIKAN: Cek session manual dari localStorage (Sesuai sistem Login baru)
    const user = localStorage.getItem('user_session');
    if (user) {
      setSession(JSON.parse(user));
    }
    setLoading(false);

    // Auto redirect to demo login if accessed from demo domain
    const isDemoDomain = window.location.hostname.includes('demo.') ||
                         window.location.pathname === '/demo' ||
                         window.location.search.includes('demo=true');

    if (isDemoDomain && !user && window.location.pathname === '/login') {
      window.location.href = '/demo';
    }
  }, []);

  if (loading) return (
    <div className="h-screen flex items-center justify-center bg-slate-50 dark:bg-zinc-950">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-600"></div>
    </div>
  );

  return (
    <Router>
      <Routes>
        {/* Rute Login */}
        <Route path="/login" element={!session ? <Login /> : <Navigate to="/" />} />
        <Route path="/demo" element={!session ? <DemoLogin /> : <Navigate to="/" />} />

        {/* Rute Dashboard Utama (Admin/Guru/Kurikulum) */}
        <Route path="/" element={session ? <Dashboard /> : <Navigate to="/login" />} />
        
        {/* Rute Master Data */}
        <Route path="/master" element={session ? <MasterMajors /> : <Navigate to="/login" />} />
        <Route path="/master-kelas" element={session ? <MasterClasses /> : <Navigate to="/login" />} />
        <Route path="/master-guru" element={session ? <MasterTeachers /> : <Navigate to="/login" />} />
        <Route path="/master-mapel" element={session ? <MasterSubjects /> : <Navigate to="/login" />} />
        <Route path="/penugasan-guru" element={session ? <TeacherAssignments /> : <Navigate to="/login" />} />

        {/* Rute Akademik & Siswa */}
        <Route path="/bank-soal" element={session ? <BankSoal /> : <Navigate to="/login" />} />
        <Route path="/schedules" element={session ? <Schedules /> : <Navigate to="/login" />} />
        <Route path="/select-questions/:examId" element={session ? <SelectQuestions /> : <Navigate to="/login" />} />
        <Route path="/data-siswa" element={session ? <MasterStudents /> : <Navigate to="/login" />} />
        <Route path="/import-siswa" element={session ? <ImportStudents /> : <Navigate to="/login" />} />
        <Route path="/exam-participants/:examId" element={session ? <ExamParticipants /> : <Navigate to="/login" />} />
        <Route path="/exam-interface/:examId" element={<ExamInterface />} />
        <Route path="/logistics" element={<Logistics />} />
        <Route path="/session-management" element={<SessionManagement />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/exam-cards" element={session ? <ExamCards /> : <Navigate to="/login" />} />
        <Route path="/attendance-list" element={<AttendanceList />} />
        <Route path="/exam-results/:examId" element={<ExamResults />} />

        {/* Dashboard Khusus Siswa */}
        <Route path="/student-dashboard" element={session?.role === 'siswa' ? <StudentDashboard /> : <Navigate to="/login" />} />
        
        {/* Redirect jika alamat ngawur */}
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </Router>
  );
}

export default App;
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Login from './pages/Login';
import AuthCallback from './pages/AuthCallback';
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

// Komponen Pelindung Rute (Protected Route)
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-50 dark:bg-zinc-950">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-600"></div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Jika siswa coba akses admin -> lempar ke student-dashboard
    if (user.role === 'siswa') {
      return <Navigate to="/student-dashboard" replace />;
    }
    // Jika guru/admin coba akses siswa -> lempar ke dashboard admin
    return <Navigate to="/" replace />;
  }

  return children;
};

function AppRoutes() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-50 dark:bg-zinc-950">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-600"></div>
      </div>
    );
  }

  return (
    <Routes>
      {/* Rute Otentikasi */}
      <Route path="/login" element={!user ? <Login /> : (user.role === 'siswa' ? <Navigate to="/student-dashboard" replace /> : <Navigate to="/" replace />)} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      
      {/* Rute Dashboard Utama (Admin / Guru / Kurikulum) */}
      <Route path="/" element={
        <ProtectedRoute allowedRoles={['admin', 'guru', 'kurikulum', 'pengawas']}>
          <Dashboard />
        </ProtectedRoute>
      } />
      
      {/* Rute Master Data */}
      <Route path="/master" element={
        <ProtectedRoute allowedRoles={['admin', 'kurikulum']}>
          <MasterMajors />
        </ProtectedRoute>
      } />
      <Route path="/master-kelas" element={
        <ProtectedRoute allowedRoles={['admin', 'kurikulum']}>
          <MasterClasses />
        </ProtectedRoute>
      } />
      <Route path="/master-guru" element={
        <ProtectedRoute allowedRoles={['admin', 'kurikulum']}>
          <MasterTeachers />
        </ProtectedRoute>
      } />
      <Route path="/master-mapel" element={
        <ProtectedRoute allowedRoles={['admin', 'kurikulum']}>
          <MasterSubjects />
        </ProtectedRoute>
      } />
      <Route path="/penugasan-guru" element={
        <ProtectedRoute allowedRoles={['admin', 'kurikulum']}>
          <TeacherAssignments />
        </ProtectedRoute>
      } />

      {/* Rute Akademik & Ujian */}
      <Route path="/bank-soal" element={
        <ProtectedRoute allowedRoles={['admin', 'guru', 'kurikulum']}>
          <BankSoal />
        </ProtectedRoute>
      } />
      <Route path="/schedules" element={
        <ProtectedRoute allowedRoles={['admin', 'guru', 'kurikulum']}>
          <Schedules />
        </ProtectedRoute>
      } />
      <Route path="/select-questions/:examId" element={
        <ProtectedRoute allowedRoles={['admin', 'guru', 'kurikulum']}>
          <SelectQuestions />
        </ProtectedRoute>
      } />
      <Route path="/data-siswa" element={
        <ProtectedRoute allowedRoles={['admin', 'kurikulum']}>
          <MasterStudents />
        </ProtectedRoute>
      } />
      <Route path="/import-siswa" element={
        <ProtectedRoute allowedRoles={['admin', 'kurikulum']}>
          <ImportStudents />
        </ProtectedRoute>
      } />
      <Route path="/exam-participants/:examId" element={
        <ProtectedRoute allowedRoles={['admin', 'guru', 'kurikulum', 'pengawas']}>
          <ExamParticipants />
        </ProtectedRoute>
      } />
      <Route path="/exam-interface/:examId" element={
        <ProtectedRoute allowedRoles={['siswa']}>
          <ExamInterface />
        </ProtectedRoute>
      } />
      <Route path="/logistics" element={
        <ProtectedRoute allowedRoles={['admin', 'kurikulum']}>
          <Logistics />
        </ProtectedRoute>
      } />
      <Route path="/session-management" element={
        <ProtectedRoute allowedRoles={['admin', 'kurikulum']}>
          <SessionManagement />
        </ProtectedRoute>
      } />
      <Route path="/settings" element={
        <ProtectedRoute allowedRoles={['admin', 'kurikulum']}>
          <Settings />
        </ProtectedRoute>
      } />
      <Route path="/exam-cards" element={
        <ProtectedRoute allowedRoles={['admin', 'kurikulum', 'pengawas']}>
          <ExamCards />
        </ProtectedRoute>
      } />
      <Route path="/attendance-list" element={
        <ProtectedRoute allowedRoles={['admin', 'kurikulum', 'pengawas']}>
          <AttendanceList />
        </ProtectedRoute>
      } />
      <Route path="/exam-results/:examId" element={
        <ProtectedRoute allowedRoles={['admin', 'guru', 'kurikulum', 'pengawas']}>
          <ExamResults />
        </ProtectedRoute>
      } />

      {/* Dashboard Khusus Siswa */}
      <Route path="/student-dashboard" element={
        <ProtectedRoute allowedRoles={['siswa']}>
          <StudentDashboard />
        </ProtectedRoute>
      } />
      
      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}

export default App;
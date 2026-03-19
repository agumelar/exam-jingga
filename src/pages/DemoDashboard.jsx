import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LogOut, Users, BookOpen, FileText, Calendar,
  BarChart3, Settings, School, TrendingUp, Clock,
  CheckCircle2, AlertCircle, Sparkles
} from 'lucide-react';
import Swal from 'sweetalert2';
import { mockDashboardData, mockExams, mockStudents, mockTeachers } from '../demoData';
import logoSekolah from '../assets/logo_sekolah.png';

const DemoDashboard = () => {
  const navigate = useNavigate();
  const [session, setSession] = useState(null);
  const [dashboardData, setDashboardData] = useState(null);

  useEffect(() => {
    // Load session
    const user = localStorage.getItem('user_session');
    if (user) {
      try {
        const userData = JSON.parse(user);
        if (userData.isDemoMode) {
          setSession(userData);
          // Load data berdasarkan role
          setDashboardData(mockDashboardData[userData.role] || {});
        } else {
          handleLogout();
        }
      } catch (e) {
        handleLogout();
      }
    } else {
      navigate('/');
    }
  }, [navigate]);

  const handleLogout = () => {
    Swal.fire({
      title: 'Logout?',
      text: 'Anda akan keluar dari demo mode',
      icon: 'question',
      showCancelButton: true,
      confirmButtonColor: '#ea580c',
      cancelButtonColor: '#64748b',
      confirmButtonText: 'Ya, Logout',
      cancelButtonText: 'Batal'
    }).then((result) => {
      if (result.isConfirmed) {
        localStorage.removeItem('user_session');
        window.location.href = '/';
      }
    });
  };

  if (!session || !dashboardData) {
    return (
      <div className="h-screen flex items-center justify-center bg-slate-50 dark:bg-zinc-950">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-orange-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-zinc-950 transition-colors duration-500">
      {/* Header */}
      <header className="bg-white dark:bg-zinc-900 border-b border-slate-200 dark:border-zinc-800 sticky top-0 z-50 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <img src={logoSekolah} alt="Logo" className="w-12 h-12 object-contain" />
            <div>
              <h1 className="text-xl font-black text-slate-900 dark:text-white uppercase italic tracking-tight">
                EXAM <span className="text-orange-600">JINGGA</span>
              </h1>
              <p className="text-xs text-slate-500 dark:text-zinc-400 font-bold uppercase tracking-wider">
                Demo Mode • {session.role.toUpperCase()}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-sm font-bold text-slate-900 dark:text-white">{session.fullName}</p>
              <p className="text-xs text-slate-500 dark:text-zinc-400">{session.email || session.nis}</p>
            </div>
            <button
              onClick={handleLogout}
              className="p-3 rounded-xl bg-slate-100 dark:bg-zinc-800 text-slate-600 dark:text-zinc-400 hover:bg-orange-600 hover:text-white transition-all"
            >
              <LogOut size={20} />
            </button>
          </div>
        </div>
      </header>

      {/* Demo Mode Banner */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-center gap-2">
          <Sparkles size={16} className="animate-pulse" />
          <p className="text-sm font-bold uppercase tracking-wider">
            Mode Demo Standalone - Data Simulasi (Tidak Terhubung ke Database)
          </p>
          <Sparkles size={16} className="animate-pulse" />
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Welcome Section */}
        <div className="mb-8">
          <h2 className="text-3xl font-black text-slate-900 dark:text-white mb-2">
            Selamat Datang, {session.fullName}!
          </h2>
          <p className="text-slate-600 dark:text-zinc-400">
            Dashboard {session.role === 'siswa' ? 'Siswa' : session.role === 'guru' ? 'Guru' : session.role === 'kurikulum' ? 'Kurikulum' : 'Administrator'}
          </p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {session.role === 'admin' && (
            <>
              <StatCard
                icon={<Users className="text-blue-600" size={24} />}
                title="Total Siswa"
                value={dashboardData.totalStudents}
                color="blue"
              />
              <StatCard
                icon={<School className="text-green-600" size={24} />}
                title="Total Guru"
                value={dashboardData.totalTeachers}
                color="green"
              />
              <StatCard
                icon={<FileText className="text-purple-600" size={24} />}
                title="Bank Soal"
                value={dashboardData.totalQuestions}
                color="purple"
              />
              <StatCard
                icon={<Calendar className="text-orange-600" size={24} />}
                title="Ujian Aktif"
                value={dashboardData.activeExams}
                color="orange"
              />
            </>
          )}

          {session.role === 'kurikulum' && (
            <>
              <StatCard
                icon={<Calendar className="text-blue-600" size={24} />}
                title="Total Jadwal"
                value={dashboardData.totalSchedules}
                color="blue"
              />
              <StatCard
                icon={<Clock className="text-orange-600" size={24} />}
                title="Ujian Aktif"
                value={dashboardData.activeExams}
                color="orange"
              />
              <StatCard
                icon={<CheckCircle2 className="text-green-600" size={24} />}
                title="Selesai"
                value={dashboardData.completedExams}
                color="green"
              />
              <StatCard
                icon={<TrendingUp className="text-purple-600" size={24} />}
                title="Mendatang"
                value={dashboardData.upcomingExams}
                color="purple"
              />
            </>
          )}

          {session.role === 'guru' && (
            <>
              <StatCard
                icon={<FileText className="text-blue-600" size={24} />}
                title="Soal Saya"
                value={dashboardData.myQuestions}
                color="blue"
              />
              <StatCard
                icon={<Calendar className="text-green-600" size={24} />}
                title="Jadwal Saya"
                value={dashboardData.mySchedules}
                color="green"
              />
              <StatCard
                icon={<AlertCircle className="text-orange-600" size={24} />}
                title="Tugas Pending"
                value={dashboardData.pendingTasks}
                color="orange"
              />
              <StatCard
                icon={<CheckCircle2 className="text-purple-600" size={24} />}
                title="Selesai"
                value={dashboardData.completedExams}
                color="purple"
              />
            </>
          )}

          {session.role === 'siswa' && (
            <>
              <StatCard
                icon={<Calendar className="text-blue-600" size={24} />}
                title="Ujian Tersedia"
                value={dashboardData.availableExams?.length || 0}
                color="blue"
              />
              <StatCard
                icon={<CheckCircle2 className="text-green-600" size={24} />}
                title="Ujian Selesai"
                value={dashboardData.completedExams?.length || 0}
                color="green"
              />
              <StatCard
                icon={<TrendingUp className="text-purple-600" size={24} />}
                title="Rata-rata Nilai"
                value="85"
                color="purple"
              />
              <StatCard
                icon={<BarChart3 className="text-orange-600" size={24} />}
                title="Peringkat Kelas"
                value="12/36"
                color="orange"
              />
            </>
          )}
        </div>

        {/* Content based on role */}
        {session.role === 'siswa' && (
          <div className="space-y-6">
            {/* Available Exams */}
            <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-lg border border-slate-200 dark:border-zinc-800 p-6">
              <h3 className="text-xl font-black text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                <Calendar size={24} className="text-orange-600" />
                Ujian Tersedia Hari Ini
              </h3>
              <div className="space-y-3">
                {dashboardData.availableExams?.map((exam) => (
                  <div key={exam.id} className="p-4 bg-slate-50 dark:bg-zinc-800 rounded-xl border border-slate-200 dark:border-zinc-700 hover:border-orange-500 transition-colors">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-bold text-slate-900 dark:text-white">{exam.title}</h4>
                        <p className="text-sm text-slate-600 dark:text-zinc-400 mt-1">
                          {exam.subject} • {exam.time} • {exam.duration} menit
                        </p>
                      </div>
                      <span className="px-3 py-1 bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400 text-xs font-bold rounded-full">
                        Tersedia
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Completed Exams */}
            <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-lg border border-slate-200 dark:border-zinc-800 p-6">
              <h3 className="text-xl font-black text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                <CheckCircle2 size={24} className="text-green-600" />
                Ujian Selesai
              </h3>
              <div className="space-y-3">
                {dashboardData.completedExams?.map((exam) => (
                  <div key={exam.id} className="p-4 bg-slate-50 dark:bg-zinc-800 rounded-xl border border-slate-200 dark:border-zinc-700">
                    <div className="flex justify-between items-start">
                      <div>
                        <h4 className="font-bold text-slate-900 dark:text-white">{exam.title}</h4>
                        <p className="text-sm text-slate-600 dark:text-zinc-400 mt-1">
                          {exam.subject} • {exam.date}
                        </p>
                      </div>
                      <div className="text-right">
                        <span className="text-2xl font-black text-green-600">{exam.score}</span>
                        <p className="text-xs text-slate-500 dark:text-zinc-400">Nilai</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {(session.role === 'admin' || session.role === 'kurikulum' || session.role === 'guru') && (
          <div className="space-y-6">
            {/* Recent Activities */}
            <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-lg border border-slate-200 dark:border-zinc-800 p-6">
              <h3 className="text-xl font-black text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                <BarChart3 size={24} className="text-orange-600" />
                Aktivitas Terbaru
              </h3>
              <div className="space-y-3">
                {dashboardData.recentActivities?.map((activity) => (
                  <div key={activity.id} className="p-4 bg-slate-50 dark:bg-zinc-800 rounded-xl border border-slate-200 dark:border-zinc-700">
                    <p className="text-sm font-bold text-slate-900 dark:text-white">{activity.action}</p>
                    <p className="text-xs text-slate-500 dark:text-zinc-400 mt-1">{activity.time}</p>
                  </div>
                )) || (
                  <div className="text-center py-8 text-slate-500 dark:text-zinc-400">
                    <p className="text-sm">Belum ada aktivitas terbaru</p>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Actions */}
            <div className="bg-white dark:bg-zinc-900 rounded-2xl shadow-lg border border-slate-200 dark:border-zinc-800 p-6">
              <h3 className="text-xl font-black text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                <Settings size={24} className="text-purple-600" />
                Aksi Cepat (Demo)
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <QuickActionButton icon={<Users />} label="Data Siswa" color="blue" />
                <QuickActionButton icon={<School />} label="Data Guru" color="green" />
                <QuickActionButton icon={<FileText />} label="Bank Soal" color="purple" />
                <QuickActionButton icon={<Calendar />} label="Jadwal Ujian" color="orange" />
              </div>
              <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl">
                <p className="text-xs text-blue-700 dark:text-blue-300 text-center">
                  <strong>Demo Mode:</strong> Fitur penuh tersedia di aplikasi asli
                </p>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

// Stat Card Component
const StatCard = ({ icon, title, value, color }) => {
  const colorClasses = {
    blue: 'border-blue-200 dark:border-blue-900/50 bg-blue-50/50 dark:bg-blue-900/20',
    green: 'border-green-200 dark:border-green-900/50 bg-green-50/50 dark:bg-green-900/20',
    purple: 'border-purple-200 dark:border-purple-900/50 bg-purple-50/50 dark:bg-purple-900/20',
    orange: 'border-orange-200 dark:border-orange-900/50 bg-orange-50/50 dark:bg-orange-900/20'
  };

  return (
    <div className={`p-6 rounded-2xl border ${colorClasses[color]} backdrop-blur-sm shadow-lg hover:shadow-xl transition-all`}>
      <div className="flex items-start justify-between mb-3">
        <div className="p-3 rounded-xl bg-white dark:bg-zinc-900 shadow-md">
          {icon}
        </div>
      </div>
      <p className="text-3xl font-black text-slate-900 dark:text-white mb-1">{value}</p>
      <p className="text-sm font-bold text-slate-600 dark:text-zinc-400">{title}</p>
    </div>
  );
};

// Quick Action Button Component
const QuickActionButton = ({ icon, label, color }) => {
  const colorClasses = {
    blue: 'hover:bg-blue-600',
    green: 'hover:bg-green-600',
    purple: 'hover:bg-purple-600',
    orange: 'hover:bg-orange-600'
  };

  return (
    <button className={`p-4 bg-slate-100 dark:bg-zinc-800 rounded-xl hover:text-white ${colorClasses[color]} transition-all group`}>
      <div className="flex flex-col items-center gap-2">
        <div className="group-hover:scale-110 transition-transform">
          {React.cloneElement(icon, { size: 24 })}
        </div>
        <span className="text-xs font-bold">{label}</span>
      </div>
    </button>
  );
};

export default DemoDashboard;

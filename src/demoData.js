// Mock data untuk demo (tanpa database)
export const mockUsers = {
  admin: {
    id: 'demo-admin-001',
    uid: 'demo-admin-001',
    fullName: 'Administrator Demo',
    role: 'admin',
    email: 'admin@demo.com'
  },
  kurikulum: {
    id: 'demo-kurikulum-001',
    uid: 'demo-kurikulum-001',
    fullName: 'Kurikulum Demo',
    role: 'kurikulum',
    email: 'kurikulum@demo.com'
  },
  guru: {
    id: 'demo-guru-001',
    uid: 'demo-guru-001',
    fullName: 'Guru Demo',
    role: 'guru',
    email: 'guru@demo.com'
  },
  siswa: {
    id: 'demo-siswa-001',
    uid: 'demo-siswa-001',
    fullName: 'Siswa Demo',
    nis: '123456789',
    role: 'siswa'
  }
};

export const mockDashboardData = {
  admin: {
    totalStudents: 850,
    totalTeachers: 45,
    totalQuestions: 2450,
    activeExams: 12,
    recentActivities: [
      { id: 1, action: 'Ujian PTS Matematika dimulai', time: '10 menit yang lalu' },
      { id: 2, action: 'Guru baru ditambahkan: Ibu Siti', time: '2 jam yang lalu' },
      { id: 3, action: '25 siswa menyelesaikan ujian Bahasa Inggris', time: '3 jam yang lalu' },
    ]
  },
  kurikulum: {
    totalSchedules: 48,
    activeExams: 12,
    completedExams: 36,
    upcomingExams: 15
  },
  guru: {
    myQuestions: 156,
    mySchedules: 8,
    pendingTasks: 3,
    completedExams: 5
  },
  siswa: {
    availableExams: [
      {
        id: 1,
        title: 'Ujian Tengah Semester - Matematika',
        subject: 'Matematika',
        date: '2026-03-20',
        time: '08:00 - 10:00',
        duration: 120,
        status: 'available'
      },
      {
        id: 2,
        title: 'Ulangan Harian - Bahasa Indonesia',
        subject: 'Bahasa Indonesia',
        date: '2026-03-20',
        time: '10:30 - 11:30',
        duration: 60,
        status: 'available'
      }
    ],
    completedExams: [
      {
        id: 3,
        title: 'Ujian Bahasa Inggris',
        subject: 'Bahasa Inggris',
        date: '2026-03-15',
        score: 85,
        status: 'completed'
      }
    ]
  }
};

export const mockExams = [
  {
    id: 1,
    title: 'Ujian Tengah Semester - Matematika',
    subject: 'Matematika',
    type: 'PTS',
    class: '10 RPL 1',
    date: '2026-03-20',
    time: '08:00',
    duration: 120,
    questionCount: 40,
    status: 'ready',
    token: '123456'
  },
  {
    id: 2,
    title: 'Ulangan Harian - Bahasa Indonesia',
    subject: 'Bahasa Indonesia',
    type: 'UH',
    class: '10 RPL 1',
    date: '2026-03-20',
    time: '10:30',
    duration: 60,
    questionCount: 25,
    status: 'ready',
    token: '789012'
  }
];

export const mockQuestions = [
  {
    id: 1,
    question: 'Berapakah hasil dari 2 + 2?',
    options: ['3', '4', '5', '6'],
    correctAnswer: 1,
    subject: 'Matematika'
  },
  {
    id: 2,
    question: 'Apa ibu kota Indonesia?',
    options: ['Bandung', 'Surabaya', 'Jakarta', 'Medan'],
    correctAnswer: 2,
    subject: 'Geografi'
  }
];

export const mockStudents = [
  { id: 1, nis: '123456', fullName: 'Ahmad Fauzi', class: '10 RPL 1', status: 'aktif' },
  { id: 2, nis: '123457', fullName: 'Siti Nurhaliza', class: '10 RPL 1', status: 'aktif' },
  { id: 3, nis: '123458', fullName: 'Budi Santoso', class: '10 RPL 2', status: 'aktif' },
  { id: 4, nis: '123459', fullName: 'Dewi Lestari', class: '11 TKJ 1', status: 'aktif' },
  { id: 5, nis: '123460', fullName: 'Eko Prasetyo', class: '11 TKJ 1', status: 'aktif' }
];

export const mockTeachers = [
  { id: 1, fullName: 'Drs. Agus Setiawan', email: 'agus@smkn1rongga.sch.id', role_level: 'admin', subjects: ['Matematika'] },
  { id: 2, fullName: 'Sri Wahyuni, S.Pd', email: 'sri@smkn1rongga.sch.id', role_level: 'guru', subjects: ['Bahasa Indonesia'] },
  { id: 3, fullName: 'Bambang Sutrisno, M.Pd', email: 'bambang@smkn1rongga.sch.id', role_level: 'kurikulum', subjects: [] },
  { id: 4, fullName: 'Rina Kartika, S.Kom', email: 'rina@smkn1rongga.sch.id', role_level: 'guru', subjects: ['Pemrograman Web'] }
];

export const mockClasses = [
  { id: 1, name: '10 RPL 1', major: 'Rekayasa Perangkat Lunak', studentCount: 36 },
  { id: 2, name: '10 RPL 2', major: 'Rekayasa Perangkat Lunak', studentCount: 35 },
  { id: 3, name: '11 TKJ 1', major: 'Teknik Komputer Jaringan', studentCount: 34 },
  { id: 4, name: '11 TKJ 2', major: 'Teknik Komputer Jaringan', studentCount: 36 },
  { id: 5, name: '12 MM 1', major: 'Multimedia', studentCount: 32 }
];

export const mockSubjects = [
  { id: 1, name: 'Matematika', category: 'Umum' },
  { id: 2, name: 'Bahasa Indonesia', category: 'Umum' },
  { id: 3, name: 'Bahasa Inggris', category: 'Umum' },
  { id: 4, name: 'Pemrograman Web', category: 'Kejuruan' },
  { id: 5, name: 'Basis Data', category: 'Kejuruan' },
  { id: 6, name: 'Jaringan Komputer', category: 'Kejuruan' }
];

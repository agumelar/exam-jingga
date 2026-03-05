import React, { useState } from 'react';
import { supabase } from '../supabaseClient';
import Swal from 'sweetalert2';

const Login = () => {
  const [identifier, setIdentifier] = useState(''); // Bisa Email atau NIS
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);

    // --- JALUR 1: ADMIN / GURU (NON-AUTH SAKTI) ---
    // Langsung cek ke tabel teachers, nggak lewat auth.signIn lagi biar anti-stuck
    const { data: staff, error: staffError } = await supabase
      .from('teachers')
      .select('*')
      .eq('email', identifier)
      .eq('password', password) // Cek password manual yang di-input Admin
      .maybeSingle();

    if (staff) {
      // Simpan session manual di localStorage agar App.jsx & Sidebar tau siapa yang masuk
      localStorage.setItem('user_session', JSON.stringify({
        id: staff.id,
        name: staff.full_name,
        role: staff.role_level.toLowerCase(),
        email: staff.email
      }));

      Swal.fire({
        title: 'Login Berhasil!',
        text: `Halo ${staff.role_level}: ${staff.full_name}`,
        icon: 'success',
        timer: 1500,
        showConfirmButton: false,
        timerProgressBar: true,
        background: document.documentElement.classList.contains('dark') ? '#18181b' : '#fff',
        color: document.documentElement.classList.contains('dark') ? '#fff' : '#000'
      });

      setTimeout(() => {
        window.location.href = '/'; 
      }, 1500);
      return;
    }

    // --- JALUR 2: SISWA (GERILYA - TETAP UTUH) ---
    const { data: student } = await supabase
      .from('students')
      .select('*, classes(name)')
      .eq('nis', identifier)
      .eq('password_plain', password)
      .eq('status', 'aktif')
      .maybeSingle();

    if (student) {
      localStorage.setItem('user_session', JSON.stringify({
        id: student.id,
        name: student.full_name,
        role: 'siswa',
        class: student.classes?.name
      }));
      
      Swal.fire({
        title: 'Login Berhasil!',
        text: `Selamat datang, ${student.full_name}`,
        icon: 'success',
        timer: 1500,
        showConfirmButton: false,
        timerProgressBar: true,
        background: document.documentElement.classList.contains('dark') ? '#18181b' : '#fff',
        color: document.documentElement.classList.contains('dark') ? '#fff' : '#000'
      });
    
      setTimeout(() => {
        window.location.href = '/student-dashboard';
      }, 1500);

    } else {
      // Jika kedua jalur gagal
      Swal.fire({
        title: 'Gagal!',
        text: 'Akun tidak ditemukan atau password salah!',
        icon: 'error',
        confirmButtonColor: '#ea580c'
      });
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <form onSubmit={handleLogin} style={styles.card}>
        <h2 style={{fontWeight: '900', color: '#ea580c', fontStyle: 'italic', fontSize: '24px'}}>EXAM JINGGA</h2>
        <p style={{fontSize: '12px', color: '#666', marginBottom: '20px'}}>Masuk dengan Email atau NIS</p>
        <input 
          type="text" 
          placeholder="Email atau NIS" 
          value={identifier} 
          onChange={(e) => setIdentifier(e.target.value)} 
          required 
          style={styles.input}
        />
        <input 
          type="password" 
          placeholder="Password" 
          value={password} 
          onChange={(e) => setPassword(e.target.value)} 
          required 
          style={styles.input}
        />
        <button type="submit" disabled={loading} style={styles.button}>
          {loading ? 'Mohon Tunggu...' : 'Masuk'}
        </button>
      </form>
    </div>
  );
};

const styles = {
  container: { display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', backgroundColor: '#f0f2f5' },
  card: { padding: '2rem', backgroundColor: '#fff', borderRadius: '15px', boxShadow: '0 10px 25px rgba(0,0,0,0.05)', width: '320px', textAlign: 'center' },
  input: { width: '100%', padding: '12px', margin: '10px 0', borderRadius: '8px', border: '1px solid #ddd', boxSizing: 'border-box', outline: 'none' },
  button: { width: '100%', padding: '12px', backgroundColor: '#ea580c', color: '#fff', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }
};

export default Login;
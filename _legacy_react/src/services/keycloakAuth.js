import { supabase } from '../supabaseClient';

const KEYCLOAK_URL = import.meta.env.VITE_KEYCLOAK_URL || 'https://sso.smkn1rongga.sch.id';
const KEYCLOAK_REALM = import.meta.env.VITE_KEYCLOAK_REALM || 'sekolah';
const KEYCLOAK_CLIENT_ID = import.meta.env.VITE_KEYCLOAK_CLIENT_ID || 'exam-jingga';

const AUTH_ENDPOINT = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/auth`;
const TOKEN_ENDPOINT = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token`;
const LOGOUT_ENDPOINT = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/logout`;
const USERINFO_ENDPOINT = `${KEYCLOAK_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/userinfo`;

// --- PKCE Helpers (RFC 7636) ---
function generateRandomString(length = 64) {
  const charset = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
  let result = '';
  const randomValues = new Uint8Array(length);
  window.crypto.getRandomValues(randomValues);
  for (let i = 0; i < length; i++) {
    result += charset[randomValues[i] % charset.length];
  }
  return result;
}

async function sha256(plain) {
  const encoder = new TextEncoder();
  const data = encoder.encode(plain);
  return window.crypto.subtle.digest('SHA-256', data);
}

function base64UrlEncode(buffer) {
  let str = '';
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.byteLength; i++) {
    str += String.fromCharCode(bytes[i]);
  }
  return btoa(str)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

export function parseJwt(token) {
  try {
    const base64Url = token.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    console.error('Failed to parse JWT', e);
    return null;
  }
}

/**
 * Memulai Flow Login OIDC PKCE ke Keycloak
 * Ditambahkan prompt=login agar Keycloak selalu meminta akun & kata sandi baru (Anti-Tabrak Akun Lab)
 */
export async function initiateKeycloakLogin(redirectPath = '/') {
  const state = generateRandomString(32);
  const codeVerifier = generateRandomString(64);
  const hashed = await sha256(codeVerifier);
  const codeChallenge = base64UrlEncode(hashed);

  sessionStorage.setItem('kc_state', state);
  sessionStorage.setItem('kc_code_verifier', codeVerifier);
  sessionStorage.setItem('kc_target_path', redirectPath);

  const redirectUri = `${window.location.origin}/auth/callback`;

  const params = new URLSearchParams({
    client_id: KEYCLOAK_CLIENT_ID,
    response_type: 'code',
    scope: 'openid profile email roles',
    redirect_uri: redirectUri,
    state: state,
    code_challenge: codeChallenge,
    code_challenge_method: 'S256',
    prompt: 'login' // WAJIB: Memaksa form login muncul ulang
  });

  window.location.href = `${AUTH_ENDPOINT}?${params.toString()}`;
}

/**
 * Memproses authorization code dari callback URL
 */
export async function handleKeycloakCallback(code, state) {
  const savedState = sessionStorage.getItem('kc_state');
  const codeVerifier = sessionStorage.getItem('kc_code_verifier');
  const targetPath = sessionStorage.getItem('kc_target_path') || '/';

  if (!state || state !== savedState) {
    throw new Error('Validasi keamanan state OAuth2 gagal. Silakan coba login kembali.');
  }

  if (!codeVerifier) {
    throw new Error('Code verifier PKCE tidak ditemukan di sesi browser.');
  }

  const redirectUri = `${window.location.origin}/auth/callback`;

  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    client_id: KEYCLOAK_CLIENT_ID,
    code: code,
    redirect_uri: redirectUri,
    code_verifier: codeVerifier
  });

  const response = await fetch(TOKEN_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded'
    },
    body: body.toString()
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.error_description || 'Gagal menukarkan token otentikasi dari Keycloak.');
  }

  const tokenData = await response.json();
  
  // Simpan token ke storage
  localStorage.setItem('kc_access_token', tokenData.access_token);
  localStorage.setItem('kc_id_token', tokenData.id_token);
  if (tokenData.refresh_token) {
    localStorage.setItem('kc_refresh_token', tokenData.refresh_token);
  }

  // Bersihkan data sementara PKCE
  sessionStorage.removeItem('kc_state');
  sessionStorage.removeItem('kc_code_verifier');
  sessionStorage.removeItem('kc_target_path');

  // Sinkronisasi profil ke database lokal CBT
  const userSession = await syncUserWithLocalDB(tokenData);
  return { userSession, targetPath };
}

/**
 * Melakukan auto-linking profil SSO Keycloak ke tabel lokal CBT (`students` atau `teachers`)
 */
export async function syncUserWithLocalDB(tokenData) {
  const payload = parseJwt(tokenData.id_token || tokenData.access_token);
  if (!payload) throw new Error('Token otorisasi tidak valid.');

  const ssoId = payload.sub;
  const username = String(payload.preferred_username || '').trim();
  const email = String(payload.email || '').trim().toLowerCase();
  const fullName = payload.name || payload.given_name || username;
  
  // Deteksi peran dari Keycloak (Realm & Client Roles)
  const realmRoles = payload.realm_access?.roles || [];
  const clientRoles = payload.resource_access?.[KEYCLOAK_CLIENT_ID]?.roles || [];
  const allRoles = [...realmRoles, ...clientRoles].map(r => String(r).toLowerCase());

  // Pengenalan Role Lengkap SMKN 1 Rongga (Termasuk platform_admin & data_admin)
  const hasAdminRole = allRoles.some(r => 
    ['admin', 'kurikulum', 'platform_admin', 'data_admin', 'superadmin', 'administrator'].includes(r)
  ) || username.toLowerCase() === 'admin' || username.toLowerCase().includes('admin');

  const hasTeacherRole = allRoles.some(r => 
    ['guru', 'teacher', 'pengawas', 'ptk', 'staff'].includes(r)
  );

  const hasStudentRole = allRoles.some(r => 
    ['siswa', 'student', 'peserta'].includes(r)
  );

  const isLikelyNIP = /^\d{16,18}$/.test(username);
  const isLikelyNIS = /^\d{4,12}$/.test(username);

  // ==========================================
  // JALUR 1: GURU / ADMIN / KURIKULUM / PTK
  // ==========================================
  if (hasAdminRole || hasTeacherRole || isLikelyNIP || email.includes('@smkn1rongga.sch.id') || username.toLowerCase() === 'admin') {
    
    let teacher = null;

    if (ssoId) {
      const { data } = await supabase.from('teachers').select('*').eq('sso_id', ssoId).maybeSingle();
      if (data) teacher = data;
    }

    if (!teacher && email) {
      const { data } = await supabase.from('teachers').select('*').ilike('email', email).maybeSingle();
      if (data) teacher = data;
    }

    if (!teacher && username) {
      const { data } = await supabase.from('teachers').select('*').eq('nip', username).maybeSingle();
      if (data) teacher = data;
    }

    // Pencocokan khusus user 'admin'
    if (!teacher && username.toLowerCase() === 'admin') {
      const { data } = await supabase.from('teachers').select('*').or('role_level.eq.admin,email.ilike.admin@%').maybeSingle();
      if (data) teacher = data;
    }

    // Jika guru/admin ditemukan di database lokal
    if (teacher) {
      const updatePayload = {};
      if (teacher.sso_id !== ssoId) updatePayload.sso_id = ssoId;
      if (!teacher.nip && isLikelyNIP) updatePayload.nip = username;
      if (!teacher.email && email) updatePayload.email = email;
      if (fullName && fullName !== username && teacher.full_name !== fullName) updatePayload.full_name = fullName;
      
      // Jika memiliki role platform_admin/data_admin/admin, pastikan role_level di DB adalah 'admin'
      if (hasAdminRole && teacher.role_level !== 'admin' && teacher.role_level !== 'kurikulum') {
        updatePayload.role_level = 'admin';
      }

      if (Object.keys(updatePayload).length > 0) {
        await supabase.from('teachers').update(updatePayload).eq('id', teacher.id);
      }

      const roleLevel = hasAdminRole ? 'admin' : (teacher.role_level || 'guru').toLowerCase();

      const sessionObj = {
        id: teacher.id,
        uid: ssoId,
        sso_id: ssoId,
        fullName: teacher.full_name || fullName,
        email: teacher.email || email,
        nip: teacher.nip || username,
        role: roleLevel
      };

      localStorage.setItem('user_session', JSON.stringify(sessionObj));
      return sessionObj;
    }

    // Auto-create guru/admin baru jika belum terdaftar
    const newRole = hasAdminRole ? 'admin' : 'guru';
    const { data: createdTeacher, error: createErr } = await supabase
      .from('teachers')
      .insert({
        sso_id: ssoId,
        full_name: fullName || 'Administrator Sekolah',
        email: email || `${username}@smkn1rongga.sch.id`,
        nip: isLikelyNIP ? username : null,
        role_level: newRole
      })
      .select()
      .single();

    if (!createErr && createdTeacher) {
      const sessionObj = {
        id: createdTeacher.id,
        uid: ssoId,
        sso_id: ssoId,
        fullName: createdTeacher.full_name,
        email: createdTeacher.email,
        nip: createdTeacher.nip || username,
        role: newRole
      };
      localStorage.setItem('user_session', JSON.stringify(sessionObj));
      return sessionObj;
    }
  }

  // ==========================================
  // JALUR 2: SISWA (NIS)
  // ==========================================
  let student = null;

  if (ssoId) {
    const { data } = await supabase
      .from('students')
      .select('*, classes(name, major:majors(code, name))')
      .eq('sso_id', ssoId)
      .maybeSingle();
    if (data) student = data;
  }

  if (!student && username) {
    const { data } = await supabase
      .from('students')
      .select('*, classes(name, major:majors(code, name))')
      .eq('nis', username)
      .maybeSingle();
    if (data) student = data;
  }

  if (student) {
    if (student.sso_id !== ssoId) {
      await supabase
        .from('students')
        .update({ sso_id: ssoId, full_name: student.full_name || fullName })
        .eq('id', student.id);
    }

    if (student.status && student.status !== 'aktif' && student.status !== "'aktif'") {
      throw new Error('Akun ujian Anda dinonaktifkan oleh sekolah. Silakan hubungi proktor/panitia!');
    }

    const sessionObj = {
      id: student.id,
      uid: ssoId,
      sso_id: ssoId,
      fullName: student.full_name || fullName,
      nis: student.nis,
      role: 'siswa',
      class_id: student.class_id,
      className: student.classes?.name || '',
      majorName: student.classes?.major?.name || ''
    };

    localStorage.setItem('user_session', JSON.stringify(sessionObj));
    return sessionObj;
  }

  if (hasStudentRole || isLikelyNIS) {
    const { data: newStudent, error: createStudentErr } = await supabase
      .from('students')
      .insert({
        sso_id: ssoId,
        nis: username,
        full_name: fullName,
        email: email || `${username}@student.smkn1rongga.sch.id`,
        status: 'aktif'
      })
      .select('*, classes(name, major:majors(code, name))')
      .single();

    if (!createStudentErr && newStudent) {
      const sessionObj = {
        id: newStudent.id,
        uid: ssoId,
        sso_id: ssoId,
        fullName: newStudent.full_name,
        nis: newStudent.nis,
        role: 'siswa',
        class_id: newStudent.class_id,
        className: newStudent.classes?.name || '',
        majorName: newStudent.classes?.major?.name || ''
      };
      localStorage.setItem('user_session', JSON.stringify(sessionObj));
      return sessionObj;
    }
  }

  throw new Error(`Data profil SSO (${username}) belum terdaftar di CBT Exam Jingga. Hubungi administrator kurikulum.`);
}

/**
 * Logout Total (Single Logout OIDC)
 * Menghancurkan sesi lokal dan sesi Keycloak terpusat
 */
export function logoutKeycloak() {
  const idToken = localStorage.getItem('kc_id_token');
  
  localStorage.removeItem('user_session');
  localStorage.removeItem('kc_access_token');
  localStorage.removeItem('kc_id_token');
  localStorage.removeItem('kc_refresh_token');

  const redirectUri = encodeURIComponent(window.location.origin + '/login');
  
  if (idToken) {
    window.location.href = `${LOGOUT_ENDPOINT}?id_token_hint=${idToken}&post_logout_redirect_uri=${redirectUri}`;
  } else {
    window.location.href = `${LOGOUT_ENDPOINT}?client_id=${KEYCLOAK_CLIENT_ID}&post_logout_redirect_uri=${redirectUri}`;
  }
}

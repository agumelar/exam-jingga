import { execSync, spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CLOUD_URL = process.env.CLOUD_SUPABASE_URL || '';
const CLOUD_KEY = process.env.CLOUD_SUPABASE_KEY || '';
const SSH_KEY = process.env.VPS_SSH_KEY || '';
const VPS_USER_HOST = process.env.VPS_HOST || '';

const TABLES_IN_ORDER = [
  'majors',
  'classes',
  'subjects',
  'teachers',
  'students',
  'teacher_assignments',
  'questions',
  'exams',
  'exam_questions',
  'schedules',
  'exam_sessions',
  'student_answers',
  'student_logistics',
  'settings'
];

function runRemotePsql(sqlContent) {
  const tmpSql = path.join(__dirname, 'tmp_exec.sql');
  fs.writeFileSync(tmpSql, sqlContent, 'utf8');
  
  // SCP sql to VPS
  execSync(`scp -i "${SSH_KEY}" -o StrictHostKeyChecking=no "${tmpSql}" ${VPS_USER_HOST}:/tmp/remote_exec.sql`, { stdio: 'inherit' });
  
  // Execute via docker psql
  const cmd = `ssh -i "${SSH_KEY}" -o StrictHostKeyChecking=no ${VPS_USER_HOST} "sudo docker exec -i supabase-db psql -U postgres -d postgres < /tmp/remote_exec.sql"`;
  const output = execSync(cmd, { stdio: 'pipe' }).toString();
  
  if (fs.existsSync(tmpSql)) fs.unlinkSync(tmpSql);
  return output;
}

function escapeSqlValue(val) {
  if (val === null || val === undefined) return 'NULL';
  if (typeof val === 'boolean') return val ? 'TRUE' : 'FALSE';
  if (typeof val === 'number') return String(val);
  if (typeof val === 'object') {
    return "'" + JSON.stringify(val).replace(/'/g, "''") + "'::jsonb";
  }
  return "'" + String(val).replace(/'/g, "''") + "'";
}

async function fetchTableCount(table) {
  const res = await fetch(`${CLOUD_URL}${table}?select=count`, {
    headers: {
      'apikey': CLOUD_KEY,
      'Authorization': `Bearer ${CLOUD_KEY}`,
      'Range': '0-0',
      'Prefer': 'count=exact'
    }
  });
  const cr = res.headers.get('content-range');
  if (!cr) return 0;
  const total = parseInt(cr.split('/')[1], 10);
  return isNaN(total) ? 0 : total;
}

async function fetchTableChunk(table, offset, limit) {
  const end = offset + limit - 1;
  const res = await fetch(`${CLOUD_URL}${table}?select=*`, {
    headers: {
      'apikey': CLOUD_KEY,
      'Authorization': `Bearer ${CLOUD_KEY}`,
      'Range': `${offset}-${end}`,
      'Range-Unit': 'items'
    }
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch ${table} [${offset}-${end}]: ${res.statusText}`);
  }
  return await res.json();
}

async function main() {
  console.log('================================================================');
  console.log('🚀 MEMULAI MIGRASI DATA: SUPABASE CLOUD -> POSTGRESQL 17 VPS');
  console.log('================================================================\n');

  // 1. Inisialisasi Skema Dasar
  console.log('[1/4] Menerapkan Skema Dasar (schema.sql) ke PostgreSQL 17 VPS...');
  const schemaSql = fs.readFileSync(path.join(__dirname, '..', 'supabase', 'schema.sql'), 'utf8');
  runRemotePsql(schemaSql);
  console.log('✅ Skema dasar berhasil dibuat di database VPS.\n');

  // 2. Migrasi Baris Data per Tabel
  console.log('[2/4] Mengambil dan Mengimpor Data Seluruh Tabel...');
  const BATCH_SIZE = 500;

  for (const table of TABLES_IN_ORDER) {
    const totalRows = await fetchTableCount(table);
    console.log(`\n📦 Migrasi tabel [${table}] - Total: ${totalRows} baris`);

    if (totalRows === 0) {
      console.log(`   ⏭️ Tidak ada data di tabel ${table}, lewati.`);
      continue;
    }

    let offset = 0;
    let imported = 0;

    while (offset < totalRows) {
      const rows = await fetchTableChunk(table, offset, BATCH_SIZE);
      if (!rows || rows.length === 0) break;

      const columns = Object.keys(rows[0]);
      const quotedCols = columns.map(c => `"${c}"`).join(', ');

      const valueRows = rows.map(r => {
        const vals = columns.map(c => escapeSqlValue(r[c]));
        return `(${vals.join(', ')})`;
      }).join(',\n');

      const insertSql = `
        INSERT INTO public."${table}" (${quotedCols})
        VALUES ${valueRows}
        ON CONFLICT DO NOTHING;
      `;

      runRemotePsql(insertSql);
      imported += rows.length;
      offset += BATCH_SIZE;

      process.stdout.write(`\r   ⏳ Progress [${table}]: ${imported} / ${totalRows} baris (${Math.round((imported / totalRows) * 100)}%)`);
    }
    console.log(`\n   ✅ Tabel [${table}] berhasil dimigrasikan (${imported} baris).`);
  }

  // 3. Terapkan Tuning Skema, Index, Storage, & RPC
  console.log('\n[3/4] Menerapkan Optimasi Produksi (tune-schema.sql)...');
  const tuneSql = fs.readFileSync(path.join(__dirname, '..', 'supabase', 'tune-schema.sql'), 'utf8');
  runRemotePsql(tuneSql);
  console.log('✅ Optimasi skema, indeks, storage bucket, dan RPC fn_start_student_exam berhasil diterapkan.');

  // 4. Verifikasi Jumlah Baris
  console.log('\n[4/4] Verifikasi Integritas Data Cloud vs VPS:');
  console.log('----------------------------------------------------------------');
  console.log('| Tabel               | Cloud Rows | VPS Rows   | Status       |');
  console.log('----------------------------------------------------------------');

  let allMatched = true;
  for (const table of TABLES_IN_ORDER) {
    const cloudCount = await fetchTableCount(table);
    const vpsSql = `SELECT count(*)::text as c FROM public."${table}";`;
    const vpsRes = runRemotePsql(vpsSql);
    const match = vpsRes.match(/\s+(\d+)\s+/);
    const vpsCount = match ? parseInt(match[1], 10) : -1;

    const isOk = cloudCount === vpsCount;
    if (!isOk) allMatched = false;

    const statusStr = isOk ? '✅ MATCH' : '⚠️ DIFFERENCE';
    console.log(`| ${table.padEnd(19)} | ${String(cloudCount).padEnd(10)} | ${String(vpsCount).padEnd(10)} | ${statusStr.padEnd(12)} |`);
  }
  console.log('----------------------------------------------------------------');

  if (allMatched) {
    console.log('\n🎉 MIGRASI DATABASE 100% SUKSES DENGAN INTEGRITAS SEMPURNA! 🎉\n');
  } else {
    console.log('\n⚠️ Migrasi selesai dengan beberapa perbedaan baris, periksa log di atas.\n');
  }
}

main().catch(err => {
  console.error('\n❌ ERROR MIGRASI:', err);
  process.exit(1);
});

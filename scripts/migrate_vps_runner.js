import { execSync, spawnSync } from 'child_process';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const CLOUD_URL = process.env.CLOUD_SUPABASE_URL || '';
const CLOUD_KEY = process.env.CLOUD_SUPABASE_KEY || '';

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

function runLocalPsql(sqlContent) {
  const result = spawnSync('sudo', ['docker', 'exec', '-i', 'supabase-db', 'psql', '-U', 'postgres', '-d', 'postgres'], {
    input: sqlContent,
    encoding: 'utf8'
  });
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error(`psql error: ${result.stderr}`);
  }
  return result.stdout;
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
  console.log('🚀 HIGH-SPEED CLOUD TO VPS DATABASE MIGRATION ENGINE');
  console.log('================================================================\n');

  // 1. Inisialisasi Skema Dasar
  console.log('[1/4] Memastikan Skema Dasar (schema.sql) di PostgreSQL 17...');
  if (fs.existsSync('/tmp/schema.sql')) {
    runLocalPsql(fs.readFileSync('/tmp/schema.sql', 'utf8'));
    console.log('✅ Skema dasar siap.\n');
  }

  // 2. Migrasi Baris Data per Tabel
  console.log('[2/4] Mengimpor Data Seluruh Tabel dengan Batch Turbo...');
  
  for (const table of TABLES_IN_ORDER) {
    const totalRows = await fetchTableCount(table);
    const BATCH_SIZE = (table === 'student_answers') ? 2500 : (table === 'questions' ? 500 : 1000);
    
    console.log(`\n📦 Migrasi tabel [${table}] - Total Cloud: ${totalRows} baris`);

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

      runLocalPsql(insertSql);
      imported += rows.length;
      offset += BATCH_SIZE;

      process.stdout.write(`\r   ⏳ Progress [${table}]: ${imported} / ${totalRows} baris (${Math.round((imported / totalRows) * 100)}%)`);
    }
    console.log(`\n   ✅ Tabel [${table}] selesai diproses.`);
  }

  // 3. Terapkan Tuning Skema, Index, Storage, & RPC
  console.log('\n[3/4] Menerapkan Optimasi Produksi (tune-schema.sql)...');
  if (fs.existsSync('/tmp/tune-schema.sql')) {
    runLocalPsql(fs.readFileSync('/tmp/tune-schema.sql', 'utf8'));
    console.log('✅ Optimasi skema, indeks, storage bucket, dan RPC berhasil diterapkan.');
  }

  // 4. Verifikasi Jumlah Baris
  console.log('\n[4/4] Verifikasi Integritas Data Cloud vs VPS:');
  console.log('----------------------------------------------------------------');
  console.log('| Tabel               | Cloud Rows | VPS Rows   | Status       |');
  console.log('----------------------------------------------------------------');

  let allMatched = true;
  for (const table of TABLES_IN_ORDER) {
    const cloudCount = await fetchTableCount(table);
    const vpsSql = `SELECT count(*)::text as c FROM public."${table}";`;
    const vpsRes = runLocalPsql(vpsSql);
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
    console.log('\n⚠️ Verifikasi selesai, ada catatan di atas.\n');
  }
}

main().catch(err => {
  console.error('\n❌ ERROR MIGRASI:', err);
  process.exit(1);
});

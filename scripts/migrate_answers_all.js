import { spawnSync } from 'child_process';
import fs from 'fs';

const CLOUD_URL = process.env.CLOUD_SUPABASE_URL || '';
const CLOUD_KEY = process.env.CLOUD_SUPABASE_KEY || '';

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

async function fetchTableChunkWithParams(table, offset, limit) {
  const url = `${CLOUD_URL}${table}?select=*&limit=${limit}&offset=${offset}&order=created_at.asc,id.asc`;
  const res = await fetch(url, {
    headers: {
      'apikey': CLOUD_KEY,
      'Authorization': `Bearer ${CLOUD_KEY}`
    }
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch ${table} offset ${offset}: ${res.statusText}`);
  }
  return await res.json();
}

async function main() {
  console.log('================================================================');
  console.log('🚀 CONTINUING HIGH-SPEED IMPORT FOR STUDENT_ANSWERS (190,900 ROWS)');
  console.log('================================================================\n');

  const table = 'student_answers';
  const BATCH_SIZE = 2000;
  let offset = 0;
  let totalImported = 0;

  // Cek jumlah yang sudah ada di VPS
  const countSql = `SELECT count(*)::text as c FROM public."${table}";`;
  const countRes = runLocalPsql(countSql);
  const match = countRes.match(/\s+(\d+)\s+/);
  const currentCount = match ? parseInt(match[1], 10) : 0;
  console.log(`📊 Baris saat ini di VPS: ${currentCount} baris.`);

  // Kita mulai dari offset yang belum diimpor atau loop semua secara aman (ON CONFLICT DO NOTHING)
  offset = Math.floor(currentCount / BATCH_SIZE) * BATCH_SIZE;
  console.log(`⏩ Memulai dari offset: ${offset}...`);

  while (true) {
    const rows = await fetchTableChunkWithParams(table, offset, BATCH_SIZE);
    if (!rows || rows.length === 0) {
      console.log('\n🏁 Selesai membaca semua data dari cloud.');
      break;
    }

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
    totalImported += rows.length;
    offset += rows.length;

    process.stdout.write(`\r   ⏳ Progress [${table}]: Offset ${offset} | Diimpor sesi ini: ${totalImported}`);

    if (rows.length < BATCH_SIZE) {
      console.log('\n🏁 Akhir data tercapai.');
      break;
    }
  }

  // Final count check
  const finalCountRes = runLocalPsql(countSql);
  const finalMatch = finalCountRes.match(/\s+(\d+)\s+/);
  const finalCount = finalMatch ? parseInt(finalMatch[1], 10) : 0;

  console.log('\n================================================================');
  console.log(`✅ HASIL AKHIR STUDENT_ANSWERS DI VPS: ${finalCount} / 190,900 BARIS`);
  console.log('================================================================\n');
}

main().catch(err => {
  console.error('\n❌ ERROR:', err);
  process.exit(1);
});

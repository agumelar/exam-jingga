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

async function fetchChunkKeyset(lastId, limit = 1000) {
  let url = `${CLOUD_URL}student_answers?select=*&order=id.asc&limit=${limit}`;
  if (lastId) {
    url += `&id=gt.${lastId}`;
  }
  const res = await fetch(url, {
    headers: {
      'apikey': CLOUD_KEY,
      'Authorization': `Bearer ${CLOUD_KEY}`
    }
  });
  if (!res.ok) {
    throw new Error(`Failed to fetch chunk (lastId: ${lastId}): ${res.statusText}`);
  }
  return await res.json();
}

async function main() {
  console.log('================================================================');
  console.log('🚀 FULL KEYSET STREAMING: ALL 190,900 STUDENT_ANSWERS -> VPS DB');
  console.log('================================================================\n');

  let lastId = null;
  let totalProcessed = 0;

  // Cek ID terakhir yang ada di database VPS untuk resume super cepat jika ada
  const maxIdRes = runLocalPsql('SELECT max(id)::text as m FROM public.student_answers;');
  const matchMax = maxIdRes.match(/([a-f0-9\-]{36})/i);
  if (matchMax) {
    lastId = matchMax[1];
    const curCountRes = runLocalPsql('SELECT count(*)::text as c FROM public.student_answers;');
    const curCountMatch = curCountRes.match(/\s+(\d+)\s+/);
    totalProcessed = curCountMatch ? parseInt(curCountMatch[1], 10) : 0;
    console.log(`⏩ Melanjutkan dari Last ID di VPS: ${lastId} (Sudah ada: ${totalProcessed} baris)`);
  }

  while (true) {
    const rows = await fetchChunkKeyset(lastId, 1000);
    if (!rows || rows.length === 0) {
      console.log('\n🏁 Selesai! Semua 190,900 baris jawaban telah terimpor 100%.');
      break;
    }

    const columns = Object.keys(rows[0]);
    const quotedCols = columns.map(c => `"${c}"`).join(', ');

    const valueRows = rows.map(r => {
      const vals = columns.map(c => escapeSqlValue(r[c]));
      return `(${vals.join(', ')})`;
    }).join(',\n');

    const insertSql = `
      INSERT INTO public.student_answers (${quotedCols})
      VALUES ${valueRows}
      ON CONFLICT DO NOTHING;
    `;

    runLocalPsql(insertSql);
    totalProcessed += rows.length;
    lastId = rows[rows.length - 1].id;

    process.stdout.write(`\r   ⏳ Progress: ${totalProcessed} / 190900 baris (${Math.round((totalProcessed / 190900) * 100)}%) - ID: ${lastId.substring(0, 8)}...`);
  }

  // Final count check
  const finalCountRes = runLocalPsql('SELECT count(*)::text as c FROM public.student_answers;');
  const match = finalCountRes.match(/\s+(\d+)\s+/);
  const finalCount = match ? parseInt(match[1], 10) : 0;

  console.log('\n================================================================');
  console.log(`🎉 VERIFIKASI AKHIR STUDENT_ANSWERS: ${finalCount} / 190,900 BARIS (100% LENGKAP!)`);
  console.log('================================================================\n');
}

main().catch(err => {
  console.error('\n❌ ERROR:', err);
  process.exit(1);
});

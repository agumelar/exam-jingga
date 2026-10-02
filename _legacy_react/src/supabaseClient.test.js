import test from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';

test('supabaseClient throws when env missing', () => {
  const result = spawnSync(process.execPath, ['-e', "import('./src/supabaseClient.js')"], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      VITE_SUPABASE_URL: '',
      VITE_SUPABASE_ANON_KEY: '',
    },
    encoding: 'utf-8',
  });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Missing Supabase env/);
});

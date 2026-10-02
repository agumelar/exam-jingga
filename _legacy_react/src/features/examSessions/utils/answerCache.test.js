import test from 'node:test';
import assert from 'node:assert/strict';
import { readLocal, writeLocal, clearLocal } from './answerCache.js';

const store = new Map();
globalThis.localStorage = {
  getItem: (k) => (store.has(k) ? store.get(k) : null),
  setItem: (k, v) => { store.set(k, String(v)); },
  removeItem: (k) => { store.delete(k); },
  clear: () => { store.clear(); },
};

test('writeLocal then readLocal returns persisted payload', () => {
  localStorage.clear();
  const sessionId = 'sess-1';
  const payload = {
    version: 1,
    updatedAt: 1710000000000,
    answers: {
      q1: { choice: 'A', isDoubt: false, updatedAt: 1710000000000 }
    }
  };
  writeLocal(sessionId, payload);
  assert.deepEqual(readLocal(sessionId), payload);
});

test('clearLocal removes payload', () => {
  localStorage.clear();
  const sessionId = 'sess-2';
  writeLocal(sessionId, { version: 1, updatedAt: 1, answers: {} });
  clearLocal(sessionId);
  assert.equal(readLocal(sessionId), null);
});

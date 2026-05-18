import test from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_DRIFT_THRESHOLD_MS, isDrift } from './antiCheatSignals.js';

test('isDrift returns true when delta exceeds threshold', () => {
  assert.equal(
    isDrift(DEFAULT_DRIFT_THRESHOLD_MS + 1, DEFAULT_DRIFT_THRESHOLD_MS),
    true
  );
});

test('isDrift returns false for small or invalid deltas', () => {
  assert.equal(
    isDrift(DEFAULT_DRIFT_THRESHOLD_MS - 1, DEFAULT_DRIFT_THRESHOLD_MS),
    false
  );
  assert.equal(isDrift(Number.NaN, DEFAULT_DRIFT_THRESHOLD_MS), false);
});

test('isDrift uses default threshold when not provided', () => {
  assert.equal(isDrift(DEFAULT_DRIFT_THRESHOLD_MS + 100), true);
});

export const DEFAULT_DRIFT_THRESHOLD_MS = 3500;
export const DEFAULT_DRIFT_TICK_MS = 1000;
export const DEFAULT_FOCUS_POLL_MS = 1500;

export function isDrift(deltaMs, thresholdMs = DEFAULT_DRIFT_THRESHOLD_MS) {
  if (!Number.isFinite(deltaMs) || !Number.isFinite(thresholdMs)) return false;
  return deltaMs > thresholdMs;
}

const PREFIX = 'exam_answers_cache:';

const safeParse = (value) => {
  if (!value) return null;
  try { return JSON.parse(value); } catch { return null; }
};

export function readLocal(sessionId) {
  if (!sessionId) return null;
  const raw = localStorage.getItem(`${PREFIX}${sessionId}`);
  return safeParse(raw);
}

export function writeLocal(sessionId, payload) {
  if (!sessionId) return;
  localStorage.setItem(`${PREFIX}${sessionId}`, JSON.stringify(payload));
}

export function clearLocal(sessionId) {
  if (!sessionId) return;
  localStorage.removeItem(`${PREFIX}${sessionId}`);
}

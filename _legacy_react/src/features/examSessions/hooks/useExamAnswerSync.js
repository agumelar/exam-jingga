import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchSessionAnswers, upsertSessionAnswers } from '../services/answerService.js';
import { readLocal, writeLocal, clearLocal } from '../utils/answerCache.js';

export const normalizeId = (value) => (value === null || value === undefined ? '' : String(value));

export function mergeAnswers(dbRows, cache) {
  const answers = {};
  const doubts = [];
  (dbRows || []).forEach((r) => {
    const normalizedId = normalizeId(r?.question_id);
    if (!normalizedId) return;
    const chosenAnswer = r?.chosen_answer;
    if (chosenAnswer === null || chosenAnswer === undefined) {
      answers[normalizedId] = null;
    } else {
      answers[normalizedId] = String(chosenAnswer).trim().toUpperCase();
    }
    if (r?.is_doubt && !doubts.includes(normalizedId)) {
      doubts.push(normalizedId);
    }
  });
  if (cache?.answers) {
    Object.entries(cache.answers).forEach(([qid, v]) => {
      const normalizedId = normalizeId(qid);
      if (!normalizedId) return;
      const cachedChoice = v?.choice;
      if (cachedChoice === null || cachedChoice === undefined) {
        answers[normalizedId] = null;
      } else {
        answers[normalizedId] = String(cachedChoice).trim().toUpperCase();
      }
      if (v?.isDoubt && !doubts.includes(normalizedId)) {
        doubts.push(normalizedId);
      }
    });
  }
  return { answers, doubts };
}

export async function loadMergedAnswers({ sessionId, fetchFn, readCache }) {
  if (!sessionId) return { answers: {}, doubts: [] };
  try {
    const response = await fetchFn(sessionId);
    if (response?.error) throw response.error;
    return mergeAnswers(response?.data || [], readCache(sessionId));
  } catch {
    return mergeAnswers([], readCache(sessionId));
  }
}

export function buildCachePayload({ answers, doubts, now }) {
  const payload = {
    version: 1,
    updatedAt: now,
    answers: {},
  };
  Object.entries(answers || {}).forEach(([qid, choice]) => {
    const normalizedId = normalizeId(qid);
    if (!normalizedId) return;
    payload.answers[normalizedId] = {
      choice: choice ?? null,
      isDoubt: Array.isArray(doubts) && doubts.includes(normalizedId),
      updatedAt: now,
    };
  });
  return payload;
}

export async function runFlush({
  sessionId,
  isLocked,
  queue,
  upsertFn,
  writeCache,
  snapshot,
  setFlushing,
}) {
  if (!sessionId || isLocked || !queue || queue.size === 0) {
    return { data: [], error: null };
  }
  try {
    setFlushing(true);
    const rows = Array.from(queue.values());
    const response = await upsertFn(sessionId, rows);
    if (!response?.error) {
      queue.clear();
      if (writeCache && snapshot) {
        writeCache(sessionId, snapshot);
      }
    }
    return response;
  } catch (error) {
    return { data: null, error };
  } finally {
    setFlushing(false);
  }
}

export function useExamAnswerSync({ sessionId, isLocked }) {
  const [answers, setAnswers] = useState({});
  const [doubts, setDoubts] = useState([]);
  const answersRef = useRef({});
  const doubtsRef = useRef([]);
  const queueRef = useRef(new Map());
  const flushingRef = useRef(false);

  const hydrate = useCallback(async () => {
    const merged = await loadMergedAnswers({
      sessionId,
      fetchFn: fetchSessionAnswers,
      readCache: readLocal,
    });
    setAnswers(merged.answers);
    setDoubts(merged.doubts);
  }, [sessionId]);

  const enqueue = useCallback(
    (questionId, choice, isDoubt) => {
      if (!sessionId) return;
      const normalizedId = normalizeId(questionId);
      if (!normalizedId) return;
      const now = Date.now();
      queueRef.current.set(normalizedId, {
        questionId: normalizedId,
        choice,
        isDoubt,
        updatedAt: now,
      });
      const payload = buildCachePayload({
        answers: {
          ...answersRef.current,
          [normalizedId]: choice ?? null,
        },
        doubts: isDoubt
          ? Array.from(new Set([...doubtsRef.current, normalizedId]))
          : doubtsRef.current.filter((qid) => qid !== normalizedId),
        now,
      });
      writeLocal(sessionId, payload);
    },
    [sessionId]
  );

  const flush = useCallback(async () => {
    const snapshot = buildCachePayload({
      answers: answersRef.current,
      doubts: doubtsRef.current,
      now: Date.now(),
    });
    await runFlush({
      sessionId,
      isLocked,
      queue: queueRef.current,
      upsertFn: upsertSessionAnswers,
      writeCache: writeLocal,
      snapshot,
      setFlushing: (value) => {
        flushingRef.current = value;
      },
    });
  }, [sessionId, isLocked]);

  const clearCache = useCallback(() => {
    if (!sessionId) return;
    clearLocal(sessionId);
    queueRef.current.clear();
  }, [sessionId]);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    answersRef.current = answers;
    doubtsRef.current = doubts;
  }, [answers, doubts]);

  useEffect(() => {
    if (!sessionId || isLocked) return;
    const timer = setInterval(() => {
      flush();
    }, 1200);
    return () => clearInterval(timer);
  }, [sessionId, isLocked, flush]);

  return {
    answers,
    doubts,
    setAnswers,
    setDoubts,
    enqueue,
    flush,
    hydrate,
    clearCache,
  };
}

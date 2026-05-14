import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../api/endpoints';
import type { AnalysisResult, JobStatus } from '../types/api';
import { POLLING_INTERVAL_MS, MAX_POLL_ATTEMPTS } from '../constants';

interface PollState {
  status: JobStatus | 'idle';
  result: AnalysisResult | null;
  error: string | null;
  attempts: number;
}

export function useJobPoller(jobId: string | null) {
  const [state, setState] = useState<PollState>({
    status: 'idle',
    result: null,
    error: null,
    attempts: 0,
  });

  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const activeRef = useRef(true);

  const poll = useCallback(async (id: string, attempt: number) => {
    if (!activeRef.current) return;

    if (attempt >= MAX_POLL_ATTEMPTS) {
      setState((s) => ({
        ...s,
        status: 'error',
        error: 'Analysis timed out after 5 minutes. Please try again.',
      }));
      return;
    }

    try {
      const response = await api.analysis.getStatus(id);
      if (!activeRef.current) return;

      setState((s) => ({ ...s, status: response.status, attempts: attempt + 1 }));

      if (response.status === 'done') {
        setState((s) => ({ ...s, result: response.result ?? null }));
      } else if (response.status === 'error') {
        setState((s) => ({ ...s, error: response.error ?? 'Analysis failed.' }));
      } else {
        timerRef.current = setTimeout(() => poll(id, attempt + 1), POLLING_INTERVAL_MS);
      }
    } catch (err) {
      if (!activeRef.current) return;
      setState((s) => ({ ...s, status: 'error', error: (err as Error).message }));
    }
  }, []);

  useEffect(() => {
    if (!jobId) return;

    activeRef.current = true;
    setState({ status: 'pending', result: null, error: null, attempts: 0 });
    poll(jobId, 0);

    return () => {
      activeRef.current = false;
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [jobId, poll]);

  return state;
}

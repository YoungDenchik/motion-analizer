import { useState, useCallback } from 'react';
import { api } from '../api/endpoints';

type Phase = 'idle' | 'uploading' | 'processing' | 'error';

export function useAnalysis() {
  const [phase, setPhase] = useState<Phase>('idle');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const startAnalysis = useCallback(
    async (exercise: string, videoUri: string, videoName: string) => {
      setPhase('uploading');
      setUploadProgress(0);
      setError(null);
      setJobId(null);
      try {
        const response = await api.analysis.start(exercise, videoUri, videoName, setUploadProgress);
        setJobId(response.job_id);
        setPhase('processing');
      } catch (err) {
        setPhase('error');
        setError((err as Error).message);
      }
    },
    []
  );

  const reset = useCallback(() => {
    setPhase('idle');
    setUploadProgress(0);
    setJobId(null);
    setError(null);
  }, []);

  return { phase, uploadProgress, jobId, error, startAnalysis, reset };
}

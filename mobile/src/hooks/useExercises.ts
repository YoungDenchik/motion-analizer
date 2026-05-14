import { useState, useCallback } from 'react';
import { api } from '../api/endpoints';

export function useExercises() {
  const [exercises, setExercises] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.references.list();
      setExercises(data.exercises);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  const deleteExercise = useCallback(async (name: string) => {
    await api.references.delete(name);
    setExercises((prev) => prev.filter((e) => e !== name));
  }, []);

  return { exercises, loading, error, fetch, deleteExercise };
}

import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { startGeneration } from '../api/generations.js';
import { ROUTES } from '../routes.js';

export function useStartGeneration() {
  const navigate = useNavigate();
  const [isStarting, setIsStarting] = useState(false);
  const [error, setError] = useState('');

  const start = useCallback(async () => {
    setIsStarting(true);
    setError('');

    try {
      const generation = await startGeneration();
      navigate(ROUTES.generationRestrictions(generation.id));
    } catch (startError) {
      setError(startError.message);
      setIsStarting(false);
    }
  }, [navigate]);

  return { start, isStarting, error };
}

import { useStartGeneration } from '../../hooks/useStartGeneration.js';
import './GenerationShell.css';

export default function GenerationError({ error, onRetry }) {
  const { start, isStarting, error: startError } = useStartGeneration();
  const isExpired = error.code === 'GENERATION_NOT_FOUND';

  return (
    <div className='generation__status generation__status--error' role='alert'>
      <p>{startError || error.message}</p>

      {isExpired ? (
        <button
          className='generation__button'
          type='button'
          onClick={start}
          disabled={isStarting}
        >
          {isStarting ? 'Створення…' : 'Почати нову генерацію'}
        </button>
      ) : (
        <button className='generation__button' type='button' onClick={onRetry}>
          Спробувати ще раз
        </button>
      )}
    </div>
  );
}
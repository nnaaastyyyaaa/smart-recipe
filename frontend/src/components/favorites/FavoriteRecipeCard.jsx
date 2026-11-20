import { useState } from 'react';
import { FaRegClock } from 'react-icons/fa';
import { Link } from 'react-router-dom';
import { ROUTES } from '../../routes.js';
import './FavoriteRecipeCard.css';

function formatCookingTime(totalMinutes) {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours === 0) return `${minutes} хв`;
  return minutes === 0 ? `${hours} год` : `${hours} год ${minutes} хв`;
}

export default function FavoriteRecipeCard({ recipe, onDelete }) {
  const [step, setStep] = useState('idle');

  async function handleConfirm() {
    setStep('deleting');

    const isDeleted = await onDelete(recipe);
    if (!isDeleted) setStep('idle');
  }

  return (
    <article className='recipe-card'>
      <h3 className='recipe-card__title'>{recipe.title}</h3>
      <p className='recipe-card__description'>{recipe.description}</p>

      <p className='recipe-card__time'>
        <FaRegClock aria-hidden='true' />
        {formatCookingTime(recipe.cooking_time)}
      </p>

      {step === 'idle' ? (
        <div className='recipe-card__actions'>
          <Link
            className='recipe-card__link'
            to={ROUTES.favoriteRecipe(recipe.id)}
          >
            Детальніше
          </Link>

          <button
            className='recipe-card__delete'
            type='button'
            onClick={() => setStep('confirm')}
          >
            Видалити
          </button>
        </div>
      ) : (
        <div className='recipe-card__actions' role='group'>
          <span className='recipe-card__confirm-text'>Видалити рецепт?</span>

          <span className='recipe-card__confirm-buttons'>
            <button
              className='recipe-card__confirm-yes'
              type='button'
              onClick={handleConfirm}
              disabled={step === 'deleting'}
            >
              Так
            </button>
            <button
              className='recipe-card__confirm-no'
              type='button'
              onClick={() => setStep('idle')}
              disabled={step === 'deleting'}
            >
              Ні
            </button>
          </span>
        </div>
      )}
    </article>
  );
}

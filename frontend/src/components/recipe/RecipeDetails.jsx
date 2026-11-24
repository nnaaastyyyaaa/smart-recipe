import { FaRegClock } from 'react-icons/fa';
import { formatCookingTime } from '../../utils/formatCookingTime.js';
import { splitIngredients, splitSteps } from '../../utils/recipeText.js';
import './RecipeDetails.css';

export default function RecipeDetails({ recipe, actions }) {
  const ingredients = splitIngredients(recipe.ingredients);
  const steps = splitSteps(recipe.instructions);

  return (
    <article className='recipe'>
      <header className='recipe__header'>
        <h1 className='recipe__title'>{recipe.title}</h1>
        <p className='recipe__time'>
          <FaRegClock aria-hidden='true' />
          {formatCookingTime(recipe.cooking_time)}
        </p>
        <p className='recipe__description'>{recipe.description}</p>
      </header>

      <div className='recipe__body'>
        <section className='recipe__section'>
          <h2 className='recipe__heading'>Інгредієнти</h2>
          <ol className='recipe__list'>
            {ingredients.map((ingredient, index) => (
              <li key={index}>{ingredient}</li>
            ))}
          </ol>
        </section>

        <section className='recipe__section recipe__section--scrollable'>
          <h2 className='recipe__heading' id='recipe-instructions-heading'>
            Приготування
          </h2>
          <div
            className='recipe__scroll'
            role='region'
            aria-labelledby='recipe-instructions-heading'
            tabIndex={0}
          >
            {steps.length > 1 ? (
              <ol className='recipe__list recipe__list--steps'>
                {steps.map((step, index) => (
                  <li key={index}>{step}</li>
                ))}
              </ol>
            ) : (
              <p className='recipe__text'>{steps[0]}</p>
            )}
          </div>
        </section>
      </div>

      {actions && <div className='recipe__actions'>{actions}</div>}
    </article>
  );
}

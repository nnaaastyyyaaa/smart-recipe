import { FaArrowLeft } from 'react-icons/fa';
import { Link } from 'react-router-dom';
import ProfileShell from '../../components/profile/ProfileShell.jsx';
import { ROUTES } from '../../routes.js';
import './FavoriteRecipePage.css';

export default function FavoriteRecipePage() {
  return (
    <ProfileShell>
      <div className='recipe-stub'>
        <p className='recipe-stub__title'>Сторінка рецепта ще в розробці</p>
        <p className='recipe-stub__text'>
          Детальний перегляд збереженого рецепта зʼявиться найближчим часом.
        </p>
        <Link className='recipe-stub__back' to={ROUTES.favorites}>
          <FaArrowLeft aria-hidden='true' />
          До улюблених рецептів
        </Link>
      </div>
    </ProfileShell>
  );
}

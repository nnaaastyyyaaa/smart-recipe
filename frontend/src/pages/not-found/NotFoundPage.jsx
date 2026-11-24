import { Link } from 'react-router-dom';
import { ROUTES } from '../../routes.js';
import './NotFoundPage.css';

export default function NotFoundPage() {
  return (
    <section className='not-found'>
      <p className='not-found__code' aria-hidden='true'>
        404
      </p>
      <h1 className='not-found__title'>Сторінку не знайдено</h1>
      <p className='not-found__text'>
        Цієї сторінки не існує або вона видалена
      </p>
      <Link className='not-found__link' to={ROUTES.home}>
        На головну
      </Link>
    </section>
  );
}

import { NavLink } from 'react-router-dom';
import { ROUTES } from '../../routes.js';
import './ProfileTabs.css';

export default function ProfileTabs() {
  return (
    <nav className='profile-tabs' aria-label='Розділи профілю'>
      <NavLink to={ROUTES.profile} end className='profile-tabs__tab'>
        Особисті дані
      </NavLink>
      <NavLink to={ROUTES.favorites} className='profile-tabs__tab'>
        Улюблені рецепти
      </NavLink>
    </nav>
  );
}

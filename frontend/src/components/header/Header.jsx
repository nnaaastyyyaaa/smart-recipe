import { Link, useLocation } from 'react-router-dom';
import logoCompact from '../../assets/logo-compact.svg';
import logoFull from '../../assets/logo-full.svg';
import { useAuth } from '../../auth/useAuth.js';
import { ROUTES } from '../../routes.js';
import './Header.css';

export default function Header() {
  const { status, user } = useAuth();
  const { pathname } = useLocation();

  const showProfileLink =
    status === 'authenticated' && !pathname.startsWith(ROUTES.profile);

  return (
    <header className='header'>
      <div className='header__inner'>
        <Link
          to={ROUTES.home}
          className='header__logo'
          aria-label='SmartRecipe: на головну'
        >
          <picture>
            <source media='(max-width: 640px)' srcSet={logoCompact} />
            <img className='header__logo-image' src={logoFull} alt='' />
          </picture>
        </Link>

        {showProfileLink && (
          <nav className='header__nav'>
            <Link
              className='header__avatar'
              to={ROUTES.profile}
              aria-label='Профіль'
              title='Профіль'
            >
              {user.name.trim().charAt(0).toUpperCase()}
            </Link>
          </nav>
        )}
      </div>
    </header>
  );
}

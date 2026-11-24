import { useState } from 'react';
import { FaSignOutAlt } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/useAuth.js';
import { ROUTES } from '../../routes.js';
import './LogoutButton.css';

export default function LogoutButton() {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [error, setError] = useState('');

  async function handleLogout() {
    setIsLoggingOut(true);
    setError('');

    try {
      await logout();
      navigate(ROUTES.home, { replace: true });
    } catch (logoutError) {
      setError(logoutError.message);
      setIsLoggingOut(false);
    }
  }

  return (
    <div className='logout'>
      <button
        className='logout__button'
        type='button'
        onClick={handleLogout}
        disabled={isLoggingOut}
      >
        <FaSignOutAlt aria-hidden='true' />
        {isLoggingOut ? 'Вихід…' : 'Вийти'}
      </button>
      {error && (
        <p className='logout__error' role='alert'>
          {error}
        </p>
      )}
    </div>
  );
}

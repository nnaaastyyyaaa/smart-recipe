import { useState } from 'react';
import { FaSignOutAlt } from 'react-icons/fa';
import { useAuth } from '../../auth/useAuth.js';
import './LogoutButton.css';

export default function LogoutButton() {
  const { logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [error, setError] = useState('');

  async function handleLogout() {
    setIsLoggingOut(true);
    setError('');

    try {
      await logout();
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

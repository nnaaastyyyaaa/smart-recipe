import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../auth/useAuth.js';
import { getRedirectPath } from '../auth/redirect.js';

export default function GuestRoute() {
  const { status } = useAuth();
  const location = useLocation();

  if (status === 'loading') {
    return <p className='page-status'>Завантаження…</p>;
  }

  if (status === 'authenticated') {
    return <Navigate to={getRedirectPath(location)} replace />;
  }

  return <Outlet />;
}
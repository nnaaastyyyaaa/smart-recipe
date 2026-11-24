import { useLocation } from 'react-router-dom';

export default function LocationDisplay() {
  const location = useLocation();

  return (
    <div data-testid='location'>{`${location.pathname}${location.search}`}</div>
  );
}

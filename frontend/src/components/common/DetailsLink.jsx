import { Link } from 'react-router-dom';
import './DetailsLink.css';

export default function DetailsLink({ to, title, ref }) {
  return (
    <Link
      className='details-link'
      to={to}
      aria-label={`Детальніше: ${title}`}
      ref={ref}
    >
      Детальніше
    </Link>
  );
}

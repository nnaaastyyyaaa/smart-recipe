import { FaRegClock } from 'react-icons/fa';
import { formatCookingTime } from '../../utils/formatCookingTime.js';
import DetailsLink from '../common/DetailsLink.jsx';
import './SuggestionCard.css';

export default function SuggestionCard({ suggestion, to, ref }) {
  return (
    <article className='suggestion-card'>
      <h2 className='suggestion-card__title'>{suggestion.title}</h2>
      <p className='suggestion-card__description'>{suggestion.description}</p>
      <div className='suggestion-card__footer'>
        <span className='suggestion-card__time'>
          <FaRegClock aria-hidden='true' />
          {formatCookingTime(suggestion.cooking_time)}
        </span>
        <DetailsLink to={to} title={suggestion.title} ref={ref} />
      </div>
    </article>
  );
}

import { FaArrowLeft } from 'react-icons/fa';
import { Link, useParams } from 'react-router-dom';
import GenerationShell from '../../components/generation/GenerationShell.jsx';
import { ROUTES } from '../../routes.js';

export default function SuggestionsPage() {
  const { generationId } = useParams();

  return (
    <GenerationShell step={3} title='Варіанти рецептів'>
      <div className='generation__card generation__status'>
        <p>Рецепти підібрано! Сторінка з варіантами ще в розробці.</p>
        <Link
          className='generation__button'
          to={ROUTES.generationProducts(generationId)}
        >
          <FaArrowLeft aria-hidden='true' />
          Назад до продуктів
        </Link>
      </div>
    </GenerationShell>
  );
}
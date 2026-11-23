import { FaRegClock } from 'react-icons/fa';
import { Link } from 'react-router-dom';
import { useAuth } from '../../auth/useAuth.js';
import { useStartGeneration } from '../../hooks/useStartGeneration.js';
import { ROUTES } from '../../routes.js';
import './HomePage.css';

const FRIDGE_ITEMS = [
  { name: 'Яйця', tone: 'orange', tilt: -6 },
  { name: 'Шпинат', tone: 'green', tilt: 4 },
  { name: 'Сир твердий', tone: 'brown', tilt: -2 },
  { name: 'Помідори', tone: 'orange', tilt: 7 },
  { name: 'Цибуля', tone: 'brown', tilt: -5 },
  { name: 'Вершки', tone: 'green', tilt: 3 },
];

const STEPS = [
  {
    title: 'Оберіть обмеження',
    text: 'Веганське, без глютену чи інше. Або вкажіть, що обмежень немає.',
  },
  {
    title: 'Відмітьте продукти',
    text: 'Знайдіть у каталозі те, що є вдома. Невідповідні продукти приховані.',
  },
  {
    title: 'Отримайте ідеї',
    text: 'Штучний інтелект запропонує до 16 страв саме з ваших інгредієнтів.',
  },
  {
    title: 'Збережіть рецепт',
    text: 'Відкрийте покроковий рецепт і додайте його до своєї кулінарної книги.',
  },
];

function HeroActions() {
  const { status } = useAuth();
  const { start, isStarting, error } = useStartGeneration();

  if (status === 'loading') {
    return <p className='home__status'>Завантаження…</p>;
  }

  if (status === 'guest') {
    return (
      <div className='home__actions'>
        <Link className='home__button' to={ROUTES.register}>
          Зареєструватися
        </Link>
        <Link className='home__button home__button--ghost' to={ROUTES.login}>
          Увійти
        </Link>
      </div>
    );
  }

  return (
    <>
      <div className='home__actions'>
        <button
          className='home__button'
          type='button'
          onClick={start}
          disabled={isStarting}
        >
          {isStarting ? 'Створення…' : 'Почати генерацію'}
        </button>
        <Link
          className='home__button home__button--ghost'
          to={ROUTES.favorites}
        >
          Мої рецепти
        </Link>
      </div>

      {error && (
        <p className='home__alert' role='alert'>
          {error}
        </p>
      )}
    </>
  );
}

function FridgeIllustration() {
  return (
    <div className='fridge' aria-hidden='true'>
      <div className='fridge__door'>
        <span className='fridge__handle' />
        <ul className='fridge__magnets'>
          {FRIDGE_ITEMS.map(({ name, tone, tilt }, index) => (
            <li
              key={name}
              className={`fridge__magnet fridge__magnet--${tone}`}
              style={{ '--tilt': `${tilt}deg`, '--order': index }}
            >
              {name}
            </li>
          ))}
        </ul>
      </div>

      <div className='fridge__recipe'>
        <p className='fridge__recipe-title'>Фритата зі шпинатом і сиром</p>
        <p className='fridge__recipe-meta'>
          <FaRegClock />
          25 хв · з 5 ваших продуктів
        </p>
        <ol className='fridge__recipe-steps'>
          <li>Збийте яйця з вершками</li>
          <li>Обсмажте цибулю та шпинат</li>
          <li>Залийте, посипте сиром і запечіть</li>
        </ol>
      </div>
    </div>
  );
}

export default function HomePage() {
  const { user, status } = useAuth();

  return (
    <div className='home'>
      <section className='home__hero'>
        <div className='home__intro'>
          {status === 'authenticated' && (
            <p className='home__greeting'>Вітаємо, {user.name}!</p>
          )}
          <h1 className='home__title'>
            Що приготувати з того, що вже є вдома?
          </h1>
          <p className='home__lead'>
            Позначте продукти з холодильника, і SmartRecipe запропонує страви,
            які з них справді вийдуть. З урахуванням ваших дієтичних обмежень.
          </p>
          <HeroActions />
        </div>

        <FridgeIllustration />
      </section>

      <section className='home__how' aria-labelledby='home-how-title'>
        <h2 className='home__heading' id='home-how-title'>
          Як це працює
        </h2>

        <ol className='home__steps'>
          {STEPS.map(({ title, text }, index) => (
            <li className='home__step' key={title}>
              <span className='home__step-number' aria-hidden='true'>
                {index + 1}
              </span>
              <h3 className='home__step-title'>{title}</h3>
              <p className='home__step-text'>{text}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
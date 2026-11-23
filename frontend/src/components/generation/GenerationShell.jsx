import './GenerationShell.css';

const STEPS = ['Обмеження', 'Продукти', 'Рецепти'];

export default function GenerationShell({ step, title, children }) {
  return (
    <section className='generation'>
      <ol className='generation__steps' aria-label='Кроки генерації'>
        {STEPS.map((label, index) => {
          const number = index + 1;
          const state =
            number < step ? 'done' : number === step ? 'current' : 'next';

          return (
            <li
              key={label}
              className={`generation__step generation__step--${state}`}
              aria-current={state === 'current' ? 'step' : undefined}
            >
              <span className='generation__step-number'>{number}</span>
              {label}
            </li>
          );
        })}
      </ol>

      <h1 className='generation__title'>{title}</h1>
      {children}
    </section>
  );
}
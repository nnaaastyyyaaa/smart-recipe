import './RecipeStatus.css';

export default function RecipeStatus({ message, hint, isError, children }) {
  return (
    <div
      className={`recipe-status${isError ? ' recipe-status--error' : ''}`}
      role={isError ? 'alert' : 'status'}
    >
      {!isError && (
        <span className='recipe-status__spinner' aria-hidden='true' />
      )}
      <p className='recipe-status__message'>{message}</p>
      {hint && <p className='recipe-status__hint'>{hint}</p>}
      {children && <div className='recipe-status__actions'>{children}</div>}
    </div>
  );
}

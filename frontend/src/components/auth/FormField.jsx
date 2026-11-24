import { useState } from 'react';
import { FaEye, FaEyeSlash } from 'react-icons/fa';

export default function FormField({
  name,
  label,
  type = 'text',
  autoComplete,
  hint,
  error,
  value,
  onChange,
  maxLength,
}) {
  const [isVisible, setIsVisible] = useState(false);
  const isPassword = type === 'password';

  const describedBy =
    [hint && `${name}-hint`, error && `${name}-error`]
      .filter(Boolean)
      .join(' ') || undefined;

  return (
    <div className='auth-form__field'>
      <label className='auth-form__label' htmlFor={name}>
        {label}
      </label>

      <div className='auth-form__control'>
        <input
          className={`auth-form__input${isPassword ? ' auth-form__input--password' : ''}`}
          id={name}
          name={name}
          type={isPassword && isVisible ? 'text' : type}
          autoComplete={autoComplete}
          maxLength={maxLength}
          value={value}
          onChange={onChange}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy}
        />

        {isPassword && (
          <button
            className='auth-form__toggle'
            type='button'
            onClick={() => setIsVisible((current) => !current)}
            aria-label={isVisible ? 'Сховати пароль' : 'Показати пароль'}
          >
            {isVisible ? <FaEyeSlash size={20} /> : <FaEye size={20} />}
          </button>
        )}
      </div>

      {hint && (
        <p className='auth-form__hint' id={`${name}-hint`}>
          {hint}
        </p>
      )}

      {error && (
        <p className='auth-form__error' id={`${name}-error`}>
          {error}
        </p>
      )}
    </div>
  );
}

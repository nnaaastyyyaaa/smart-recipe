import { useEffect, useState } from 'react';
import { FaCheck, FaEye, FaEyeSlash } from 'react-icons/fa';
import { changePassword } from '../../api/users.js';
import './ChangePasswordForm.css';

const ALLOWED_PASSWORD = /^[A-Za-z0-9!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]+$/;

const EMPTY_VALUES = {
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
};

function validate({ currentPassword, newPassword, confirmPassword }) {
  const errors = {};

  if (!currentPassword) {
    errors.currentPassword = 'Введіть поточний пароль';
  }

  if (!newPassword) {
    errors.newPassword = 'Введіть новий пароль';
  } else if (newPassword.length < 8 || newPassword.length > 16) {
    errors.newPassword = 'Пароль має містити від 8 до 16 символів';
  } else if (!ALLOWED_PASSWORD.test(newPassword)) {
    errors.newPassword =
      'Пароль може містити лише латинські літери, цифри та спеціальні символи';
  }

  if (!confirmPassword) {
    errors.confirmPassword = 'Повторіть новий пароль';
  } else if (confirmPassword !== newPassword) {
    errors.confirmPassword = 'Паролі не збігаються';
  }

  return errors;
}

function PasswordField({
  name,
  label,
  autoComplete,
  hint,
  error,
  value,
  onChange,
  maxLength,
}) {
  const [isVisible, setIsVisible] = useState(false);

  const describedBy =
    [hint && `${name}-hint`, error && `${name}-error`]
      .filter(Boolean)
      .join(' ') || undefined;

  return (
    <div className='password-form__field'>
      <label className='password-form__label' htmlFor={name}>
        {label}
      </label>

      <div className='password-form__control'>
        <input
          className='password-form__input'
          id={name}
          name={name}
          type={isVisible ? 'text' : 'password'}
          autoComplete={autoComplete}
          maxLength={maxLength}
          value={value}
          onChange={onChange}
          aria-invalid={Boolean(error)}
          aria-describedby={describedBy}
        />
        <button
          className='password-form__toggle'
          type='button'
          onClick={() => setIsVisible((current) => !current)}
          aria-label={isVisible ? 'Сховати пароль' : 'Показати пароль'}
        >
          {isVisible ? <FaEyeSlash size={20} /> : <FaEye size={20} />}
        </button>
      </div>

      {hint && (
        <p className='password-form__hint' id={`${name}-hint`}>
          {hint}
        </p>
      )}

      {error && (
        <p className='password-form__error' id={`${name}-error`}>
          {error}
        </p>
      )}
    </div>
  );
}

export default function ChangePasswordForm() {
  const [values, setValues] = useState(EMPTY_VALUES);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [isSuccess, setIsSuccess] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isSuccess) return undefined;

    const timer = setTimeout(() => setIsSuccess(false), 4000);
    return () => clearTimeout(timer);
  }, [isSuccess]);

  function handleChange(event) {
    const { name, value } = event.target;

    setValues((current) => ({ ...current, [name]: value }));
    setFieldErrors((current) => ({ ...current, [name]: undefined }));
    setFormError('');
    setIsSuccess(false);
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const errors = validate(values);
    setFieldErrors(errors);
    setFormError('');
    setIsSuccess(false);

    if (Object.keys(errors).length > 0) return;

    setIsSubmitting(true);

    try {
      await changePassword(values);
      setValues(EMPTY_VALUES);
      setIsSuccess(true);
    } catch (error) {
      if (error.status === 400) {
        setFieldErrors({ currentPassword: error.message });
      } else {
        setFormError(error.message);
      }
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <form className='password-form' onSubmit={handleSubmit} noValidate>
      <PasswordField
        name='currentPassword'
        label='Поточний пароль'
        autoComplete='current-password'
        maxLength={128}
        value={values.currentPassword}
        onChange={handleChange}
        error={fieldErrors.currentPassword}
      />

      <PasswordField
        name='newPassword'
        label='Новий пароль'
        autoComplete='new-password'
        hint='Від 8 до 16 символів: латинські літери, цифри та спеціальні символи'
        value={values.newPassword}
        onChange={handleChange}
        error={fieldErrors.newPassword}
      />

      <PasswordField
        name='confirmPassword'
        label='Повторіть новий пароль'
        autoComplete='new-password'
        value={values.confirmPassword}
        onChange={handleChange}
        error={fieldErrors.confirmPassword}
      />

      {formError && (
        <p
          className='password-form__alert password-form__alert--error'
          role='alert'
        >
          {formError}
        </p>
      )}

      <button
        className={`password-form__submit${isSuccess ? ' password-form__submit--done' : ''}`}
        type='submit'
        disabled={isSubmitting}
      >
        {isSubmitting && 'Збереження…'}
        {!isSubmitting && isSuccess && (
          <>
            <FaCheck aria-hidden='true' />
            Пароль змінено
          </>
        )}
        {!isSubmitting && !isSuccess && 'Змінити пароль'}
      </button>

      <p className='password-form__sr' role='status'>
        {isSuccess ? 'Пароль успішно змінено.' : ''}
      </p>
    </form>
  );
}

import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { getRedirectPath } from '../../auth/redirect.js';
import { useAuth } from '../../auth/useAuth.js';
import { validateLogin } from '../../auth/validation.js';
import AuthCard from '../../components/auth/AuthCard.jsx';
import FormField from '../../components/auth/FormField.jsx';
import { ROUTES } from '../../routes.js';

const EMPTY_VALUES = { email: '', password: '' };

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [values, setValues] = useState(EMPTY_VALUES);
  const [fieldErrors, setFieldErrors] = useState({});
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  function handleChange(event) {
    const { name, value } = event.target;

    setValues((current) => ({ ...current, [name]: value }));
    setFieldErrors((current) => ({ ...current, [name]: undefined }));
    setFormError('');
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const errors = validateLogin(values);
    setFieldErrors(errors);
    setFormError('');

    if (Object.keys(errors).length > 0) return;

    setIsSubmitting(true);

    try {
      await login({ email: values.email.trim(), password: values.password });
      navigate(getRedirectPath(location), { replace: true });
    } catch (error) {
      setFormError(error.message);
      setIsSubmitting(false);
    }
  }

  return (
    <AuthCard
      title='Вхід'
      subtitle='Увійдіть, щоб генерувати та зберігати рецепти'
      footer={
        <>
          Ще не маєте акаунта?{' '}
          <Link
            className='auth__link'
            to={ROUTES.register}
            state={location.state}
          >
            Зареєструватися
          </Link>
        </>
      }
    >
      <form className='auth-form' onSubmit={handleSubmit} noValidate>
        <FormField
          name='email'
          label='Електронна пошта'
          type='email'
          autoComplete='email'
          value={values.email}
          onChange={handleChange}
          error={fieldErrors.email}
        />

        <FormField
          name='password'
          label='Пароль'
          type='password'
          autoComplete='current-password'
          maxLength={128}
          value={values.password}
          onChange={handleChange}
          error={fieldErrors.password}
        />

        {formError && (
          <p className='auth-form__alert' role='alert'>
            {formError}
          </p>
        )}

        <button
          className='auth-form__submit'
          type='submit'
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Вхід…' : 'Увійти'}
        </button>
      </form>
    </AuthCard>
  );
}
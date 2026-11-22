import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { getRedirectPath } from '../../auth/redirect.js';
import { useAuth } from '../../auth/useAuth.js';
import { NAME_MAX, validateRegister } from '../../auth/validation.js';
import AuthCard from '../../components/auth/AuthCard.jsx';
import FormField from '../../components/auth/FormField.jsx';
import { ROUTES } from '../../routes.js';

const EMPTY_VALUES = {
  name: '',
  email: '',
  password: '',
  confirmPassword: '',
};

export default function RegisterPage() {
  const { register } = useAuth();
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

    const errors = validateRegister(values);
    setFieldErrors(errors);
    setFormError('');

    if (Object.keys(errors).length > 0) return;

    setIsSubmitting(true);

    try {
      await register({
        name: values.name.trim(),
        email: values.email.trim(),
        password: values.password,
      });
      navigate(getRedirectPath(location), { replace: true });
    } catch (error) {
      // 409: такий email уже зареєстровано — показуємо помилку біля поля.
      if (error.status === 409) {
        setFieldErrors({ email: error.message });
      } else {
        setFormError(error.message);
      }
      setIsSubmitting(false);
    }
  }

  return (
    <AuthCard
      title='Реєстрація'
      subtitle='Створіть акаунт, щоб почати готувати з SmartRecipe'
      footer={
        <>
          Вже маєте акаунт?{' '}
          <Link className='auth__link' to={ROUTES.login} state={location.state}>
            Увійти
          </Link>
        </>
      }
    >
      <form className='auth-form' onSubmit={handleSubmit} noValidate>
        <FormField
          name='name'
          label="Ім'я"
          autoComplete='name'
          maxLength={NAME_MAX}
          value={values.name}
          onChange={handleChange}
          error={fieldErrors.name}
        />

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
          autoComplete='new-password'
          hint='Від 8 до 16 символів: латинські літери, цифри та спеціальні символи'
          value={values.password}
          onChange={handleChange}
          error={fieldErrors.password}
        />

        <FormField
          name='confirmPassword'
          label='Повторіть пароль'
          type='password'
          autoComplete='new-password'
          value={values.confirmPassword}
          onChange={handleChange}
          error={fieldErrors.confirmPassword}
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
          {isSubmitting ? 'Реєстрація…' : 'Зареєструватися'}
        </button>
      </form>
    </AuthCard>
  );
}
export const NAME_MIN = 2;
export const NAME_MAX = 24;
export const PASSWORD_MIN = 8;
export const PASSWORD_MAX = 16;

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const ALLOWED_PASSWORD = /^[A-Za-z0-9!@#$%^&*()_+\-=[\]{};':"\\|,.<>/?]+$/;

export function validateEmail(email) {
  const value = email.trim();

  if (!value) return 'Введіть електронну пошту';
  if (!EMAIL_PATTERN.test(value)) return 'Введіть коректну електронну пошту';
  return undefined;
}

export function validateName(name) {
  const value = name.trim();

  if (!value) return "Введіть ім'я";
  if (value.length < NAME_MIN || value.length > NAME_MAX) {
    return `Ім'я має містити від ${NAME_MIN} до ${NAME_MAX} символів`;
  }
  return undefined;
}

export function validateNewPassword(password) {
  if (!password) return 'Введіть пароль';
  if (password.length < PASSWORD_MIN || password.length > PASSWORD_MAX) {
    return `Пароль має містити від ${PASSWORD_MIN} до ${PASSWORD_MAX} символів`;
  }
  if (!ALLOWED_PASSWORD.test(password)) {
    return 'Пароль може містити лише латинські літери, цифри та спеціальні символи';
  }
  return undefined;
}

function compact(errors) {
  return Object.fromEntries(
    Object.entries(errors).filter(([, message]) => message !== undefined),
  );
}

export function validateLogin({ email, password }) {
  return compact({
    email: validateEmail(email),
    password: password ? undefined : 'Введіть пароль',
  });
}

export function validateRegister({ name, email, password, confirmPassword }) {
  let confirmError;

  if (!confirmPassword) confirmError = 'Повторіть пароль';
  else if (confirmPassword !== password) confirmError = 'Паролі не збігаються';

  return compact({
    name: validateName(name),
    email: validateEmail(email),
    password: validateNewPassword(password),
    confirmPassword: confirmError,
  });
}

import { describe, expect, it } from 'vitest';
import {
  validateEmail,
  validateLogin,
  validateName,
  validateNewPassword,
  validateRegister,
} from '../../src/auth/validation.js';

const VALID_FORM = {
  name: 'Вероніка',
  email: 'nika@example.com',
  password: 'Secret123',
  confirmPassword: 'Secret123',
};

describe('validateEmail: email format', () => {
  it('accepts trimmed address', () => {
    expect(validateEmail('  nika@example.com  ')).toBeUndefined();
  });

  it('requires value', () => {
    expect(validateEmail('   ')).toBe('Введіть електронну пошту');
  });

  it.each(['nika', 'nika@', 'nika@example', 'ni ka@example.com'])(
    'rejects %j',
    (value) => {
      expect(validateEmail(value)).toBe('Введіть коректну електронну пошту');
    },
  );
});

describe('validateName: name length', () => {
  it('accepts 2 to 24 characters', () => {
    expect(validateName('Ая')).toBeUndefined();
    expect(validateName('а'.repeat(24))).toBeUndefined();
  });

  it('rejects too short or too long', () => {
    expect(validateName('  А  ')).toMatch(/від 2 до 24/);
    expect(validateName('а'.repeat(25))).toMatch(/від 2 до 24/);
  });
});

describe('validateNewPassword: password rules', () => {
  it('checks 8 to 16 length', () => {
    expect(validateNewPassword('a'.repeat(7))).toMatch(/від 8 до 16/);
    expect(validateNewPassword('a'.repeat(8))).toBeUndefined();
    expect(validateNewPassword('a'.repeat(16))).toBeUndefined();
    expect(validateNewPassword('a'.repeat(17))).toMatch(/від 8 до 16/);
  });

  it('rejects cyrillic and spaces', () => {
    expect(validateNewPassword('пароль123')).toMatch(/латинські літери/);
    expect(validateNewPassword('pass word1')).toMatch(/латинські літери/);
  });
});

describe('validateLogin: login form', () => {
  it('returns no errors for valid data', () => {
    expect(validateLogin({ email: 'nika@example.com', password: 'x' })).toEqual(
      {},
    );
  });

  it('requires both fields', () => {
    expect(validateLogin({ email: '', password: '' })).toEqual({
      email: 'Введіть електронну пошту',
      password: 'Введіть пароль',
    });
  });
});

describe('validateRegister: registration form', () => {
  it('returns no errors for valid data', () => {
    expect(validateRegister(VALID_FORM)).toEqual({});
  });

  it('requires repeated password', () => {
    expect(validateRegister({ ...VALID_FORM, confirmPassword: '' })).toEqual({
      confirmPassword: 'Повторіть пароль',
    });
  });

  it('detects mismatched passwords', () => {
    expect(
      validateRegister({ ...VALID_FORM, confirmPassword: 'Secret124' }),
    ).toEqual({ confirmPassword: 'Паролі не збігаються' });
  });
});

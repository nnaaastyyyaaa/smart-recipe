 import './AuthForm.css';

export default function AuthCard({ title, subtitle, children, footer }) {
  return (
    <section className='auth'>
      <div className='auth__card'>
        <h1 className='auth__title'>{title}</h1>
        {subtitle && <p className='auth__subtitle'>{subtitle}</p>}
        {children}
        {footer && <p className='auth__footer'>{footer}</p>}
      </div>
    </section>
  );
}
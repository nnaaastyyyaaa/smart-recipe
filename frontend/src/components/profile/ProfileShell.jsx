import ProfileTabs from './ProfileTabs.jsx';
import './ProfileShell.css';

export default function ProfileShell({ children }) {
  return (
    <section className='profile'>
      <h1 className='profile__title'>Профіль</h1>
      <ProfileTabs />
      {children}
    </section>
  );
}

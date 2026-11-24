import LogoutButton from './LogoutButton.jsx';
import ProfileTabs from './ProfileTabs.jsx';
import './ProfileShell.css';

export default function ProfileShell({ children }) {
  return (
    <section className='profile'>
      <div className='profile__header'>
        <h1 className='profile__title'>Профіль</h1>
        <LogoutButton />
      </div>
      <ProfileTabs />
      {children}
    </section>
  );
}

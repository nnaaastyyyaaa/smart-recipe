import ChangePasswordForm from '../../components/profile/ChangePasswordForm.jsx'
import ProfileInfo from '../../components/profile/ProfileInfo.jsx'
import './ProfilePage.css'

export default function ProfilePage() {
  return (
    <section className="profile">
      <h1 className="profile__title">Профіль</h1>

      <div className="profile__grid">
        <article className="profile__card profile__card--center">
          <h2 className="profile__heading">Особисті дані</h2>
          <ProfileInfo />
        </article>

        <article className="profile__card">
          <h2 className="profile__heading">Зміна пароля</h2>
          <ChangePasswordForm />
        </article>
      </div>
    </section>
  )
}

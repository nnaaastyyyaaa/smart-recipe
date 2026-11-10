import { useAuth } from '../../auth/useAuth.js'
import './ProfileInfo.css'

export default function ProfileInfo() {
  const { user } = useAuth()
  const initial = user.name.trim().charAt(0).toUpperCase()

  return (
    <div className="profile-info">
      <div className="profile-info__avatar" aria-hidden="true">
        {initial}
      </div>

      <dl className="profile-info__details">
        <div className="profile-info__row">
          <dt className="profile-info__term">Ім'я</dt>
          <dd className="profile-info__value">{user.name}</dd>
        </div>
        <div className="profile-info__row">
          <dt className="profile-info__term">Електронна пошта</dt>
          <dd className="profile-info__value">{user.email}</dd>
        </div>
      </dl>
    </div>
  )
}

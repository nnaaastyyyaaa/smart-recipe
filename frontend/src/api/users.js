import { apiFetch } from './client.js'

export function changePassword({ currentPassword, newPassword }) {
  return apiFetch('/users/me/password', {
    method: 'PATCH',
    body: { current_password: currentPassword, new_password: newPassword },
  })
}

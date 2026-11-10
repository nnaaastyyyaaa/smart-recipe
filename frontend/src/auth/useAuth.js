import { useContext } from 'react'
import { AuthContext } from './AuthContext.js'

export function useAuth() {
  const context = useContext(AuthContext)

  if (context === null) {
    throw new Error('useAuth потрібно викликати всередині <AuthProvider>')
  }

  return context
}

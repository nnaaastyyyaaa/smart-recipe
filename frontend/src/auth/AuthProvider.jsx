import { useCallback, useEffect, useMemo, useState } from 'react'
import * as authApi from '../api/auth.js'
import { AuthContext } from './AuthContext.js'

export default function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState('loading')

  const setSession = useCallback((nextUser) => {
    setUser(nextUser)
    setStatus(nextUser ? 'authenticated' : 'guest')
  }, [])

  useEffect(() => {
    const controller = new AbortController()

    authApi
      .getMe({ signal: controller.signal })
      .then(setSession)
      .catch((error) => {
        if (error.name === 'AbortError') return
        setSession(null)
      })

    return () => controller.abort()
  }, [setSession])

  const value = useMemo(() => ({ user, status }), [user, status])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

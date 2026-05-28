import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function ProtectedRoute({ children, allowedRoles }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    const redirect = user.role === 'UPLOADER' ? '/dashboard'
      : user.role === 'ANALYST' ? '/analyst' : '/admin'
    return <Navigate to={redirect} replace />
  }
  return children
}

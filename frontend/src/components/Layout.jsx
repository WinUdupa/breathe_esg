import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  const homeLink = user?.role === 'UPLOADER' ? '/dashboard'
    : user?.role === 'ANALYST' ? '/analyst'
    : '/admin'

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <Link to={homeLink} className="text-lg font-semibold text-gray-900">
          Breathe ESG
        </Link>
        <div className="flex items-center gap-4 text-sm text-gray-600">
          <span>{user?.username} ({user?.role})</span>
          <button
            onClick={handleLogout}
            className="text-red-600 hover:text-red-800"
          >
            Logout
          </button>
        </div>
      </header>
      <main className="flex-1 p-6">{children}</main>
    </div>
  )
}

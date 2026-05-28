import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import UserDashboard from './pages/user/UserDashboard'
import UserUploadDetail from './pages/user/UserUploadDetail'
import AnalystDashboard from './pages/analyst/AnalystDashboard'
import UploadSummary from './pages/analyst/UploadSummary'
import ScopeRowView from './pages/analyst/ScopeRowView'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminBatchView from './pages/admin/AdminBatchView'

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 10000 } },
})

function RootRedirect() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (user.role === 'UPLOADER') return <Navigate to="/dashboard" replace />
  if (user.role === 'ANALYST') return <Navigate to="/analyst" replace />
  return <Navigate to="/admin" replace />
}

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            {/* Uploader */}
            <Route path="/dashboard" element={
              <ProtectedRoute allowedRoles={['UPLOADER', 'ANALYST', 'ADMIN']}>
                <UserDashboard />
              </ProtectedRoute>
            } />
            <Route path="/uploads/:id" element={
              <ProtectedRoute allowedRoles={['UPLOADER', 'ANALYST', 'ADMIN']}>
                <UserUploadDetail />
              </ProtectedRoute>
            } />

            {/* Analyst */}
            <Route path="/analyst" element={
              <ProtectedRoute allowedRoles={['ANALYST', 'ADMIN']}>
                <AnalystDashboard />
              </ProtectedRoute>
            } />
            <Route path="/analyst/batch/:id" element={
              <ProtectedRoute allowedRoles={['ANALYST', 'ADMIN']}>
                <UploadSummary />
              </ProtectedRoute>
            } />
            <Route path="/analyst/batch/:id/scope/:scope" element={
              <ProtectedRoute allowedRoles={['ANALYST', 'ADMIN']}>
                <ScopeRowView />
              </ProtectedRoute>
            } />

            {/* Admin */}
            <Route path="/admin" element={
              <ProtectedRoute allowedRoles={['ADMIN']}>
                <AdminDashboard />
              </ProtectedRoute>
            } />
            <Route path="/admin/batch/:id" element={
              <ProtectedRoute allowedRoles={['ADMIN']}>
                <AdminBatchView />
              </ProtectedRoute>
            } />
            <Route path="/admin/batch/:id/scope/:scope" element={
              <ProtectedRoute allowedRoles={['ADMIN']}>
                <ScopeRowView readonly />
              </ProtectedRoute>
            } />

            <Route path="/" element={<RootRedirect />} />
            <Route path="*" element={<RootRedirect />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import UserDashboard from './pages/user/UserDashboard'
import SubmissionDetail from './pages/user/SubmissionDetail'
import UserUploadDetail from './pages/user/UserUploadDetail'
import AnalystDashboard from './pages/analyst/AnalystDashboard'
import AnalystSubmissionDetail from './pages/analyst/AnalystSubmissionDetail'
import UploadSummary from './pages/analyst/UploadSummary'
import ScopeRowView from './pages/analyst/ScopeRowView'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminSubmissionView from './pages/admin/AdminSubmissionView'
import AdminBatchView from './pages/admin/AdminBatchView'
import AuditLogPage from './pages/admin/AuditLogPage'
import PeriodManagement from './pages/admin/PeriodManagement'
import ReportingPage from './pages/ReportingPage'

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
            <Route path="/submissions/:id" element={
              <ProtectedRoute allowedRoles={['UPLOADER', 'ANALYST', 'ADMIN']}>
                <SubmissionDetail />
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
            <Route path="/analyst/submission/:id" element={
              <ProtectedRoute allowedRoles={['ANALYST', 'ADMIN']}>
                <AnalystSubmissionDetail />
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
            <Route path="/admin/submission/:id" element={
              <ProtectedRoute allowedRoles={['ADMIN']}>
                <AdminSubmissionView />
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

            {/* Reporting — analyst + admin */}
            <Route path="/reporting" element={
              <ProtectedRoute allowedRoles={['ANALYST', 'ADMIN']}>
                <ReportingPage />
              </ProtectedRoute>
            } />

            {/* Admin tools */}
            <Route path="/admin/audit" element={
              <ProtectedRoute allowedRoles={['ADMIN']}>
                <AuditLogPage />
              </ProtectedRoute>
            } />
            <Route path="/admin/periods" element={
              <ProtectedRoute allowedRoles={['ADMIN']}>
                <PeriodManagement />
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

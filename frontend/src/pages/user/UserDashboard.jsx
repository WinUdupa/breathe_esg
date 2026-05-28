import { useState, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../../api/client'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'

const SOURCE_TYPES = [
  { value: 'SAP', label: 'SAP Fuel & Procurement' },
  { value: 'UTILITY', label: 'Utility Electricity' },
  { value: 'TRAVEL', label: 'Corporate Travel' },
]

export default function UserDashboard() {
  const qc = useQueryClient()
  const [sourceType, setSourceType] = useState('SAP')
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadError, setUploadError] = useState('')
  const [uploadSuccess, setUploadSuccess] = useState('')
  const fileRef = useRef()

  const { data: batches = [], isLoading } = useQuery({
    queryKey: ['batches'],
    queryFn: () => api.get('/ingestion/batches/').then(r => r.data),
  })

  const uploadMutation = useMutation({
    mutationFn: async () => {
      const fd = new FormData()
      fd.append('source_type', sourceType)
      fd.append('file', uploadFile)
      return api.post('/ingestion/upload/', fd)
    },
    onSuccess: (res) => {
      setUploadSuccess(`Uploaded: ${res.data.file_name} — ${res.data.row_count} rows`)
      setUploadFile(null)
      setUploadError('')
      if (fileRef.current) fileRef.current.value = ''
      qc.invalidateQueries({ queryKey: ['batches'] })
    },
    onError: (err) => {
      setUploadError(err.response?.data?.detail || 'Upload failed')
    },
  })

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <h2 className="text-xl font-semibold text-gray-900 mb-6">Upload Emissions Data</h2>

        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-8">
          <div className="flex gap-3 mb-4">
            {SOURCE_TYPES.map(st => (
              <button
                key={st.value}
                onClick={() => setSourceType(st.value)}
                className={`px-4 py-2 rounded-md text-sm font-medium border ${
                  sourceType === st.value
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                }`}
              >
                {st.label}
              </button>
            ))}
          </div>
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center mb-4">
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              onChange={e => setUploadFile(e.target.files[0])}
              className="hidden"
              id="file-input"
            />
            <label htmlFor="file-input" className="cursor-pointer">
              {uploadFile ? (
                <span className="text-gray-900 font-medium">{uploadFile.name}</span>
              ) : (
                <span className="text-gray-500">
                  <span className="text-blue-600 hover:underline">Choose a CSV file</span> or drag and drop
                </span>
              )}
            </label>
          </div>
          {uploadError && <p className="text-red-600 text-sm mb-3">{uploadError}</p>}
          {uploadSuccess && <p className="text-green-600 text-sm mb-3">{uploadSuccess}</p>}
          <button
            onClick={() => uploadMutation.mutate()}
            disabled={!uploadFile || uploadMutation.isPending}
            className="bg-blue-600 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {uploadMutation.isPending ? 'Uploading…' : 'Upload'}
          </button>
        </div>

        <h2 className="text-xl font-semibold text-gray-900 mb-4">Upload History</h2>
        {isLoading ? (
          <p className="text-gray-500">Loading…</p>
        ) : batches.length === 0 ? (
          <p className="text-gray-500">No uploads yet.</p>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">File Name</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Type</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Submitted</th>
                  <th className="text-right px-4 py-3 font-medium text-gray-600">Rows</th>
                  <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {batches.map(b => (
                  <tr key={b.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{b.file_name}</td>
                    <td className="px-4 py-3 text-gray-600">{b.source_type}</td>
                    <td className="px-4 py-3 text-gray-600">
                      {new Date(b.uploaded_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-right text-gray-600">{b.row_count ?? '—'}</td>
                    <td className="px-4 py-3"><StatusBadge status={b.status} /></td>
                    <td className="px-4 py-3 text-right">
                      <Link to={`/uploads/${b.id}`} className="text-blue-600 hover:underline text-xs">
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  )
}

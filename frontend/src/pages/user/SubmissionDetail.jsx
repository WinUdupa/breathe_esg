import { useRef, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, Link, useNavigate } from 'react-router-dom'
import api from '../../api/client'
import Layout from '../../components/Layout'
import StatusBadge from '../../components/StatusBadge'

const FILE_SLOTS = [
  { type: 'SAP', label: 'SAP Fuel & Procurement', icon: '🏭' },
  { type: 'UTILITY', label: 'Utility Electricity', icon: '⚡' },
  { type: 'TRAVEL', label: 'Corporate Travel', icon: '✈️' },
]

function FileSlot({ slot, file, submissionId, submissionOpen, onUploaded, onDeleted }) {
  const fileRef = useRef()
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  async function handleUpload(e) {
    const f = e.target.files[0]
    if (!f) return
    setError('')
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('source_type', slot.type)
      fd.append('file', f)
      const res = await api.post(`/ingestion/submissions/${submissionId}/upload/`, fd)
      onUploaded(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  async function handleDelete() {
    if (!file) return
    try {
      const res = await api.delete(`/ingestion/files/${file.id}/delete/`)
      onDeleted(res.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Delete failed')
    }
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">{slot.icon}</span>
        <span className="font-medium text-gray-900">{slot.label}</span>
      </div>

      {file ? (
        <div>
          <div className="flex items-center justify-between mb-2">
            <div>
              <div className="text-sm font-medium text-gray-800">{file.file_name}</div>
              <div className="text-xs text-gray-500">{file.row_count ?? '—'} rows</div>
            </div>
            <StatusBadge status={file.status} />
          </div>

          {file.error_log?.length > 0 && (
            <div className="text-xs text-red-600 bg-red-50 rounded p-2 mb-2">
              {file.error_log.join('; ')}
            </div>
          )}

          {submissionOpen && (
            <button
              onClick={handleDelete}
              className="text-xs text-red-600 hover:underline mt-1"
            >
              Delete and re-upload
            </button>
          )}
        </div>
      ) : (
        <div>
          {submissionOpen ? (
            <>
              <input
                ref={fileRef}
                type="file"
                accept=".csv"
                onChange={handleUpload}
                className="hidden"
                id={`file-${slot.type}`}
              />
              <label
                htmlFor={`file-${slot.type}`}
                className={`inline-block px-4 py-2 text-sm rounded border border-dashed border-gray-300 text-gray-600 cursor-pointer hover:bg-gray-50 ${uploading ? 'opacity-50 pointer-events-none' : ''}`}
              >
                {uploading ? 'Uploading…' : 'Choose CSV file'}
              </label>
            </>
          ) : (
            <span className="text-sm text-gray-400 italic">Not uploaded</span>
          )}
        </div>
      )}

      {error && <p className="text-xs text-red-600 mt-2">{error}</p>}
    </div>
  )
}

export default function SubmissionDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [submitError, setSubmitError] = useState('')
  const [showConfirm, setShowConfirm] = useState(false)

  const { data: submission, isLoading, refetch } = useQuery({
    queryKey: ['submission', id],
    queryFn: () => api.get(`/ingestion/submissions/${id}/`).then(r => r.data),
  })

  const submitMutation = useMutation({
    mutationFn: () => api.post(`/ingestion/submissions/${id}/submit/`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['submissions'] })
      qc.invalidateQueries({ queryKey: ['submission', id] })
      navigate('/dashboard')
    },
    onError: (err) => setSubmitError(err.response?.data?.detail || 'Submit failed'),
  })

  if (isLoading) return <Layout><p className="text-gray-500">Loading…</p></Layout>
  if (!submission) return <Layout><p className="text-red-600">Not found</p></Layout>

  const isFinalized = submission.status === 'FINALIZED'
  const isOpen = submission.status === 'OPEN'
  const files = submission.files || []
  const allReady = files.length > 0 && files.every(f => f.status === 'PENDING_REVIEW')
  const hasProcessing = files.some(f => f.status === 'PROCESSING')
  const hasFailed = files.some(f => f.status === 'FAILED')

  function handleFileChange(updatedSubmission) {
    qc.setQueryData(['submission', id], updatedSubmission)
    qc.invalidateQueries({ queryKey: ['submissions'] })
  }

  return (
    <Layout>
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center gap-3 mb-6">
          <Link to="/dashboard" className="text-blue-600 hover:underline text-sm">← My Batches</Link>
        </div>

        <div className="flex items-center justify-between mb-5">
          <h2 className="text-xl font-semibold text-gray-900">Batch #{submission.batch_number}</h2>
          <StatusBadge status={submission.status} />
        </div>

        <div className="flex flex-col gap-4 mb-6">
          {FILE_SLOTS.map(slot => {
            const file = files.find(f => f.source_type === slot.type)
            return (
              <FileSlot
                key={slot.type}
                slot={slot}
                file={file}
                submissionId={id}
                submissionOpen={!isFinalized}
                onUploaded={handleFileChange}
                onDeleted={handleFileChange}
              />
            )
          })}
        </div>

        {!isFinalized && (
          <div className="bg-white border border-gray-200 rounded-lg p-5">
            {hasProcessing && (
              <p className="text-blue-600 text-sm mb-3">⏳ Files are still processing…</p>
            )}
            {hasFailed && (
              <p className="text-red-600 text-sm mb-3">
                ⚠ One or more files failed. Delete and re-upload them before submitting.
              </p>
            )}
            {!hasProcessing && !hasFailed && files.length === 0 && (
              <p className="text-gray-500 text-sm mb-3">Upload at least one file to submit for review.</p>
            )}
            {!showConfirm ? (
              <button
                onClick={() => setShowConfirm(true)}
                disabled={!allReady || hasProcessing || hasFailed}
                className="bg-green-600 text-white px-6 py-2 rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Submit for Review
              </button>
            ) : (
              <div className="flex flex-col gap-3">
                <p className="text-sm text-gray-700">
                  Submit Batch #{submission.batch_number} for analyst review?
                  You will not be able to upload or delete files after this.
                </p>
                {submitError && <p className="text-red-600 text-sm">{submitError}</p>}
                <div className="flex gap-3">
                  <button
                    onClick={() => submitMutation.mutate()}
                    disabled={submitMutation.isPending}
                    className="bg-green-600 text-white px-5 py-2 rounded-md text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                  >
                    {submitMutation.isPending ? 'Submitting…' : 'Confirm Submit'}
                  </button>
                  <button
                    onClick={() => setShowConfirm(false)}
                    className="bg-gray-100 text-gray-700 px-4 py-2 rounded-md text-sm hover:bg-gray-200"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {isFinalized && (
          <p className="text-sm text-gray-500 text-center mt-4">
            Finalized {submission.finalized_at && new Date(submission.finalized_at).toLocaleString()} — all records are locked.
          </p>
        )}
      </div>
    </Layout>
  )
}

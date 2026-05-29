import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../../api/client'
import Layout from '../../components/Layout'

export default function PeriodManagement() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', start_date: '', end_date: '' })
  const [formError, setFormError] = useState('')

  const { data: periods = [], isLoading } = useQuery({
    queryKey: ['periods'],
    queryFn: () => api.get('/periods/').then(r => r.data),
  })

  const createMutation = useMutation({
    mutationFn: () => api.post('/periods/', form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['periods'] })
      setForm({ name: '', start_date: '', end_date: '' })
      setShowForm(false)
      setFormError('')
    },
    onError: (err) => setFormError(err.response?.data?.detail || 'Create failed'),
  })

  const lockMutation = useMutation({
    mutationFn: (id) => api.post(`/periods/${id}/lock/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['periods'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id) => api.delete(`/periods/${id}/`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['periods'] }),
  })

  return (
    <Layout>
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">Reporting Periods</h2>
          <button
            onClick={() => setShowForm(v => !v)}
            className="bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-blue-700"
          >
            + New Period
          </button>
        </div>

        {showForm && (
          <div className="bg-white border border-gray-200 rounded-lg p-5 mb-6">
            <h3 className="font-medium text-gray-900 mb-4">Create Reporting Period</h3>
            <div className="grid grid-cols-3 gap-4 mb-4">
              <div>
                <label className="block text-xs text-gray-600 mb-1">Name</label>
                <input
                  type="text"
                  placeholder="e.g. FY2025"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">Start Date</label>
                <input
                  type="date"
                  value={form.start_date}
                  onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-600 mb-1">End Date</label>
                <input
                  type="date"
                  value={form.end_date}
                  onChange={e => setForm(f => ({ ...f, end_date: e.target.value }))}
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm"
                />
              </div>
            </div>
            {formError && <p className="text-red-600 text-sm mb-3">{formError}</p>}
            <div className="flex gap-3">
              <button
                onClick={() => createMutation.mutate()}
                disabled={createMutation.isPending || !form.name || !form.start_date || !form.end_date}
                className="bg-blue-600 text-white px-5 py-2 rounded-md text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
              >
                {createMutation.isPending ? 'Creating…' : 'Create'}
              </button>
              <button
                onClick={() => { setShowForm(false); setFormError('') }}
                className="bg-gray-100 text-gray-700 px-4 py-2 rounded-md text-sm hover:bg-gray-200"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {isLoading ? (
          <p className="text-gray-500">Loading…</p>
        ) : periods.length === 0 ? (
          <p className="text-gray-500">No reporting periods yet.</p>
        ) : (
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-5 py-3 font-medium text-gray-600">Name</th>
                  <th className="text-left px-5 py-3 font-medium text-gray-600">Start</th>
                  <th className="text-left px-5 py-3 font-medium text-gray-600">End</th>
                  <th className="text-left px-5 py-3 font-medium text-gray-600">Status</th>
                  <th className="px-5 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {periods.map(p => (
                  <tr key={p.id} className="hover:bg-gray-50">
                    <td className="px-5 py-3 font-medium text-gray-900">{p.name}</td>
                    <td className="px-5 py-3 text-gray-600">{p.start_date}</td>
                    <td className="px-5 py-3 text-gray-600">{p.end_date}</td>
                    <td className="px-5 py-3">
                      {p.is_locked ? (
                        <span className="inline-flex items-center gap-1 text-xs bg-gray-200 text-gray-600 px-2 py-0.5 rounded">
                          🔒 Locked {p.locked_by && `by ${p.locked_by}`}
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded">
                          ✓ Open
                        </span>
                      )}
                    </td>
                    <td className="px-5 py-3 text-right">
                      <div className="flex justify-end gap-2">
                        {!p.is_locked && (
                          <>
                            <button
                              onClick={() => lockMutation.mutate(p.id)}
                              disabled={lockMutation.isPending}
                              className="text-xs px-3 py-1 rounded border border-gray-300 text-gray-600 hover:bg-gray-50"
                            >
                              Lock
                            </button>
                            <button
                              onClick={() => {
                                if (confirm(`Delete "${p.name}"?`)) deleteMutation.mutate(p.id)
                              }}
                              className="text-xs px-3 py-1 rounded border border-red-200 text-red-600 hover:bg-red-50"
                            >
                              Delete
                            </button>
                          </>
                        )}
                      </div>
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

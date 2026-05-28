export default function FlagBadge({ flags }) {
  if (!flags || flags.length === 0) return <span className="text-green-600 text-xs">Clean</span>
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-amber-100 text-amber-700">
      ⚠ {flags.length} flag{flags.length > 1 ? 's' : ''}
    </span>
  )
}

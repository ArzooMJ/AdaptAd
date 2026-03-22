interface Props {
  decision: string
  size?: 'sm' | 'md' | 'lg'
}

const styles: Record<string, string> = {
  SHOW:     'bg-show/20 text-show border-show/40',
  SOFTEN:   'bg-soften/20 text-soften border-soften/40',
  DELAY:    'bg-delay/20 text-delay border-delay/40',
  SUPPRESS: 'bg-suppress/20 text-suppress border-suppress/40',
}

const sizes = { sm: 'px-2 py-0.5 text-xs', md: 'px-3 py-1 text-sm', lg: 'px-4 py-1.5 text-base' }

export default function DecisionBadge({ decision, size = 'md' }: Props) {
  return (
    <span className={`inline-block border rounded-full font-semibold tracking-wide ${styles[decision] ?? 'bg-gray-700 text-gray-300 border-gray-600'} ${sizes[size]}`}>
      {decision}
    </span>
  )
}

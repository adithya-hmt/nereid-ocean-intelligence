type Props = { timestamps: readonly string[]; cutoff: number; onChange: (cutoff: number) => void }

export function TimeController({ timestamps, cutoff, onChange }: Props) {
  if (!timestamps.length) return null
  const timestamp = timestamps[cutoff] ?? timestamps[timestamps.length - 1]
  return <label className="time-controller">Time cutoff
    <input aria-label="Time cutoff" type="range" min="0" max={timestamps.length - 1} value={cutoff} onChange={(event) => onChange(Number(event.target.value))} />
    <output>{new Date(timestamp).toISOString()}</output>
  </label>
}

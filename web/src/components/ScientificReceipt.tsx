import { exportEvidence } from '../lib/api'
import type { ResultEnvelope } from '../lib/types'

const parameterValue = (value: unknown) => typeof value === 'string' ? value : JSON.stringify(value)

export function ScientificReceipt({ result }: { result: ResultEnvelope }) {
  const download = async () => {
    const blob = await exportEvidence(result)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'nereid-evidence.zip'
    anchor.click()
    URL.revokeObjectURL(url)
  }
  const profiles = Array.from(new Set(result.data.filter((row) => row.wmo !== undefined && row.cycle !== undefined).map((row) => `${String(row.wmo)} / cycle ${String(row.cycle)}${row.source_profile_index === undefined ? '' : ` / representation ${String(row.source_profile_index)}${row.vertical_sampling_scheme === undefined ? '' : ` (${String(row.vertical_sampling_scheme)})`}`}`)))
  return <section className="receipt" aria-labelledby="receipt-heading"><h2 id="receipt-heading">Scientific receipt</h2><button type="button" onClick={() => void download()}>Download evidence ZIP</button>{profiles.length > 0 && <p>Profiles: {profiles.join(', ')}</p>}<div className="receipt-counts"><span><strong>{result.qc_summary.retained}</strong> retained</span><span><strong>{result.qc_summary.rejected}</strong> excluded</span></div><div className="receipt-columns"><div><h3>Sources</h3>{result.provenance.length ? result.provenance.map((source) => <p key={source.sha256}><a href={source.source_url}>Source file</a><br />DOI {source.snapshot_doi}<br />Fetched <time dateTime={source.fetched_at}>{source.fetched_at}</time><br /><code>{source.sha256}</code></p>) : <p>No source files in this result.</p>}</div><div><h3>Methods</h3>{result.methods.map((method) => <div key={method.name}><p>{method.name}<br /><small>v{method.version}</small></p><dl>{Object.entries(method.parameters).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{parameterValue(value)}</dd></div>)}</dl></div>)}</div><div><h3>Assumptions & warnings</h3>{[...result.assumptions, ...result.warnings].length ? [...result.assumptions, ...result.warnings].map((item) => <p key={item}>{item}</p>) : <p>No additional warnings.</p>}</div></div></section>
}

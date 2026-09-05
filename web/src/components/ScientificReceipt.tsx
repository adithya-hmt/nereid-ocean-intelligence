import { useState } from 'react'
import { exportEvidence } from '../lib/api'
import type { ResultEnvelope } from '../lib/types'

const parameterValue = (value: unknown) => typeof value === 'string' ? value : JSON.stringify(value)
type Selection = { wmo: string; cycle: number; source_profile_index: number }

export function ScientificReceipt({ result }: { result: ResultEnvelope }) {
  const representations = Array.from(new Map(result.data.filter((row) => row.wmo !== undefined && row.cycle !== undefined && row.source_profile_index !== undefined).map((row) => {
    const selection = { wmo: String(row.wmo), cycle: Number(row.cycle), source_profile_index: Number(row.source_profile_index) }
    return [`${selection.wmo}/${selection.cycle}/${selection.source_profile_index}`, { ...selection, scheme: String(row.vertical_sampling_scheme) }]
  })).values())
  const [selected, setSelected] = useState<Selection[]>(() => representations.map(({ wmo, cycle, source_profile_index }) => ({ wmo, cycle, source_profile_index })))
  const toggle = (selection: Selection) => setSelected((current) => current.some((item) => item.wmo === selection.wmo && item.cycle === selection.cycle && item.source_profile_index === selection.source_profile_index) ? current.filter((item) => item.wmo !== selection.wmo || item.cycle !== selection.cycle || item.source_profile_index !== selection.source_profile_index) : [...current, selection])
  const download = async () => {
    const blob = await exportEvidence(result.query_plan, selected)
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a')
    anchor.href = url; anchor.download = 'nereid-evidence.zip'; anchor.click(); URL.revokeObjectURL(url)
  }
  return <section className="receipt" aria-labelledby="receipt-heading"><h2 id="receipt-heading">Scientific receipt</h2><fieldset><legend>Select profile representations for evidence export</legend>{representations.map((item) => <label key={`${item.wmo}/${item.cycle}/${item.source_profile_index}`}><input type="checkbox" checked={selected.some((choice) => choice.wmo === item.wmo && choice.cycle === item.cycle && choice.source_profile_index === item.source_profile_index)} onChange={() => toggle(item)} />{item.wmo} / cycle {item.cycle} / representation {item.source_profile_index} ({item.scheme})</label>)}</fieldset><button type="button" onClick={() => void download()} disabled={!selected.length}>Download evidence ZIP</button><div className="receipt-counts"><span><strong>{result.qc_summary.retained}</strong> retained</span><span><strong>{result.qc_summary.rejected}</strong> excluded</span></div><div className="receipt-columns"><div><h3>Sources</h3>{result.provenance.map((source) => <p key={source.sha256}><a href={source.source_url}>Source file</a><br />DOI {source.snapshot_doi}<br />Fetched <time dateTime={source.fetched_at}>{source.fetched_at}</time><br /><code>{source.sha256}</code></p>)}</div><div><h3>Methods</h3>{result.methods.map((method) => <div key={method.name}><p>{method.name}</p><dl>{Object.entries(method.parameters).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{parameterValue(value)}</dd></div>)}</dl></div>)}</div><div><h3>Assumptions & warnings</h3>{[...result.assumptions, ...result.warnings].map((item) => <p key={item}>{item}</p>)}</div></div></section>
}

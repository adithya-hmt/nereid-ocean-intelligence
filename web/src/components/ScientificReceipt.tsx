import { exportEvidence } from '../lib/api'
import type { ProfileIdentifier, ResultEnvelope } from '../lib/types'

type Selection = ProfileIdentifier & { source_profile_index: number }
type Props = { result: ResultEnvelope; selections: Selection[]; onSelectionChange: (selections: Selection[]) => void }

const parameterValue = (value: unknown) => typeof value === 'string' ? value : JSON.stringify(value)
const same = (left: Selection, right: Selection) => left.wmo === right.wmo && left.cycle === right.cycle && left.direction === right.direction && left.source_profile_index === right.source_profile_index

export function ScientificReceipt({ result, selections, onSelectionChange }: Props) {
  const representations = Array.from(new Map(result.data.filter((row) => row.wmo !== undefined && row.cycle !== undefined && (row.direction === 'A' || row.direction === 'D') && row.source_profile_index !== undefined).map((row) => {
    const selection = { wmo: String(row.wmo), cycle: Number(row.cycle), direction: row.direction as 'A' | 'D', source_profile_index: Number(row.source_profile_index) }
    return [`${selection.wmo}/${selection.cycle}/${selection.direction}/${selection.source_profile_index}`, { ...selection, scheme: String(row.vertical_sampling_scheme) }]
  })).values())
  const toggle = (selection: Selection) => onSelectionChange(selections.some((item) => same(item, selection)) ? selections.filter((item) => !same(item, selection)) : [...selections, selection])
  const download = async () => {
    const blob = await exportEvidence(result.query_plan, selections)
    const url = URL.createObjectURL(blob); const anchor = document.createElement('a')
    anchor.href = url; anchor.download = 'nereid-evidence.zip'; anchor.click(); URL.revokeObjectURL(url)
  }
  return <section className="receipt" aria-labelledby="receipt-heading"><h2 id="receipt-heading">Scientific receipt</h2><fieldset><legend>Select exact profile representations for linked views and evidence export</legend>{representations.map((item) => <label key={`${item.wmo}/${item.cycle}/${item.direction}/${item.source_profile_index}`}><input type="checkbox" checked={selections.some((choice) => same(choice, item))} onChange={() => toggle(item)} />{item.wmo} / cycle {item.cycle} / {item.direction} / representation {item.source_profile_index} ({item.scheme})</label>)}</fieldset><button type="button" onClick={() => void download()} disabled={!selections.length}>Download evidence ZIP</button><div className="receipt-counts"><span><strong>{result.qc_summary.retained}</strong> retained</span><span><strong>{result.qc_summary.rejected}</strong> excluded</span></div><div className="receipt-columns"><div><h3>Sources</h3>{result.provenance.map((source) => <p key={source.sha256}><a href={source.source_url}>Source file</a><br />DOI {source.snapshot_doi}<br />Fetched <time dateTime={source.fetched_at}>{source.fetched_at}</time><br /><code>{source.sha256}</code></p>)}</div><div><h3>Methods</h3>{result.methods.map((method) => <div key={method.name}><p>{method.name}</p><dl>{Object.entries(method.parameters).map(([name, value]) => <div key={name}><dt>{name}</dt><dd>{parameterValue(value)}</dd></div>)}{Object.entries(method.units ?? {}).map(([name, unit]) => <div key={`unit-${name}`}><dt>{name} units</dt><dd>{unit}</dd></div>)}</dl></div>)}</div><div><h3>Assumptions & warnings</h3>{[...result.assumptions, ...result.warnings].map((item) => <p key={item}>{item}</p>)}</div></div></section>
}

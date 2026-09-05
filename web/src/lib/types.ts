export type Operation = 'find_profiles' | 'nearest_floats' | 'get_profile' | 'compare_profiles' | 'derive_section' | 'export_selection'
export type Parameter = 'TEMP' | 'PSAL' | 'PRES'
export type QcPolicy = 'research' | 'exploratory'

export interface QueryPlan {
  operation: Operation
  bbox?: [number, number, number, number]
  start_date?: string
  end_date?: string
  parameters: Parameter[]
  qc_mode: QcPolicy
  wmo?: string
  cycle?: number
  row_limit: number
}

export interface Provenance { source_url: string; snapshot_doi: string; fetched_at: string; sha256: string }
export interface QcSummary { retained: number; rejected: number }
export interface MethodRecord { name: string; version: string; parameters: Record<string, unknown> }
export interface SectionRequest { profile_ids: [string, number][]; qc_mode: QcPolicy; depth_step_m: number; max_time_gap_hours: number; max_distance_km: number }
export interface ResultEnvelope {
  query_plan: QueryPlan
  data: Record<string, unknown>[]
  chart_spec: Record<string, unknown>[]
  provenance: Provenance[]
  qc_summary: QcSummary
  methods: MethodRecord[]
  assumptions: string[]
  warnings: string[]
  section_request?: SectionRequest | null
  answer?: string | null
}

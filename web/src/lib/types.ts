export type Operation = 'find_profiles' | 'nearest_floats' | 'get_profile' | 'compare_profiles' | 'derive_section'
export type Parameter = 'TEMP' | 'PSAL' | 'PRES'
export type QcPolicy = 'research' | 'exploratory'

export interface ProfileIdentifier { wmo: string; cycle: number; direction: 'A' | 'D'; source_profile_index?: number }

export interface QueryPlan {
  operation: Operation
  bbox?: [number, number, number, number]
  start_date?: string
  end_date?: string
  parameters: Parameter[]
  qc_mode: QcPolicy
  wmo?: string
  cycle?: number
  direction?: 'A' | 'D'
  float_count?: number
  profile_ids?: ProfileIdentifier[]
  row_limit: number
}

export interface Provenance { source_url: string; snapshot_doi: string; fetched_at: string; sha256: string }
export interface QcSummary { retained: number; rejected: number }
export interface MethodRecord { name: string; version: string; parameters: Record<string, unknown> }
export interface SectionRequest { profile_ids: Array<ProfileIdentifier & { source_profile_index: number }>; qc_mode: QcPolicy; depth_step_m: number; max_time_gap_hours: number; max_distance_km: number; max_vertical_gap_m: number }
export type ProfileMetricId = 'principal_thermocline' | 'strongest_salinity_gradient'
export interface ProfileMetric {
  wmo: string
  cycle: number
  direction: 'A' | 'D'
  source_profile_index: number
  name: ProfileMetricId
  value: number
  depth_m: number
  units: string
  uncertainty_m: number
  algorithm: string
  parameters: Record<string, unknown>
  quality_label: string
}
export interface SectionObservationCoordinate {
  wmo: string
  cycle: number
  direction: 'A' | 'D'
  source_profile_index: number
  vertical_sampling_scheme: string
  latitude: number
  longitude: number
  timestamp: string
}
export interface SectionCell {
  left_profile_index: number
  right_profile_index: number
  depth_m: number
  temperature: number | null
  salinity: number | null
  mask_reason?: string | null
}
export interface MaskedGap {
  left_profile_index: number
  right_profile_index: number
  reason: string
}
export interface SectionData {
  observation_coordinates?: SectionObservationCoordinate[]
  section_cells?: SectionCell[]
  masked_gaps?: MaskedGap[]
}
export interface ChartSpec { profile_metrics?: ProfileMetric[]; section?: Record<string, unknown>; [key: string]: unknown }
export interface ResultEnvelope {
  query_plan: QueryPlan
  data: Record<string, unknown>[]
  chart_spec: ChartSpec[]
  provenance: Provenance[]
  qc_summary: QcSummary
  methods: MethodRecord[]
  assumptions: string[]
  warnings: string[]
  section_request?: SectionRequest | null
  answer?: string | null
}

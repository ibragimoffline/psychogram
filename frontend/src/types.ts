export type Role = 'owner' | 'admin' | 'researcher' | 'operator' | 'auditor'
export interface Membership { organization_id: string; organization_name: string; role: Role; can_view_pii: boolean }
export interface Me { id: string; email: string; full_name: string; is_platform_admin: boolean; memberships: Membership[] }
export interface Research { id: string; tenant_id: string; name: string; purpose: string; status: string; methodology_version_id: string; pii_mode: string }
export interface Retention { id: string; code: string; retention_days: number; active: boolean; created_at: string }
export interface Licence { id: string; status: string; content_disclosure_level: string; allow_item_display: boolean; eligible: boolean; restrictions_i18n: Record<string,string> }
export interface InstrumentItem { item_code: string; item_type: 'integer'|'decimal'|'boolean'|'single_choice'|string; required: boolean; value_constraints?: Record<string, unknown>; prompt_i18n?: Record<string,string>; options?: {option_code:string;label_i18n:Record<string,string>}[] }
export interface Version { id:string; methodology_id:string; version_code:string; lifecycle_status:string; estimated_minutes:number; content_hash:string|null; snapshot:{items?:InstrumentItem[];scales?:Record<string,unknown>[]} | null; licence:Licence|null; eligible:boolean; disclaimer_i18n:Record<string,string> }
export interface Participant { id:string;research_id:string;external_code:string;processing_status:string;created_at:string;current_consent_status:string|null;has_pii:boolean }
export interface Page<T>{items:T[];total:number;offset:number;limit:number}
export interface ResponseItem {id:string;research_id:string;participant_id:string;participant_external_code:string;attempt_key:string;status:string;lock_version:number;current_revision_id:string|null;current_revision_number:number|null;current_revision_status:string|null;created_at:string}
export interface Revision {id:string;response_id:string;revision_number:number;status:string;answer_payload_hash:string;validation_summary:Record<string,unknown>;answers:Record<string,unknown>|null;is_current:boolean;correction_reason:string|null;created_at:string;source_type:string}
export interface ResponseDetail extends ResponseItem {methodology_version_id:string;current_revision:Revision|null}
export interface Scale {scale_code:string;validity_status:string;reason_codes:string[];answered_count:number;missing_count:number;score_display:string|null;unit_code:string;norm_band_code:string|null;interpretation_snapshot_i18n:Record<string,string>|null;disclosure_level_applied:string}
export interface Result {id:string;research_id:string;participant_id:string;response_id?:string;response_revision_id:string;status:string;disclaimer_i18n:Record<string,string>;calculated_at:string;result_hash:string;scales:Scale[];trace?:Record<string,unknown>[]}
export interface ImportIssue {row_number:number;column_name:string|null;item_code:string|null;error_code:string;severity:string;message_key:string;safe_params:Record<string,unknown>;rejected_value_preview:string;suggested_action:string}
export interface ImportPreview {import_id:string;status:string;preview_hash:string;summary:Record<string,number>;errors:ImportIssue[]}
export interface ApiErrorShape {error?:{code?:string;message?:string;details?:unknown};detail?:unknown}

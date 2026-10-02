# Psychogram — arxitektura, modellar va funksiyalar

Bu fayl loyihaning to'liq texnik xaritasi: qatlamlar, ma'lumotlar modeli, har bir
servis funksiyasi, API endpointlar, xavfsizlik va frontend tuzilishi. Ishga tushirish
bo'yicha qo'llanma — [README.md](README.md), metodika kontrakti va UX talablari —
[docs/](docs/).

> **Joriy yo'nalish:** pilot MVP qisqartirish topshirig'i —
> [docs/08_mvp_pilot_scope.md](docs/08_mvp_pilot_scope.md). A–E bosqichlarining kod qismi
> bajarilgan (`closed` holati, `POST /researches/{id}/close`, `GET /researches/{id}/export`);
> B (haqiqiy metodika paketi, [docs/10](docs/10_methodology_package.md)) va F (PostgreSQL pilot,
> backup/restore) ochiq.

---

## 1. Umumiy ko'rinish

Psychogram — psixologik tadqiqotlar uchun **multi-tenant scoring platformasi** (MVP).
Asosiy oqim:

```
Platform admin                Organization (tenant)                         Natija
──────────────                ─────────────────────                         ──────
Methodology  ──► Version ──► Licence ──► Publish
                                           │
                                           ▼
                       Research (pin: version + content_hash + norm)
                                           │ activate
                                           ▼
                       Participant ──► Consent ──► Response ──► Revision ──► Validate
                                           ▲                                   │
                       CSV import (preview → confirm) ─────────────────────────┤
                                                                               ▼
                                                     Calculation ──► Result + ScaleResult
                                                                    + ExplainabilityTrace
                                                                               │
                                                                               ▼
                                                                  Export (JSON / CSV)
```

Asosiy tamoyillar:

- **Deterministik scoring** — natija faqat immutable snapshot, validated revision va
  versiyalangan engine'dan hisoblanadi; `computation_key` hash orqali takror hisob
  bir xil natijani qaytaradi.
- **Immutability** — published metodika, validated revision, result, trace va audit
  ORM darajasida o'zgartirib/o'chirib bo'lmaydi.
- **Gate'lar** — har bir muhim amal oldidan licence, consent, research holati va
  methodology hash tekshiriladi (fail-closed).
- **Tenant izolyatsiyasi** — har bir tenant query `tenant_id` bilan cheklanadi.
- **Tibbiy tashxis emas** — har bir natijada `"Bu natija tibbiy tashxis emas."` disclaimer.

## 2. Texnologiyalar

| Qatlam | Stack |
|---|---|
| Backend | Python 3.14, FastAPI 0.139, Pydantic 2 / pydantic-settings, SQLAlchemy 2.0, Alembic |
| DB | SQLite (lokal), PostgreSQL (production, `psycopg2`) |
| Xavfsizlik | Argon2 (`pwdlib`), JWT HS256 (`PyJWT`), AES-256-GCM (`cryptography`) |
| Test / sifat | pytest, httpx, black, flake8, mypy |
| Frontend | React 19, TypeScript 5.8, Vite 7, React Router 7, TanStack Query 5, motion |
| Frontend test | Vitest, Testing Library, jsdom, ESLint |

## 3. Katalog tuzilishi

```
psychogram/
├── src/
│   ├── main.py                  # create_app(): FastAPI factory
│   ├── core/
│   │   ├── config.py            # Settings (PSYCHOGRAM_* env)
│   │   ├── db.py                # Database: engine + session factory
│   │   ├── errors.py            # DomainError + global handler
│   │   ├── middleware.py        # APISecurityMiddleware
│   │   └── security.py          # Argon2 + JWT
│   ├── models/domain.py         # Barcha ORM modellar + immutability hook
│   ├── schemas/
│   │   ├── api.py               # Write/command DTO'lar
│   │   └── read.py              # Read-model DTO'lar
│   ├── api/
│   │   ├── dependencies.py      # Auth, tenant, RBAC, PII dependency'lar
│   │   └── routers/
│   │       ├── auth.py          # /api/v1/auth/*
│   │       ├── v1.py            # Write (command) endpointlar
│   │       └── read.py          # Read, export, PII endpointlar
│   └── services/
│       ├── audit.py             # audit() yozuvchi
│       ├── domain.py            # Auth, member, research, participant, consent, response
│       ├── registry.py          # Methodology / version / licence / publish
│       ├── rule_engine.py       # Xavfsiz JSON-AST interpreter
│       ├── scoring_engine.py    # Toza scoring funksiyalari
│       ├── orchestration.py     # calculate(): gate'lar + persist
│       ├── imports.py           # CSV preview / confirm
│       ├── exports.py           # JSON / CSV export + redaction
│       └── pii.py               # AES-GCM PII saqlash
├── alembic/versions/            # 0001_initial, 0002_pii_aes_gcm_envelope
├── config/settings.py           # Eski import yo'li uchun re-export
├── tests/                       # pytest (65 funksiya, 74 holat)
├── frontend/                    # React SPA
└── docs/                        # 01..07 mahsulot, metodika, UX, QA hujjatlari
```

## 4. Backend arxitekturasi

Qatlamlar yuqoridan pastga bog'lanadi, teskari import yo'q:

```
HTTP ─► APISecurityMiddleware ─► CORSMiddleware ─► Router (auth / v1 / read)
                                                     │  Depends: get_db, current_user,
                                                     │  tenant_context, roles(), pii_access
                                                     ▼
                                                  Services  ──► audit()
                                                     │
                                                     ▼
                                       SQLAlchemy ORM (models/domain.py)
                                       + before_flush immutability hook
                                                     │
                                                     ▼
                                              SQLite / PostgreSQL
```

- **Routerlar** faqat HTTP, dependency va `db.commit()` bilan shug'ullanadi.
- **Servislar** biznes qoidalarini bajaradi, `db.flush()` qiladi, `DomainError` otadi
  va audit yozadi. Commit routerda — bitta request = bitta tranzaksiya.
- **scoring_engine** va **rule_engine** DB'ga bog'liq emas (toza funksiyalar).

### 4.1. Ilova yig'ilishi — `src/main.py`

`create_app(settings=None, database=None) -> FastAPI`
- `Settings` va `Database`ni yaratadi (testlarda tashqaridan beriladi).
- `lifespan`: `auto_create_schema=true` bo'lsa `Base.metadata.create_all` (default o'chiq —
  schema Alembic orqali).
- `DomainError` handler, `CORSMiddleware` (explicit allowlist, headerlar:
  `Authorization`, `Content-Type`, `X-Organization-ID`, `Idempotency-Key`),
  `APISecurityMiddleware`.
- Routerlar: `auth_router`, `v1_router`, `read_router`.
- `GET /` — nom va versiya; `GET /health` — `SELECT 1` bilan DB tekshiruvi.

### 4.2. Core

**`config.py` — `Settings`** (env prefiksi `PSYCHOGRAM_`, `.env` o'qiladi)

| Maydon | Default | Izoh |
|---|---|---|
| `environment` | `development` | `production` qat'iy tekshiruvlarni yoqadi |
| `database_url` | `sqlite:///./psychogram.db` | |
| `auto_create_schema` | `false` | |
| `jwt_secret` | tasodifiy | productionda explicit va ≥32 belgi shart |
| `jwt_algorithm` / `access_token_minutes` | `HS256` / `60` | |
| `bootstrap_enabled` / `bootstrap_token` | `false` / — | yoqilsa token ≥32 belgi |
| `registration_enabled` | `false` | ochiq `/auth/register`; pilotda o'chiq |
| `csv_import_enabled` | `false` | CSV preview/confirm; pilotning birinchi relizida o'chiq |
| `pii_encryption_key` / `pii_key_version` | — / `v1` | Base64, aniq 32 bayt |
| `cors_origins` | localhost:3000,5173 | `*` taqiqlangan |
| `max_csv_bytes` / `max_csv_rows` | 1 000 000 / 10 000 | |
| `max_request_body_bytes` | 3 100 000 | `max_csv_bytes`dan katta bo'lishi shart |

Validatorlar: `reject_wildcard_cors`, `validate_production_secrets`, `validate_pii_key`,
`_validate_pii_key`. Property: `cors_origin_list`. `get_settings()` — `lru_cache` singleton.

**`db.py` — `Database`**
- `__init__(settings)` — engine (`pool_pre_ping`), SQLite uchun `check_same_thread=False`,
  in-memory uchun `StaticPool`, `PRAGMA foreign_keys=ON`; `session_factory`
  (`expire_on_commit=False`, `autoflush=False`).
- `_enable_sqlite_foreign_keys(...)`, `session()` — generator.

**`errors.py`**
- `DomainError(code, message, status_code=400, details=None)` — barcha biznes xatolari.
- `domain_error_handler` → `{"error": {"code", "message", "details?"}}`.

**`security.py`**
- `hash_password(password)` — ≥12 belgi, aks holda `PASSWORD_TOO_WEAK`; Argon2.
- `verify_password(password, encoded) -> bool` — xatoda `False`.
- `create_access_token(user_id, settings) -> (token, expires_in_sec)` — `sub`, `iat`, `exp`, `type=access`.
- `decode_access_token(token, settings) -> user_id` — xato bo'lsa `AUTH_TOKEN_INVALID` (401).

**`middleware.py` — `APISecurityMiddleware`** (ASGI)
- Har bir javobga: `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`,
  `X-Frame-Options: DENY`; `/api/*` uchun qat'iy CSP.
- Sezgir yo'llar (`/api/v1/results*`, `*/calculations`, `*/pii`) uchun
  `Cache-Control: no-store, private` + `Pragma: no-cache`.
- `*/imports/preview` uchun body parse'dan oldin: `Content-Length` limitdan oshsa
  `413 REQUEST_BODY_TOO_LARGE`, UTF-8 bo'lmagan charset — `415 ENCODING_INVALID`.
- Yordamchilar: `_request_rejection`, `_charset`, `_is_sensitive`, `_error_response`.

### 4.3. API dependency'lar — `src/api/dependencies.py`

| Funksiya | Vazifasi |
|---|---|
| `get_db(request)` | Request uchun Session yaratib, oxirida yopadi |
| `get_runtime_settings(request)` | `app.state.settings` |
| `require_csv_import(settings)` | `csv_import_enabled=false` bo'lsa `CSV_IMPORT_DISABLED` 404 |
| `current_user(...)` | Bearer JWT → aktiv `User`, aks holda `AUTH_REQUIRED` 401 |
| `platform_admin(user)` | `is_platform_admin` talab qiladi → `ROLE_FORBIDDEN` 403 |
| `TenantContext` | `organization` + `membership` dataclass |
| `tenant_context(X-Organization-ID, ...)` | Aktiv membership + aktiv organization → `TENANT_ACCESS_DENIED` 403 |
| `roles(*allowed)` | Dependency factory: membership roli ro'yxatda bo'lishi shart |
| `pii_access(context)` | Rol `owner/admin/researcher` **va** `can_view_pii=true` |

## 5. Ma'lumotlar modeli — `src/models/domain.py`

Umumiy: `Base(DeclarativeBase)`, `IdMixin` (`id` = UUID string), `CreatedMixin`
(`created_at`, UTC). Yordamchilar: `new_id()`, `utcnow()`. Pul/ball qiymatlari
float emas, **canonical decimal string** sifatida saqlanadi.

### 5.1. ER diagramma (soddalashtirilgan)

```
Organization 1─* Membership *─1 User
Organization 1─* RetentionPolicy
Organization 1─* Research *─1 MethodologyVersion *─1 Methodology
Research 1─1 ResearchMethodologyPin
Research 1─* Participant 1─* ConsentRecord
                         1─0..1 ParticipantPII
Participant 1─* Response 1─* ResponseRevision 1─* ResponseValidationIssue
ResponseRevision 1─* CalculationRun 1─1 Result 1─* ScaleResult
                                    1─1 ExplainabilityTrace 1─* TraceStep
MethodologyVersion 1─* Item 1─* ResponseOption
                   1─* Scale *─* Item (ScaleItemLink)
                   1─* NormSet (per Scale) 1─* NormBand
                   1─* InterpretationRule (per Scale)
                   1─* LicenceRevision
Research 1─* ImportJob 1─* ImportRow, ImportIssue
Research 1─* LegalHold
AuditEvent (tenant_id?, research_id?, actor_id?)
ColumnMapping (MethodologyVersion uchun CSV shablon)
```

### 5.2. Identity va tenant

| Model (jadval) | Asosiy maydonlar | Cheklovlar |
|---|---|---|
| `Organization` (`organizations`) | `code` (unique), `name`, `org_type` (`research_center`), `region` (`GLOBAL`), `active` | |
| `User` (`users`) | `email` (unique), `full_name`, `password_hash`, `is_platform_admin`, `active` | |
| `Membership` (`memberships`) | `tenant_id`, `user_id`, `role`, `can_view_pii`, `active` | unique(tenant,user); role ∈ owner/admin/researcher/operator/auditor |
| `RetentionPolicy` (`retention_policies`) | `tenant_id`, `code`, `retention_days`, `active` | unique(tenant,code) |
| `LegalHold` (`legal_holds`) | `tenant_id`, `research_id`, `active`, `reason`, `created_by` | aktiv hold PII o'chirishni bloklaydi |

### 5.3. Metodika registri

| Model | Asosiy maydonlar |
|---|---|
| `Methodology` | `methodology_code` (unique), `canonical_name`, `purpose_summary`, `owner_name`, `source_reference`, `catalog_status` |
| `MethodologyVersion` | `methodology_id`, `version_code` (semver), `schema_version` (`methodology-contract/1`), `default_locale`, `supported_locales`, `target_population`, `estimated_minutes`, `lifecycle_status` (draft/in_review/published/deprecated/withdrawn), `content_hash`, `engine_contract_version` (`scoring/1`), `disclaimer_i18n`, **`snapshot`** (JSON — scoring uchun yagona manba), `template_id`, `published_at/by`, `supersedes_version_id` |
| `Item` | `item_code`, `item_type` (single_choice/integer/decimal/boolean), `prompt_i18n`, `required`, `value_constraints` (min/max/step), `missing_policy`, `score_mapping`, `reverse_scoring`, `item_transform_expr`, `sort_order` |
| `ResponseOption` | `item_id`, `option_code`, `label_i18n`, `ordinal_position`, `score_value` |
| `Scale` | `scale_code`, `scale_kind` (bitta `total` majburiy), `label_i18n`, `unit_code`, `theoretical_min/max`, `display_decimals`, `aggregation`, `transform_expr`, `validity_rules` |
| `ScaleItemLink` | `scale_id`, `item_id`, `weight` |
| `NormSet` | `scale_id`, `norm_code`, `norm_kind`, `population_descriptor`, `selection_constraints`, `source_reference`, `is_default`, `lookup_mode` |
| `NormBand` | `norm_set_id`, `band_code`, `lower_bound/inclusive`, `upper_bound/inclusive`, `normalized_value`, `label_i18n` |
| `InterpretationRule` | `scale_id`, `rule_code`, `priority`, `when_expr` (JSON-AST), `interpretation_code`, `title_i18n`, `text_i18n`, `disclaimer_i18n` |
| `LicenceRevision` | `licence_revision` (ketma-ket), `status` (verified/restricted/expired/revoked/unknown), `copyright_status`, `rights_holder`, `evidence_reference`, `allowed_use_types/org_types/regions`, `content_disclosure_level` (full/derived_only/summary_only), `allow_item_display/export`, `allow_trace_item_values`, `valid_from/until`, `required_disclaimer_i18n`, `restrictions_i18n`, `verified_by/at`, `change_reason` |
| `ColumnMapping` | `methodology_version_id`, `template_id`, `source_headers_hash`, `columns` |

> Normalizatsiya qilingan jadvallar (`Item`, `Scale`, `NormSet`...) `snapshot`dan
> `_materialize_snapshot` orqali yaratiladi; scoring esa **faqat `snapshot` JSON**dan ishlaydi.

### 5.4. Tadqiqot va ma'lumot yig'ish

| Model | Asosiy maydonlar |
|---|---|
| `Research` | `tenant_id`, `name`, `purpose`, `status` (draft→ready→active), `methodology_version_id`, `pii_mode` (anonymous/pseudonymous/identified), `consent_reference/version`, `retention_policy_id`, `responsible_user_id`, `use_type` (research/education/clinical) |
| `ResearchMethodologyPin` | `research_id` (unique), `methodology_version_id`, `methodology_content_hash`, `norm_selection` ({scale_code: norm_set_id}), `pinned_by` |
| `Participant` | `research_id`, `external_code` (research ichida unique), `processing_status` |
| `ParticipantPII` | `participant_id` (unique), `encrypted_payload`, `nonce`, `algorithm` (AES-256-GCM), `key_version`, `field_names`, `updated_at/by` |
| `ConsentRecord` | `participant_id`, `status` (granted/withdrawn/declined/not_required_with_basis), `reference`, `version`, `obtained_at`, `basis`, `record_version` (append-only, eng kattasi — joriy) |
| `Response` | `participant_id`, `attempt_key` (unique per participant), `methodology_version_id`, `current_revision_id`, `status` (draft/validation_failed/validated/scored), `lock_version` (optimistic lock) |
| `ResponseRevision` | `response_id`, `revision_number`, `answers` (kalitlari saralangan), `answer_payload_hash`, `status` (draft/validation_failed/validated), `validation_summary`, `source_type` (manual/...), `correction_reason`, `validated_at/by` |
| `ResponseValidationIssue` | `response_revision_id`, `item_code`, `error_code`, `safe_params` |

### 5.5. Hisoblash va natija

| Model | Asosiy maydonlar |
|---|---|
| `CalculationRun` | `response_revision_id`, `idempotency_key` (unique per tenant), `computation_key` (unique per tenant), `status` (running/succeeded), `engine_version`, `rule_interpreter_version`, `methodology_content_hash`, `licence_id/revision`, `started_at/finished_at`, `failure_code`, `retry_count` |
| `Result` | `calculation_run_id` (unique), participant/response/revision havolalari, `methodology_content_hash`, `status` (complete / complete_with_uninterpreted_scales), `disclaimer_i18n_snapshot`, `calculated_at/by`, `result_hash`, `retention_classification` |
| `ScaleResult` | `scale_code`, `validity_status` (valid/insufficient_data), `reason_codes`, `answered_count`, `missing_count`, `aggregate_score_unrounded`, `score_unrounded`, `score_display`, `unit_code`, `norm_band_code`, `normalized_value`, `interpretation_code`, `interpretation_snapshot_i18n`, `disclosure_level_applied` |
| `ExplainabilityTrace` | `result_id` (unique), `trace_schema_version` (`explainability/1`), `disclosure_level_applied`, `methodology_content_hash`, `response_revision_hash`, `trace_hash` |
| `TraceStep` | `trace_id`, `sequence`, `step_code`, `status`, `entity_ref`, `rule_ref`, `inputs`, `outputs`, `reason_code`, `message_key`, `redactions` |

### 5.6. Import va audit

| Model | Asosiy maydonlar |
|---|---|
| `ImportJob` | `research_id`, `status` (preview_ready→committing→completed), `file_hash`, `preview_hash`, `summary`, `staged_rows`, `confirmed_at/by` |
| `ImportRow` | `import_job_id`, `row_number`, `status` (accepted/rejected), `participant_id`, `response_id` |
| `ImportIssue` | `import_job_id`, `row_number`, `column_name`, `item_code`, `error_code`, `safe_params` |
| `AuditEvent` | `occurred_at`, `tenant_id`, `research_id`, `actor_id`, `object_type`, `object_id`, `action`, `outcome` (success/failure), `reason_code`, `correlation_id`, `safe_metadata` (raw javob / PII yo'q) |

### 5.7. Immutability hook

`enforce_immutable_records(session, ...)` — `Session.before_flush` listener:
- `Result`, `ScaleResult`, `ExplainabilityTrace`, `TraceStep`, `AuditEvent` — persistent
  bo'lgach o'zgartirib bo'lmaydi.
- `MethodologyVersion` — eski status published/deprecated/withdrawn bo'lsa o'zgarmaydi.
- `ResponseRevision` — eski status validated/superseded/withdrawn bo'lsa o'zgarmaydi.
- `ResearchMethodologyPin` — research `active` bo'lsa o'zgartirish/o'chirish taqiqlangan.
- Yuqoridagilar + `MethodologyVersion`, `ResponseRevision` application session orqali
  o'chirilmaydi.

### 5.8. Migratsiyalar

- `0001_initial` — barcha jadvallar.
- `0002_pii_aes_gcm` — `participant_pii`ga `nonce`, `algorithm`, `key_version`,
  `field_names`, `updated_at/by` qo'shadi; legacy qatorlar bo'lsa upgrade'ni to'xtatadi.

## 6. Servislar va funksiyalar

### 6.1. `services/audit.py`
- `audit(db, *, actor_id, action, object_type, object_id=None, tenant_id=None,
  research_id=None, outcome="success", reason_code=None, safe_metadata=None) -> AuditEvent`
  — har bir muhim amal uchun append-only yozuv.

Audit `action` qiymatlari: `auth.bootstrap`, `auth.login`, `organization.register`,
`membership.create`, `methodology.create`, `methodology_version.create`,
`methodology_version.publish`, `licence.revise`, `research.create`, `research.activate`,
`participant.create`, `consent.record`, `response.create`, `response.revise`,
`response.validate`, `calculation.start`, `calculation.succeed`, `import.preview`,
`import.confirm`, `result.export`, `pii.create`, `pii.update`, `pii.view`, `pii.delete`.

### 6.2. `services/domain.py` — asosiy domen amallari

| Funksiya | Nima qiladi | Asosiy xatolar |
|---|---|---|
| `canonical_answer_hash(answers)` | Saralangan JSON → `sha256:...` | |
| `bootstrap_user(db, payload, configured_token, *, enabled)` | Bo'sh DBda birinchi platform admin; token SHA-256 digest bilan constant-time solishtiriladi | `BOOTSTRAP_DISABLED` 404, `BOOTSTRAP_TOKEN_INVALID` 403, `BOOTSTRAP_ALREADY_COMPLETED` 409 |
| `register_owner(db, payload, *, actor_id=None)` | User + Organization + `owner` membership (`can_view_pii=true`); `actor_id` berilsa (admin) audit `organization.create`, aks holda `organization.register` | `EMAIL_ALREADY_REGISTERED`, `ORGANIZATION_CODE_EXISTS` 409 |
| `authenticate(db, email, password)` | Login; muvaffaqiyatsizlik ham audit qilinadi, xabar generic | `AUTH_CREDENTIALS_INVALID` 401 |
| `add_member(db, tenant_id, payload, actor_id)` | Mavjud yoki yangi userni tenantga qo'shadi | `MEMBERSHIP_EXISTS` 409 |
| `create_research(db, tenant, payload, actor_id)` | Published version + tenant retention policy + licence tekshiruvi; status `ready`; norm tanlanmasa default normlar; `ResearchMethodologyPin` yaratadi | `METHODOLOGY_NOT_PUBLISHED`, `RETENTION_POLICY_NOT_FOUND`, `LICENCE_NOT_VALID`, `NORM_PIN_INVALID` |
| `activate_research(db, tenant, research, actor_id)` | `ready → active` (idempotent), licence qayta tekshiriladi | `RESEARCH_STATE_INVALID`, `METHODOLOGY_NOT_PUBLISHED` |
| `create_participant(db, research, payload, actor_id)` | Faqat aktiv research; inline `pii` rad etiladi; kod research ichida unique | `RESEARCH_NOT_ACTIVE`, `PII_STORAGE_NOT_CONFIGURED`, `PARTICIPANT_CODE_EXISTS` 409 |
| `record_consent(db, participant, payload, actor_id)` | Append-only consent, `record_version+1` | `CONSENT_BASIS_REQUIRED` |
| `latest_consent(db, participant_id)` | Eng oxirgi consent yozuvi | |
| `require_valid_consent(db, participant_id)` | `granted` yoki asosli `not_required_with_basis` | `CONSENT_NOT_VALID` 409 |
| `create_response(db, research, payload, actor_id)` | Aktiv research + participant + consent; 1-revision; `finalize=true` bo'lsa darhol validatsiya | `RESPONSE_ATTEMPT_EXISTS`, `PARTICIPANT_NOT_FOUND` |
| `revise_response(db, response, payload, actor_id)` | `expected_lock_version` mos bo'lsa yangi revision, `lock_version+1`; joriy revision `validated` bo'lsa bo'sh bo'lmagan `correction_reason` shart | `REVISION_CONFLICT` 409, `CORRECTION_REASON_REQUIRED` 400 |
| `_new_revision(...)` | Revision raqami, normalizatsiya, hash; `current_revision_id` yangilanadi | |
| `validate_revision(db, response, revision, actor_id)` | Faqat joriy revision; allaqachon `validated`/`validation_failed` bo'lsa o'zgarishsiz qaytaradi; consent; `validate_answers`; issue'larni saqlaydi; status `validated` yoki `validation_failed` | `REVISION_NOT_CURRENT`, `CONSENT_NOT_VALID` |
| `validation_issues(db, revision_id)` | Revisionning saqlangan xatolari (`item_code`, `error_code` bo'yicha tartiblangan) | |

### 6.3. `services/registry.py` — metodika registri

| Funksiya | Nima qiladi |
|---|---|
| `canonical_hash(payload)` | Har qanday JSON uchun deterministik `sha256:` hash |
| `create_methodology(db, payload, actor_id)` | Unique `methodology_code` bilan katalog yozuvi |
| `validate_snapshot(snapshot, default_locale)` | items/scales bo'sh emas, kodlar unique, bitta `total` scale, item turi whitelist, single_choice uchun options, scale maydonlari, decimal formatlar, barcha AST'lar `RuleInterpreter.validate`, interpretation'da default locale |
| `_validate_norm(norm)` | Norm band chegaralari decimal, overlap yo'q (`NORM_OVERLAP`) |
| `create_version(db, methodology, payload, actor_id)` | Snapshot validatsiyasi, `template_id = tmpl_<hash12>`, `_materialize_snapshot` |
| `_materialize_snapshot(db, version, snapshot)` | Snapshot'dan Item, ResponseOption, Scale, ScaleItemLink, NormSet, NormBand, InterpretationRule qatorlarini yaratadi |
| `create_licence(db, version, payload, actor_id)` | Yangi licence revision (ketma-ket raqam) |
| `publish_version(db, version, actor_id, reason)` | draft/in_review → published; licence majburiy; `content_hash` hisoblanadi |
| `latest_licence(db, version_id)` | Eng oxirgi licence revision |
| `check_licence(licence, *, org_type, region, use_type, today=None)` | `verified`, sana oralig'i, use/org type, region (yoki `GLOBAL`) → aks holda `LICENCE_NOT_VALID` |

### 6.4. `services/rule_engine.py` — xavfsiz formula interpretatori

- Konstantalar: `DECIMAL_RE` (canonical decimal, ≤6 kasr), `NUMERIC_OPS`, `COMPARE_OPS`,
  `BOOL_OPS`, `ALLOWED_OPS`.
- `decimal_value(value) -> Decimal` — faqat canonical base-10, bool emas, `-0` emas, ≤18 raqam.
- `decimal_text(value) -> str` — ortiqcha nollarsiz matn.
- `class RuleInterpreter` (`version = "json-ast/1"`; limitlar: chuqurlik 20, tugun 500, arg 100)
  - `validate(node)` / `_validate(...)` — har bir operator uchun aniq maydonlar to'plami,
    `ref`da `.` traversal taqiqlangan, `round` faqat `half_up` va 0..6 kasr, `in` faqat
    1..100 unique skalyar.
  - `evaluate(node, context)` / `_evaluate(...)` — `ref` kaliti `"{kind}:{code}"`.
  - `_numeric`, `_bounded` (|x| ≤ 1e18).
- Operatorlar: `const`, `ref`, `add`, `sub`, `mul`, `div`, `min`, `max`, `abs`, `round`,
  `eq`, `ne`, `lt`, `lte`, `gt`, `gte`, `and`, `or`, `not`, `is_missing`, `is_valid`, `in`.
- `eval`/`exec`/import/DB/tarmoq/soatga murojaat yo'q. Xatolar: `RULE_SCHEMA_INVALID`,
  `RULE_LIMIT_EXCEEDED`, `DIVISION_BY_ZERO`.

### 6.5. `services/scoring_engine.py` — toza scoring

- `validate_answers(snapshot, answers) -> list[issue]` — kodlar: `UNKNOWN_ITEM`,
  `ITEM_REQUIRED`, `TYPE_INVALID`, `BOOLEAN_LITERAL_INVALID`, `OPTION_NOT_ALLOWED`,
  `VALUE_OUT_OF_RANGE`, `STEP_INVALID`.
- `score_snapshot(snapshot, answers, disclosure) -> {status, scales, trace}`:
  1. Validatsiya (xato bo'lsa `RESPONSE_NOT_VALIDATED`).
  2. Har bir item: `_map_score` → reverse scoring (`range` yoki `explicit_map`) →
     ixtiyoriy `item_transform_expr`.
  3. Har bir scale: `min_answered` / `max_missing` tekshiruvi (yetmasa
     `insufficient_data`) → `_aggregate` → ixtiyoriy `transform_expr` →
     theoretical min/max tekshiruvi (`SCORE_OUT_OF_RANGE`) → `_match_norm` → `_interpret`
     → `display_decimals` bo'yicha ROUND_HALF_UP.
  4. Trace qadamlari: `execution_gate`, `response_validation`, `missing_check`,
     `option_mapping`, `item_reverse`, `scale_aggregate`, `scale_transform`, `norm_match`,
     `interpretation_select`, `round_display`; `sequence` va `message_key` qo'shiladi.
  5. Status: `complete` yoki `complete_with_uninterpreted_scales`.
- `_map_score(item, value)` — option `score_value`, boolean `score_mapping.map`, son.
- `_aggregate(config, answered, codes, scores, scale)` — `sum`, `mean`, `sum_prorated`
  (`target_item_count`), `weighted_sum`.
- `_match_norm(norm, score)` — unrounded ball bo'yicha band; bir nechta mos kelsa `NORM_OVERLAP`.
- `_interpret(rules, scale, score, band, interpreter)` — `priority` bo'yicha birinchi mos
  qoida; kontekst: `transformed_score`, `norm_band_code`, `normalized_value`, `validity_status`.
- Disclosure: `summary_only` item qadamlarini yozmaydi; `full` bo'lmasa raw javob
  `inputs`ga kirmaydi (`redactions: ["raw_answer"]`).

### 6.6. `services/orchestration.py` — hisoblash orkestratsiyasi

Versiyalar: `ENGINE_VERSION="psychogram-scoring/1"`, `INTERPRETER_VERSION="json-ast/1"`,
`ROUNDING_VERSION="decimal-half-up/1"`.

`calculate(db, *, tenant, research, revision_id, idempotency_key, actor_id) -> Result`:
1. Tenant/research/revision/response scope tekshiruvi.
2. Pin hash == version `content_hash` (`METHODOLOGY_HASH_MISMATCH`).
3. `require_result_policy(...)` — joriy consent va licence. Idempotent qayta so'rovdan
   **oldin** bajariladi, shuning uchun bekor qilingan rozilik/litsenziya cache orqali chetlanmaydi.
4. `computation_key = hash(tenant, research, revision, answer_hash, methodology_hash,
   norm_selection, engine/interpreter/rounding versiyalari)`.
5. **Idempotency**: shu `idempotency_key` boshqa computation uchun ishlatilgan bo'lsa
   `IDEMPOTENCY_KEY_REUSED`; mavjud natija bo'lsa uni qaytaradi; tugamagan bo'lsa
   `CALCULATION_IN_PROGRESS`. Xuddi shu `computation_key` bo'yicha ham dedup.
   Gate'lar (yangi hisob uchun): research `active`, revision joriy va `validated`, version published.
6. `_effective_disclosure(licence)` → `full` / `derived_only` / `summary_only`.
7. `CalculationRun(status="running")` + audit `calculation.start`.
8. `score_snapshot(...)`.
9. **Optimistik qayta tekshiruv** persistdan oldin: `RESEARCH_CHANGED_DURING_RUN`,
   `CONSENT_CHANGED_DURING_RUN`, `LICENCE_CHANGED_DURING_RUN`.
10. `Result` (`result_hash`), `ScaleResult`lar, `ExplainabilityTrace` (`trace_hash`),
    `TraceStep`lar; response `scored`, run `succeeded`; audit `calculation.succeed`.

`require_result_policy(db, *, tenant, research, participant_id, methodology_version_id)
-> (ConsentRecord, LicenceRevision)` — `require_valid_consent` + `check_licence`; `calculate`,
`GET /results/{id}` va eksport umumiy ishlatadi.

`result_view(db, result) -> dict` — natija + scale'lar + trace qadamlari (API/export uchun), shuningdek
`participant_code`, `methodology_name`, `version_code` va `is_current`.

`is_current_result(db, result, response=None)` — natija revisioni hali response'ning joriy revisionimi.

`_effective_disclosure(licence)` — `summary_only` → `summary_only`; `derived_only` yoki
`allow_trace_item_values=false` → `derived_only`; aks holda `full`.

### 6.7. `services/imports.py` — CSV import

Konstantalar: `PII_HEADERS` (name, email, phone, passport, birth_date, ...),
`RESERVED` ustunlar (`_methodology_code`, `_version_code`, `_template_id`,
`participant_external_code`, `attempt_key`, `collected_at`), item ustunlari `item.<code>`.

`preview_csv(db, *, research, csv_text, actor_id, max_bytes, max_rows) -> (ImportJob, errors)`:
- Aktiv research, bayt/qator limiti (`FILE_TOO_LARGE` 413), strict CSV parse
  (`CSV_MALFORMED`), BOM tozalash, `DUPLICATE_HEADER`, `PII_COLUMN_FORBIDDEN`,
  `UNKNOWN_COLUMN`, `REQUIRED_COLUMN_MISSING`.
- Har bir qator: `TEMPLATE_MISMATCH`, `ROW_DUPLICATE` (fayl ichida va DBda),
  `PARTICIPANT_NOT_FOUND`, `CONSENT_NOT_VALID`, `_parse_cell` xatolari, `validate_answers`.
- Xatosiz qatorlar `staged_rows`ga; `preview_hash = hash(file_hash, research, staged, errors)`.
- `ImportJob(status="preview_ready")` + `ImportIssue`lar + audit.

`confirm_import(db, *, job, research, preview_hash, actor_id) -> ImportJob`:
- Scope, `preview_ready` holati, `preview_hash` mosligi (`IMPORT_PREVIEW_CHANGED`), aktiv research.
- Har bir staged qator → `create_response(..., finalize=True)`; muvaffaqiyat/rad
  `ImportRow` va `ImportIssue`ga yoziladi. Status `completed`, summary'ga
  `accepted_rows`, `commit_rejected_rows`.

Yordamchilar: `_parse_cell(item, cell)` (integer/decimal/`true|false`/option code),
`_issue(row, column, code, item_code=None)` — xavfsiz issue (qiymat `***` bilan yashiriladi).

### 6.8. `services/exports.py` — export

- `csv_safe(value)` — `= + - @ \t \r` bilan boshlansa `'` qo'shadi (formula injection himoyasi).
- `build_json_export(db, result, disclosure_level)` — `result_view` + `calculated_at`,
  `export_disclosure_level`, `disclaimer`, redakt qilingan trace.
- `build_research_csv(db, tenant, research) -> ResearchExport` — tadqiqot bo'yicha CSV: har
  respondentga bitta qator, faqat joriy revision natijasi; litsenziya yaroqsiz bo'lsa butunlay rad;
  roziligi yaroqsizlar chiqarilib sanaladi; BOM + CRLF; matn ustunlari `csv_safe`, ballar son.
- `build_csv_export(db, result, disclosure_level)` — meta qatorlar + scale jadvali
  (`uz-Latn` interpretatsiya, disclaimer har qatorda), CRLF.
- `redact_trace(trace, disclosure_level)` — `summary_only`: item qadamlari olib tashlanadi;
  `derived_only`: barcha `inputs` tozalanadi, `redactions`ga `raw_answer`, `prompt`, `label`.

### 6.9. `services/pii.py` — shifrlangan PII

- `_key(settings)` — kalit yo'q bo'lsa `PII_KEY_NOT_CONFIGURED` 503.
- `_aad(participant, key_version)` — `psychogram-pii|tenant|research|participant|key_version`.
- `upsert_pii(db, *, research, participant, fields, actor_id, settings)` — 12 baytli random
  nonce, AES-256-GCM, faqat ciphertext + metadata saqlanadi; audit `pii.create/update`
  (faqat maydon nomlari).
- `view_pii(...)` — `key_version` mos kelmasa `PII_KEY_VERSION_UNAVAILABLE`; deshifr
  xatosi `PII_DECRYPTION_FAILED`; audit `pii.view`.
- `delete_pii(...)` — aktiv `LegalHold` bo'lsa `PII_DELETE_LEGAL_HOLD` 409; audit `pii.delete`.
- `_require_identified_scope(research, participant)` — research `pii_mode="identified"` va
  participant shu research ichida bo'lishi shart.

Ruxsat etilgan PII maydonlari (`PIIWrite`): `full_name`, `email`, `phone`, `address`,
`national_id`, `date_of_birth` (1..12 maydon, har biri 1..1000 belgi).

## 7. Pydantic sxemalar

Hamma DTO'lar `APIModel` (`from_attributes=True`)dan meros oladi.

**`schemas/api.py` (write/command):** `BootstrapRequest`, `RegisterRequest`
(`organization_code` regex `^[a-z][a-z0-9_]{1,63}$`), `LoginRequest`, `TokenResponse`,
`MembershipView`, `MeResponse`, `OrganizationView`, `MemberCreate` (rol: admin/researcher/
operator/auditor), `MemberView`, `MethodologyCreate`, `MethodologyView`,
`MethodologyVersionCreate` (`version_code` semver), `MethodologyVersionView`,
`LicenceCreate`, `LicenceView`, `PublishRequest`, `RetentionPolicyCreate` (1..36500 kun),
`ResearchCreate`, `ResearchView` (+ `consent_reference`, `consent_version`), `ParticipantCreate`, `ParticipantView`, `ConsentCreate`,
`ConsentView`, `ResponseCreate`, `RevisionCreate` (`correction_reason` — ixtiyoriy,
`expected_lock_version`), `ValidationIssueView`, `RevisionView` (+ `validation_issues`), `ResponseView`, `CalculationRequest`
(`response_revision_id`, `idempotency_key`), `ScaleResultView`, `ResultView` (+ `participant_code`, `response_id`, `is_current`, `methodology_name`, `version_code`), `CloseResearchRequest`,
`CSVPreviewRequest`, `ImportPreviewView`, `ImportConfirmRequest`, `ImportConfirmView`.

**`schemas/read.py` (read-model):** `RetentionPolicyView`, `LicenceDetailView`,
`MethodologyVersionDetailView` (+ `methodology_code`, `methodology_name`), `MethodologyDetailView`, `ParticipantListItem`,
`ParticipantPage`, `ParticipantDetailView`, `ConsentHistoryItem`, `ConsentHistoryView`,
`RevisionDetailView` (+ `validation_issues`), `ResponseListItem` (+ `result_status`: not_calculated / calculated / recalculation_required, `current_result_id`), `ResponsePage`, `ResponseDetailView`,
`RevisionHistoryView`, `ResultSummaryView` (+ `is_current`), `ResultPage`, `PIIWrite`, `PIIView`.
Sahifalash: `offset ≥ 0`, `limit` 1..100 (default 50).

## 8. REST API (`/api/v1`)

Tenant endpointlari uchun headerlar: `Authorization: Bearer <token>` va
`X-Organization-ID: <uuid>`. Rollar: **O**=owner, **A**=admin, **R**=researcher,
**Op**=operator, **Au**=auditor, **PA**=platform admin.

### Auth — `routers/auth.py`
| Metod | Yo'l | Ruxsat | Servis |
|---|---|---|---|
| POST | `/auth/bootstrap` | token + flag | `bootstrap_user` |
| POST | `/auth/register` | ochiq, faqat `registration_enabled=true` | `register_owner`; aks holda `REGISTRATION_DISABLED` 404 |
| POST | `/auth/login` | ochiq | `authenticate` |
| GET | `/auth/me` | token | membershiplar ro'yxati |

### Write — `routers/v1.py`
| Metod | Yo'l | Ruxsat | Servis |
|---|---|---|---|
| POST | `/organizations` | PA | `register_owner(actor_id=admin)` — tashkilot + owner |
| GET | `/organizations/current` | har qanday member | — |
| GET / POST | `/organizations/current/members` | O, A | `add_member` |
| POST | `/retention-policies` | O, A | to'g'ridan-to'g'ri ORM; takroriy kod → `RETENTION_POLICY_CODE_EXISTS` 409 |
| GET | `/methodologies` | token | — |
| POST | `/methodologies` | PA | `create_methodology` |
| POST | `/methodologies/{id}/versions` | PA | `create_version` |
| POST | `/methodology-versions/{id}/licences` | PA | `create_licence` |
| POST | `/methodology-versions/{id}/publish` | PA | `publish_version` |
| GET | `/researches` | member | — |
| POST | `/researches` | O, A, R | `create_research` |
| POST | `/researches/{id}/activate` | O, A, R | `activate_research` |
| POST | `/researches/{id}/close` | O, A, R | `close_research`; hisoblanmagan javoblar bo'lsa `confirm_uncalculated` talab qilinadi |
| POST | `/researches/{id}/participants` | O, A, R, Op | `create_participant` |
| POST | `/participants/{id}/consents` | O, A, R, Op | `record_consent` |
| POST | `/researches/{id}/responses` | O, A, R, Op | `create_response` |
| POST | `/responses/{id}/revisions` | O, A, R, Op | `revise_response` |
| POST | `/responses/{id}/validate` | O, A, R, Op | `validate_revision` |
| POST | `/researches/{id}/calculations` | O, A, R | `calculate` |
| GET | `/results/{id}` | O, A, R, Au | `require_result_policy` + `result_view` |
| POST | `/researches/{id}/imports/preview` | O, A, R, Op + `require_csv_import` | `preview_csv` |
| POST | `/researches/{id}/imports/{import_id}/confirm` | O, A, R, Op | `confirm_import` |
| GET | `/audit-events` | O, A, Au | oxirgi 200 ta |

### Read / export / PII — `routers/read.py`
| Metod | Yo'l | Ruxsat | Izoh |
|---|---|---|---|
| GET | `/retention-policies` | member | |
| GET | `/methodologies/{id}` | token (+tenant) | PA to'liq, tenant faqat eligible published |
| GET | `/methodologies/{id}/versions` | token (+tenant) | |
| GET | `/methodology-versions/eligible?use_type=` | member | licence tenantga mos versiyalar |
| GET | `/methodology-versions/{id}` | token | `use_type` yoki `research_id` konteksti; snapshot redaksiyasi |
| GET | `/methodology-versions/{id}/licences` | token | licence tarixi |
| GET | `/methodology-versions/{id}/licences/current` | token | |
| GET | `/researches/{id}/participants?query=&offset=&limit=` | member | consent holati, `has_pii` |
| GET | `/researches/{id}/participants/{pid}` | member | |
| GET | `/researches/{id}/participants/{pid}/consents` | member | joriy + tarix |
| GET | `/researches/{id}/responses` | member | sahifalangan |
| GET | `/responses/{id}` | member | raw `answers` faqat O/A/R/Op uchun |
| GET | `/responses/{id}/revisions` | member | |
| GET | `/responses/{id}/revisions/{rid}` | member | |
| GET | `/results?research_id=&participant_id=&response_revision_id=` | O, A, R, Au | sahifalangan |
| GET | `/researches/{id}/export?format=csv` | O, A, R | `build_research_csv`; `X-Export-Rows`, `X-Export-Not-Calculated`, `X-Export-Excluded-Consent` |
| GET | `/results/{id}/export?format=json\|csv` | O, A, R | consent + licence qayta tekshiriladi; `xlsx/pdf` → 415 |
| PUT / GET / DELETE | `/researches/{id}/participants/{pid}/pii` | `pii_access` | AES-GCM, audit |

Snapshot redaksiyasi (`_redact_snapshot`): `summary_only` yoki licence yo'q → `null`;
aks holda faqat item kodi/turi/cheklovlari va scale meta; `allow_item_display=true`
bo'lsa prompt va option label'lar ham.

Read router yordamchilari: `_catalog_tenant`, `_visible_versions`, `_version_detail`,
`_licence_detail`, `_redact_snapshot`, `_is_eligible`, `_research`, `_participant`,
`_participant_item`, `_response`, `_response_item`, `_revision_detail`, `_result_summary`.

## 9. Holat mashinalari

```
MethodologyVersion:  draft ─► in_review ─► published ─► deprecated / withdrawn
                     (published dan keyin snapshot immutable)

Research:            ready ──activate──► active ──close──► closed
                     (create'da darhol "ready"; pin active/closed'da o'zgarmaydi;
                      closed: yangi respondent, javob, tahrir, validate, hisoblash va
                      rozilik berish bloklanadi; o'qish, eksport va rozilikni qaytarib
                      olish ochiq; qayta ochilmaydi)

Response/Revision:   draft ──validate──► validated ──calculate──► (response) scored
                          └──────────► validation_failed
                     yangi revision → response yana draft, lock_version+1
                     (validated'dan keyingi revision uchun correction_reason shart)
                     ro'yxatda natija holati: not_calculated → calculated → recalculation_required

ImportJob:           preview_ready ──confirm──► committing ──► completed

CalculationRun:      running ──► succeeded
```

## 10. Xavfsizlik modeli (qisqa)

- **Autentifikatsiya**: Argon2 hash, 60 daqiqalik HS256 JWT, generic login xatosi.
- **Avtorizatsiya**: platform admin (global registr) va tenant rollari alohida;
  platform admin tenant PII/response'ga avtomatik kira olmaydi.
- **Tenant izolyatsiyasi**: har bir query `tenant_id` bilan; boshqa tenant obyekti 404.
- **PII**: faqat `identified` research, AES-256-GCM + AAD, alohida endpointlar,
  har bir ko'rish audit qilinadi, legal hold o'chirishni bloklaydi.
- **Kirish chegaralari**: CSV bayt/qator limitlari, middleware body limit, UTF-8 majburiy.
- **Formula xavfsizligi**: faqat JSON-AST whitelist, resurs limitlari.
- **HTTP headerlar**: CSP, nosniff, no-referrer, frame deny, sezgir javoblarda no-store.
- **MVPdan tashqarida (production gate)**: rate limiting, MFA/step-up, reverse proxy body
  limit, HTTPS/HSTS, XLSX/PDF export, background queue, retention worker, key rotation.

## 11. Frontend arxitekturasi (`frontend/`)

```
main.tsx ─► BrowserRouter ─► App
App: ErrorBoundary ─► QueryClientProvider ─► AuthProvider ─► Routes
      /login, /register (faqat VITE_ENABLE_REGISTRATION), /setup/bootstrap (faqat DEV + VITE_ENABLE_BOOTSTRAP)
      Protected ─► AppShell (rail + topbar + mobile nav) ─► sahifalar
```

**Qatlamlar**
- `lib/api.ts` — `api<T>(path, {token, organizationId, bodyJson})`: Bearer va
  `X-Organization-ID` qo'shadi, `referrerPolicy: no-referrer`, xatolarni `ApiError(status,
  code, message, details)`ga aylantiradi; `download(...)` — blob orqali fayl;
  `safeMessage(error)`. Base URL — `VITE_API_ORIGIN`.
- `context/AuthContext.tsx` — `AuthProvider` (token va tanlangan tenant `sessionStorage`da),
  `useAuth()` (`token`, `me`, `membership`, `setSession`, `selectTenant`, `logout`,
  `expireSession`), `useApi()` — token va tenant'ni avtomatik qo'shadi; autentifikatsiyali
  so'rov 401 qaytarsa sessiyani tugatadi va login sahifasi "Sessiya tugadi" xabarini ko'rsatadi.
- `lib/queryClient.ts` — ilova bo'ylab yagona `QueryClient` (testlarda har testdan keyin tozalanadi).
- `lib/capabilities.ts` — `Capability` turlari va rol siyosati; `can(role, capability)`,
  `canAccessPii(membership)`.
- `lib/features.ts` — `bootstrapEnabled()`, `registrationEnabled()` (`VITE_ENABLE_REGISTRATION`),
  `csvImportEnabled()` (`VITE_ENABLE_CSV_IMPORT`), `maxCsvBytes()`. Ikkala yangi flag default `false`.
- `lib/queryKeys.ts` — `tenantKey(orgId, ...parts)` — cache tenant bo'yicha ajratiladi;
  tenant almashganda `queryClient.clear()`.
- `components/` — `AppShell`, `RequireCapability`, `ErrorBoundary` (raw xatoni
  ko'rsatmaydi), `RemoteIcon` (Iconify lucide, fallback harf), `UI.tsx` (`Button`,
  `Status`, `human`, `Notice`, `ErrorSummary`, `ErrorNotice`, `LiveStatus`, `Empty`, `Page`,
  `Loading`, `Drawer`, `ConfirmAction`, `Field`, `Pagination`).
- `types.ts` — backend read-model'lariga mos TS interfeyslar.

**Sahifalar va marshrutlar**

| Fayl | Komponentlar | Marshrut |
|---|---|---|
| `AuthPages.tsx` | `LoginPage`, `RegisterPage`, `BootstrapPage` | `/login`, `/register`, `/setup/bootstrap` |
| `ResearchPages.tsx` | `ResearchList`, `ResearchCreate`, `ResearchLayout`, `ResearchOverview` | `/researches`, `/researches/new`, `/researches/:id` |
| `ParticipantPages.tsx` | `ParticipantsPage`, `ParticipantDetail` (consent, PII) | `/researches/:id/participants[/:pid]` |
| `ResponsePages.tsx` | `ResponsesPage` (javob va natija holati), `ResponseDetailPage` (revision tafsilotlari) | `/researches/:id/responses`, `/responses/:id` |
| `ResponseForm.tsx` | `ResponseForm` — respondent kodi, rozilik, savollar, qoralama, tekshirish va hisoblash | `/researches/:id/responses/new`, `/researches/:id/responses/:responseId` (bitta marshrut) |
| `ResultImportPages.tsx` | `ImportPage`, `ResultsPage`, `ResultDetail` (export) | `/researches/:id/import`, `/results[/:id]` |
| `AdminPages.tsx` | `TeamPage`, `RetentionPage`, `AuditPage`, `MethodologiesPage`, `MethodologyDetail`, `RegistryPage` | `/team`, `/retention`, `/audit`, `/methodologies[/:id]`, `/registry` |

**Pilot menyusi:** asosiy menyuda faqat Tadqiqotlar va Metodikalar (owner/admin/auditor uchun
rol bo'yicha Jamoa, Retention, Audit; platform admin uchun Registry). Natijalar tadqiqot ichida.
"Yangi tadqiqot" formasi `use_type=research` va `pii_mode=pseudonymous`ni o'zi qo'yadi, metodikani
nomi bilan ko'rsatadi, yagona retention siyosatini avtomatik qo'llaydi va "Yaratish va boshlash"
bilan create + activate'ni ketma-ket bajaradi; aktivlash xato bersa shu tadqiqotda
"Tadqiqotni boshlash" tugmasi qoladi (`draft` va `ready` holatlari uchun).

**Javob formasi (`ResponseForm`).** "Natijani hisoblash" ketma-ket: respondentni yaratadi
(`PARTICIPANT_CODE_EXISTS` bo'lsa kod bo'yicha topib qayta ishlatadi, javobi bor bo'lsa rad etadi)
→ rozilik belgisi qo'yilgan bo'lsagina `granted` consent yozadi → response'ni `finalize:false`
bilan yaratadi yoki o'zgargan javoblar bo'lsa revision qo'shadi (`RESPONSE_ATTEMPT_EXISTS` bo'lsa
mavjudini oladi) → validate (xatolar `validation_issues` orqali savol yonida) → calculate
(`idempotency_key = calc-<revision id>`) → natija sahifasi. "Qoralamani saqlash" validatsiyadan
oldin to'xtaydi; "Saqlandi" faqat server javobidan keyin. Operator "Tekshirish" tugmasini ko'radi.

**Frontend capability siyosati**

| Capability | Rollar |
|---|---|
| `research:create`, `research:activate`, `research:close`, `result:calculate` | owner, admin, researcher |
| `participant:write`, `response:write` | owner, admin, researcher, operator |
| `result:read` | owner, admin, researcher, auditor |
| `result:export` | owner, admin, researcher |
| `team:manage`, `retention:manage` | owner, admin |
| `audit:read` | owner, admin, auditor |

> Siyosat backend bilan mos: auditor natijani ko'radi, lekin eksport qila olmaydi
> (`test_auditor_and_operator_cannot_export_results`).

Dev server: Vite `:5173`, `/api` va `/health` → `http://127.0.0.1:8000` proxy.

## 12. Testlar

| Fayl | Qamrov |
|---|---|
| `tests/test_api.py` (20) | bootstrap, generic login, scoring + disclaimer + idempotency, RBAC va cross-tenant, consent/pin gate'lar, revision immutability, revoked licence, cache/natija o'qishda consent va licence gate'i, takroriy participant/retention kodi 409, har bir savol bo'yicha validatsiya xatolari, tuzatish sababi qoidasi, ro'yxatdagi natija holati, summary_only redaksiya, CSV + PII |
| `tests/test_scoring.py` (11) | kontrakt vektorlari, insufficient data, validatsiya kodlari, norm chegaralari, half-up, AST xavfsizligi va limitlari, division by zero, norm overlap |
| `tests/test_security_release.py` (7) | bootstrap gate, export RBAC, security headerlar, CSV encoding/hajm, version detail kontekst, yopiq registratsiya + admin tashkilot yaratishi, CSV import flag'i |
| `tests/test_ux_backend_gaps.py` (9) | read-model'lar, pagination, JSON/CSV export, formula-safe CSV, PII AES-GCM, fail-closed, legal hold |
| `tests/test_config.py` (6) | production secret, bootstrap token validatsiyasi, registratsiya default o'chiq |
| `tests/test_migrations.py` (2) | toza `upgrade head` va 0001→0002 |
| `tests/test_research_close.py` (4) | yopish, hisoblanmagan javoblar soni va tasdiq, yopilgandan keyingi bloklar, rol |
| `tests/test_research_export.py` (6) | qator tarkibi va hisobotlar, eskirgan natija chiqmasligi, formula himoyasi, 105 respondent, litsenziya, rol va tenant |
| `frontend/src/**/*.test.ts(x)` (54) | api client, capability siyosati, UI, Drawer, ErrorBoundary, pilot menyusi va flag'lar, tadqiqotni yaratish va boshlash, sessiya tugashi, javob formasi (rozilik, qoralama, savol yonidagi xatolar, dublikatsiz qayta urinish, tuzatish sababi), javoblar ro'yxati, tadqiqotni yakunlash, CSV yuklash, eskirgan natija belgisi, flows, import safety |

Ishga tushirish: `pytest -q`; frontend — `npm run typecheck && npm run lint && npm run test && npm run build`.

## 13. Xato kodlari ma'lumotnomasi

| Guruh | Kodlar |
|---|---|
| Auth | `REGISTRATION_DISABLED`, `AUTH_REQUIRED`, `AUTH_TOKEN_INVALID`, `AUTH_CREDENTIALS_INVALID`, `PASSWORD_TOO_WEAK`, `BOOTSTRAP_DISABLED`, `BOOTSTRAP_TOKEN_INVALID`, `BOOTSTRAP_ALREADY_COMPLETED`, `EMAIL_ALREADY_REGISTERED` |
| Tenant / RBAC | `TENANT_ACCESS_DENIED`, `ROLE_FORBIDDEN`, `ORGANIZATION_CODE_EXISTS`, `ORGANIZATION_CONTEXT_REQUIRED`, `MEMBERSHIP_EXISTS` |
| Registr | `METHODOLOGY_CODE_EXISTS`, `METHODOLOGY_NOT_FOUND`, `METHODOLOGY_VERSION_EXISTS`, `METHODOLOGY_VERSION_NOT_FOUND`, `METHODOLOGY_SCHEMA_INVALID`, `METHODOLOGY_NOT_PUBLISHED`, `VERSION_STATE_INVALID`, `LICENCE_METADATA_REQUIRED`, `LICENCE_NOT_VALID`, `LICENCE_NOT_FOUND`, `NORM_OVERLAP` |
| Research | `RESEARCH_NOT_FOUND`, `RESEARCH_STATE_INVALID`, `RESEARCH_HAS_UNCALCULATED_RESPONSES`, `RESEARCH_NOT_ACTIVE`, `RETENTION_POLICY_NOT_FOUND`, `RETENTION_POLICY_CODE_EXISTS`, `NORM_PIN_INVALID`, `RESEARCH_METHODOLOGY_MISMATCH`, `RESEARCH_USE_TYPE_INVALID` |
| Yig'ish | `CORRECTION_REASON_REQUIRED`, `PARTICIPANT_NOT_FOUND`, `CONSENT_BASIS_REQUIRED`, `CONSENT_NOT_VALID`, `RESPONSE_NOT_FOUND`, `RESPONSE_ATTEMPT_EXISTS`, `PARTICIPANT_CODE_EXISTS`, `REVISION_CONFLICT`, `REVISION_NOT_FOUND`, `REVISION_NOT_CURRENT` |
| Validatsiya | `UNKNOWN_ITEM`, `ITEM_REQUIRED`, `TYPE_INVALID`, `BOOLEAN_LITERAL_INVALID`, `OPTION_NOT_ALLOWED`, `VALUE_OUT_OF_RANGE`, `STEP_INVALID` |
| Scoring | `RESPONSE_NOT_VALIDATED`, `METHODOLOGY_HASH_MISMATCH`, `IDEMPOTENCY_KEY_REUSED`, `CALCULATION_IN_PROGRESS`, `RESEARCH_CHANGED_DURING_RUN`, `CONSENT_CHANGED_DURING_RUN`, `LICENCE_CHANGED_DURING_RUN`, `MAPPING_NOT_FOUND`, `SCORE_OUT_OF_RANGE`, `RULE_SCHEMA_INVALID`, `RULE_LIMIT_EXCEEDED`, `DIVISION_BY_ZERO`, `RESULT_NOT_FOUND` |
| Import | `CSV_IMPORT_DISABLED`, `REQUEST_BODY_TOO_LARGE`, `ENCODING_INVALID`, `FILE_TOO_LARGE`, `CSV_MALFORMED`, `DUPLICATE_HEADER`, `PII_COLUMN_FORBIDDEN`, `UNKNOWN_COLUMN`, `REQUIRED_COLUMN_MISSING`, `TEMPLATE_MISMATCH`, `ROW_DUPLICATE`, `IMPORT_NOT_FOUND`, `IMPORT_STATE_INVALID`, `IMPORT_PREVIEW_CHANGED` |
| Export | `EXPORT_FORMAT_UNSUPPORTED` |
| PII | `PII_STORAGE_NOT_CONFIGURED`, `PII_KEY_NOT_CONFIGURED`, `PII_KEY_VERSION_UNAVAILABLE`, `PII_DECRYPTION_FAILED`, `PII_NOT_FOUND`, `PII_MODE_NOT_IDENTIFIED`, `PII_ROLE_FORBIDDEN`, `PII_PERMISSION_REQUIRED`, `PII_DELETE_LEGAL_HOLD` |

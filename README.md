# Psychogram MVP backend

FastAPI va SQLAlchemy 2.x asosidagi multi-tenant MVP backend. U metodika versiyasi va litsenziyasini boshqaradi, research'ni aniq snapshot'ga pin qiladi, participant consent'ini tekshiradi, immutable response revisionlardan deterministik natija hisoblaydi va CSV importni preview/confirm oqimi orqali qabul qiladi.

Har bir natijada **“Bu natija tibbiy tashxis emas.”** disclaimer'i mavjud. `synth_balance_demo` faqat `tests/` fixture'idir; production seed yaratilmaydi.

## Muhitni tayyorlash

Python 3.14 bilan tekshirilgan:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

`.env` ichida kamida `PSYCHOGRAM_JWT_SECRET`ni uzun, tasodifiy qiymatga almashtiring. Production uchun:

```dotenv
PSYCHOGRAM_ENVIRONMENT=production
PSYCHOGRAM_DATABASE_URL=postgresql+psycopg2://user:password@db-host/psychogram
PSYCHOGRAM_JWT_SECRET=replace-with-a-random-secret-at-least-32-characters-long
PSYCHOGRAM_BOOTSTRAP_ENABLED=false
PSYCHOGRAM_BOOTSTRAP_TOKEN=replace-with-a-random-secret-at-least-32-characters-long
PSYCHOGRAM_PII_ENCRYPTION_KEY=replace-with-base64-encoded-32-random-bytes
PSYCHOGRAM_PII_KEY_VERSION=v1
PSYCHOGRAM_CORS_ORIGINS=https://app.example.org
PSYCHOGRAM_MAX_REQUEST_BODY_BYTES=3100000
```

`PSYCHOGRAM_PII_ENCRYPTION_KEY` aniq 32 baytli tasodifiy kalitning Base64
ko'rinishi bo'lishi shart. PII endpointlari kalit berilmasa yoki saqlangan
`key_version` joriy konfiguratsiyaga mos kelmasa fail-closed ishlaydi. Kalitni
repository yoki loglarga yozmang; secret manager orqali bering. Bu MVP bir vaqtda
faqat bitta faol key versionni qo'llaydi, shuning uchun rotation oldidan mavjud
yozuvlarni alohida re-encryption jarayoni bilan yangilash kerak.

Konfiguratsiya ataylab `PSYCHOGRAM_` prefiksidan foydalanadi; bu host tizimidagi umumiy `DEBUG`, `DATABASE_URL` kabi o'zgaruvchilar bilan to'qnashuvni oldini oladi. Lokal default SQLite, schema auto-create esa o'chirilgan: schema migration orqali boshqariladi.

## Migration, ishga tushirish va test

```powershell
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\uvicorn.exe src.main:app --reload
.\.venv\Scripts\python.exe -m pytest -q
```

- Health: `GET http://127.0.0.1:8000/health`
- OpenAPI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

PostgreSQL ham shu migration va model metadata bilan ishlaydi. Production DB useriga faqat zarur schema huquqlarini bering; audit/result/revision jadvallariga to'g'ridan-to'g'ri application tashqarisidan yozishni cheklash tavsiya etiladi.

## Birinchi bootstrap oqimi

Bootstrap default holatda, jumladan productionda, **o'chiq**. Deployment operatori
bo'sh DB uchun kamida 32 belgili tasodifiy tokenni secret managerga qo'yib,
`PSYCHOGRAM_BOOTSTRAP_ENABLED=true`ni faqat bootstrap oynasi davomida yoqadi.

1. Bo'sh DBda faqat bir marta `POST /api/v1/auth/bootstrap` chaqiring. Requestdagi `bootstrap_token` configured token bilan constant-time tekshiriladi.
2. Birinchi admin yaratilishi bilan `PSYCHOGRAM_BOOTSTRAP_ENABLED=false` qilib API processlarini qayta ishga tushiring. Enabled bootstrap’ni doimiy production konfiguratsiyasi sifatida qoldirmang.
3. Platform administrator `POST /api/v1/organizations` orqali tashkilot va uning owner hisobini yaratadi (body `/auth/register` bilan bir xil). Ochiq `POST /api/v1/auth/register` default holatda o'chiq (`PSYCHOGRAM_REGISTRATION_ENABLED=false`) va `404 REGISTRATION_DISABLED` qaytaradi.
4. `POST /api/v1/auth/login` access token qaytaradi; `GET /api/v1/auth/me` membership va organization IDlarni beradi.
5. Tenant endpointlarida ikkita header majburiy:

```http
Authorization: Bearer <access-token>
X-Organization-ID: <organization-uuid>
```

Platform administrator methodology draft/version/licence yaratib versiyani publish qiladi. Organization owner/admin retention policy yaratadi; researcher published+licensed versiondan research yaratib activate qiladi.

## Barqaror `/api/v1` endpointlari

- Auth: `/auth/bootstrap`, `/auth/register`, `/auth/login`, `/auth/me`
- Organization: `/organizations` (POST, platform admin), `/organizations/current`, `/organizations/current/members`
- Registry: `/methodologies`, `/methodologies/{id}`, `/methodologies/{id}/versions`, `/methodology-versions/eligible`, `/methodology-versions/{id}`, `/methodology-versions/{id}/licences`, `/methodology-versions/{id}/licences/current`, `/methodology-versions/{id}/publish`. Version detail tenant callida validated `use_type=research|education|clinical` yoki pinned `research_id` berilishi mumkin; pinned context serverdagi research `use_type`ini authoritative ishlatadi.
- Research: `/retention-policies`, `/researches`, `/researches/{id}/activate`
- Collection: `/researches/{id}/participants`, `/researches/{id}/participants/{participant_id}`, `/researches/{id}/participants/{participant_id}/consents`, `/participants/{id}/consents`, `/researches/{id}/responses`, `/responses/{id}`, `/responses/{id}/revisions`, `/responses/{id}/revisions/{revision_id}`, `/responses/{id}/validate`
- PII: `PUT|GET|DELETE /researches/{id}/participants/{participant_id}/pii`
- Scoring: `/researches/{id}/calculations`, `/results`, `/results/{id}`
- Export: `/results/{id}/export?format=json|csv` (`xlsx` va `pdf` hozir `415 EXPORT_FORMAT_UNSUPPORTED` qaytaradi)
- CSV: `/researches/{id}/imports/preview`, `/researches/{id}/imports/{import_id}/confirm` — default o'chiq (`PSYCHOGRAM_CSV_IMPORT_ENABLED=false`, `404 CSV_IMPORT_DISABLED`); pilotning birinchi relizida import yo'q
- Audit: `/audit-events`

Xatolar barqaror shaklda qaytadi:

```json
{"error": {"code": "CONSENT_NOT_VALID", "message": "Participant consent is not valid"}}
```

## Xavfsizlik va MVP chegaralari

- Passwordlar Argon2 bilan hash qilinadi; access tokenlar signed JWT.
- API process ataylab memory-only rate limiter yoki soxta MFA bermaydi. **Production
  release gate:** reverse proxy/IdP login uchun IP + account rate limiting,
  credential-stuffing monitoring va owner/admin/PII vakolatlari uchun MFA yoki
  PII reveal/exportda step-up authenticationni ta'minlashi shart. Login xatosi
  akkaunt mavjudligini oshkor qilmaydigan generic envelope bo'lib qoladi.
- CORS wildcard ishlatmaydi va explicit allowlist talab qiladi.
- API response'lari `nosniff`, `no-referrer`, frame deny va API-safe CSP oladi;
  PII/result/calculation/export response'lari `Cache-Control: no-store, private`
  va `Pragma: no-cache` oladi. HTTPS/HSTS reverse proxyda majburiy.
- Tenant querylari organization scope bilan bajariladi; platform admin tenant PII/response'ga avtomatik kira olmaydi.
- Audit metadata raw answer yoki PII qiymatlarini saqlamaydi. PII AES-256-GCM bilan random nonce va tenant/research/participant/key-version AAD orqali shifrlanadi; DBda faqat ciphertext, envelope metadata va maydon nomlari saqlanadi. Faqat `can_view_pii` huquqli owner/admin/researcher kira oladi; legal hold PII o'chirishni bloklaydi.
- Published methodology, validated revision, result, trace va audit normal ORM write pathda immutable.
- CSV endpoint canonical UTF-8 textni JSON `csv_text` maydonida oladi. API
  declared non-UTF-8 charset va katta `Content-Length`ni body parse'dan oldin
  rad etadi, service esa decoded CSV byte/qator limitini qayta tekshiradi.
  Chunked request va JSON parserdan oldingi qat'iy limitni faqat application
  processga yuklamang: **production release gate** sifatida reverse proxyda
  `PSYCHOGRAM_MAX_REQUEST_BODY_BYTES`dan katta requestlarni buffer qilmasdan
  `413` bilan rad eting. Result export JSON yoki UTF-8 CSV attachment qaytaradi,
  majburiy disclaimerni saqlaydi va spreadsheet formula injectiondan himoyalaydi.
  XLSX/PDF export, background queue, object storage, break-glass PII access va
  retention worker MVPdan tashqarida.
- Formula evaluator faqat typed JSON AST whitelistidan foydalanadi; `eval`, `exec`, dynamic import, DB/network/clock reference yo'q.

## Frontend

```powershell
Set-Location frontend
Copy-Item .env.example .env
npm.cmd install
npm.cmd run dev
```

Frontend verification: `npm.cmd run typecheck`, `npm.cmd run lint`, `npm.cmd run test`, `npm.cmd run build`. Deployment va CSP talablari `frontend/README.md`da.

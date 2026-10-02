# Frontend/backend contract, security va privacy QA

**Sana:** 2026-07-16  
**Scope:** React SPA ↔ FastAPI OpenAPI kontrakti, RBAC/tenant isolation, auth/session, CSV import/export, licence/disclaimer, PII AES-GCM lifecycle, CORS/CSP/Iconify va dependency holati.  
**Chegara:** audit read-only bajarildi; production kod o‘zgartirilmadi. Dinamik tekshiruvlar lokal `TestClient`, Vitest va build orqali bajarildi; haqiqiy reverse proxy/HTTPS deployment headerlari bu workspace ichida mavjud emas.

## 1. Yakuniy baho

**Release holati: BLOCKED.** Bir critical va bir high finding tuzatilmasdan internetga ochiq production release tavsiya etilmaydi.

| Severity | Soni | Release ta’siri |
|---|---:|---|
| Critical | 1 | Bo‘sh instance to‘liq egallanishi mumkin |
| High | 1 | Auditorga taqiqlangan natija eksporti ochiq |
| Medium | 10 | Privacy, tenant cache, RBAC UX, auth, import va contract failurelar |
| Low | 2 | Audit timestamp va export error diagnostikasi |

Eng muhim ijobiy holat: backend tenant scopingni har tenant endpointida server tomonda tekshiradi; platform administrator tenant membershipisiz participant/response/PII ma’lumotiga kira olmaydi. PII AES-256-GCM + AAD bilan shifrlanadi, reveal/delete audit qilinadi va legal hold delete’ni bloklaydi.

## 2. Findinglar

### F-01 — Production bootstrap token majburiy emas

**Severity: Critical**

- **Scenario:** yangi production DB internetga ochilganda birinchi tashqi foydalanuvchi `POST /api/v1/auth/bootstrap`ga token bermasdan murojaat qilib `is_platform_admin=True` akkaunt oladi. Natijada global metodika registry va publish pipeline egallanadi.
- **Evidence:** `bootstrap_token` default `None`; production validator faqat JWT secretni majburiy qiladi (`src/core/config.py:29-30`, `src/core/config.py:44-57`). Token faqat konfiguratsiyada mavjud bo‘lsa tekshiriladi (`src/services/domain.py:50-66`). Mavjud test tokensiz bootstrap `201` va platform admin tokenini tasdiqlaydi (`tests/test_api.py:34-55`; fixture `tests/conftest.py:145-151`). UI login bootstrap route’ni reklama qiladi va token maydonini optional qoldiradi (`frontend/src/pages/AuthPages.tsx:12`, `frontend/src/pages/AuthPages.tsx:19-22`), bu `docs/03_ux_design_spec.md:110` bilan ham zid.
- **Reproduction:** bo‘sh DB + explicit production JWT secret + `bootstrap_token=None`; tokensiz yuqoridagi endpointga valid email/12+ belgili parol yuborish → `201` bearer token → `/auth/me.is_platform_admin=true`.
- **Minimal fix:** production validator `BOOTSTRAP_TOKEN`ni kamida 32 random byte sifatida majburiy qilsin yoki bootstrap endpointni default disabled qilib, faqat CLI/one-time deployment flag orqali vaqtincha yoqsin. Login sahifasidan linkni olib tashlang; muvaffaqiyatdan keyin bootstrap capability’ni yopish deployment gate bo‘lsin.

### F-02 — Auditor natijani eksport qila oladi

**Severity: High**

- **Scenario:** product scope auditorni “eksport qilmaydi” deb belgilagan bo‘lsa-da, auditor barcha pseudonim result va trace’ni JSON/CSV qilib tashqariga olib chiqishi mumkin.
- **Evidence:** scope auditor eksportini taqiqlaydi (`docs/01_product_scope.md:89`). Backend `GET /api/v1/results/{result_id}/export` uchun auditorni allowlistga qo‘shgan (`src/api/routers/read.py:489-498`). Frontend Result Detail eksport tugmalarini roldan qat’i nazar chiqaradi (`frontend/src/pages/ResultImportPages.tsx:25-26`).
- **Reproduction:** auditor membership token + tenant header bilan result export endpointiga `?format=json` yuborish; server role dependency bo‘yicha ruxsat beradi.
- **Minimal fix:** backend eksport allowlistini `owner/admin/researcher`ga qisqartiring (yoki alohida `can_export_results` permission kiriting); UI tugmalarini ayni permission bilan guard qiling va auditor deny testini qo‘shing.

### F-03 — Tenant switch in-flight cache race

**Severity: Medium**

- **Scenario:** tenant A so‘rovi davom etayotgan paytda tenant B tanlansa, `queryClient.clear()`dan keyin A request yakunlanib tenant-independent key (`['members']`, `['retention']`, `['audit']`, `['participant', id]`, `['response', id]`, `['methodologies']`) bilan cache’ni qayta to‘ldirishi mumkin. B tenant sahifasida A ma’lumoti vaqtincha ko‘rinishi yoki stale response ishlatilishi mumkin.
- **Evidence:** switch avval synchronous `queryClient.clear()`, keyin tenant update qiladi, lekin querylarni cancel/await qilmaydi (`frontend/src/components/AppShell.tsx:16-24`). Ko‘p query keylarda organization ID yo‘q (`frontend/src/pages/AdminPages.tsx:13,19,24,28,33`; `frontend/src/pages/ParticipantPages.tsx:25-26`; `frontend/src/pages/ResponsePages.tsx:27`). Backend yuborilgan eski header bilan A response’ni qonuniy qaytaradi; frontend race’ni o‘zi to‘sishi kerak.
- **Minimal fix:** tenantni almashtirishdan oldin `await queryClient.cancelQueries()`, so‘ng `queryClient.clear()`; barcha tenant query keylariga `organization_id`ni qo‘shing. Switchni async transaction qiling va oldingi tenant PII/local state unmount bo‘lishini test qiling.

### F-04 — Route/action role guardlari to‘liq emas

**Severity: Medium**

- **Scenario:** auditor “participant qo‘shish”, consent yozish, activate, manual response/import kabi mutate UIlarini ko‘radi; operator Results/Team mobil linklarini ko‘radi. Backend 403 bilan xavfsiz bloklaydi, ammo bu phantom action va noto‘g‘ri authorization UX yaratadi.
- **Evidence:** barcha protected routelar faqat token bilan guard qilingan (`frontend/src/App.tsx:16-25`); research ichidagi tablar role-filter qilinmagan (`frontend/src/pages/ResearchPages.tsx:21-27`); participant create/consent form hamma tenant memberga ko‘rinadi (`frontend/src/pages/ParticipantPages.tsx:13-18,21-32`); mobile Team/Results linklari role-filter qilinmagan (`frontend/src/components/AppShell.tsx:27`). Backend mutatsiyalarni role dependency bilan to‘g‘ri bloklaydi (`src/api/routers/v1.py:257-263,284-290,300-310,323-334,352-363,460-471`).
- **Minimal fix:** markaziy route capability map yarating; menu, route va CTA ayni capability’dan foydalansin. Backend guard authoritative qolishi shart. Auditor/operator UI testlarini qo‘shing.

### F-05 — PII plaintext response uchun `no-store` yo‘q

**Severity: Medium**

- **Scenario:** PII `GET/PUT` plaintext JSON response browser private cache, service worker yoki intermediateda saqlanishi mumkin; DOM/state reveal sahifa tark etilguncha ochiq turadi. Frontend local state/query cachega PII yozmaydi, ammo HTTP cache policy defense-in-depth yo‘q.
- **Evidence:** PII GET/PUT `PIIView(fields=...)` qaytaradi, custom cache headers yo‘q (`src/api/routers/read.py:566-629`). Frontend reveal natijasini component state va input `defaultValue`lariga qo‘yadi (`frontend/src/pages/ParticipantPages.tsx:23-32`). Tenant switch reveal markerini o‘chiradi (`frontend/src/context/AuthContext.tsx:17`), lekin marker real PII state manbasi emas.
- **Minimal fix:** PII GET/PUT va sensitive result/export javoblariga `Cache-Control: no-store, private`, `Pragma: no-cache` qo‘shing; reveal uchun explicit “Yopish” action, blur/unmount cleanup va browser-cache header testini qo‘shing. Plaintext audit/logga tushmasligi hozirgidek saqlansin.

### F-06 — CSV hajm va encoding tekshiruvi body parse’dan keyin

**Severity: Medium**

- **Scenario:** juda katta fayl frontendda to‘liq RAMga o‘qiladi, JSON stringga aylantiriladi va FastAPI/Pydantic tomonidan to‘liq parse qilingandan keyingina 1 MB limit tekshiriladi; bu client/server memory DoSga sabab bo‘lishi mumkin. Non-UTF-8 fayl `File.text()`da replacement character bilan jim decode bo‘lib, canonical `ENCODING_INVALID` qaytmaydi.
- **Evidence:** frontend `selected.text()`ni size precheck’siz bajaradi (`frontend/src/pages/ResultImportPages.tsx:11-16`). API `csv_text: str`ni avval materialize qiladi (`src/schemas/api.py:279-287`), keyin service `encode('utf-8')` uzunligini tekshiradi (`src/services/imports.py:62-75`). Kontraktda `ENCODING_INVALID` barqaror code talab qilingan (`docs/02_methodology_contract.md:765`), lekin service bu codeni chiqarmaydi.
- **Minimal fix:** frontendda configured byte limitdan oldin file size guard; `arrayBuffer()` + fatal UTF-8 `TextDecoder`; reverse proxy/ASGI body limit; ideal holda bounded multipart/stream parser. Serverda invalid encoding uchun exact `ENCODING_INVALID` testini qo‘shing.

### F-07 — Import error maydon nomlari UI bilan mos emas

**Severity: Medium**

- **Scenario:** server qator/maydon/xato kodini qaytaradi, ammo UI noto‘g‘ri property o‘qigani uchun column `—`, sabab esa generic “Validatsiya xatosi” bo‘lib qoladi; operator faylni tuzata olmaydi.
- **Evidence:** backend error `row_number`, `column_name`, `error_code`, `suggested_action` qaytaradi (`src/services/imports.py:365-380`). UI `column ?? item_code` va `message ?? code`ni o‘qiydi (`frontend/src/pages/ResultImportPages.tsx:16`).
- **Minimal fix:** typed `ImportIssue` contract yarating va `column_name`, `error_code`, `message_key/suggested_action`ni exact render qiling; OpenAPI-generated type yoki contract test ishlating.

### F-08 — Pagination mavjud, UI faqat birinchi 100 yozuvni ko‘rsatadi

**Severity: Medium**

- **Scenario:** 101-chi participant, response yoki result topilmaydi; operator noto‘g‘ri “yo‘q” xulosasiga kelishi mumkin. `total` qaytsa-da next/previous yoki infinite loading yo‘q.
- **Evidence:** frontend barcha uch listda `limit=100` bilan bitta request qiladi (`frontend/src/pages/ParticipantPages.tsx:16`; `frontend/src/pages/ResponsePages.tsx:10`; `frontend/src/pages/ResultImportPages.tsx:20-21`). Backend `offset/limit/total` contractini beradi (`src/api/routers/read.py:252-283,327-361,456-486`).
- **Minimal fix:** server `total/offset/limit`ga asoslangan pagination controls; query keyga offset/filter/tenant qo‘shilsin; “101+ records” contract test.

### F-09 — Methodology version detail `use_type=research`ga hardcode qilingan

**Severity: Medium**

- **Scenario:** education yoki clinical use uchun eligible version tanlab research yaratiladi, ammo manual response sahifasi version detailni so‘raganda backend uni faqat `research` licence bilan tekshiradi va 404 qaytarishi mumkin.
- **Evidence:** eligible picker `use_type` queryni to‘g‘ri yuboradi (`frontend/src/pages/ResearchPages.tsx:15-18`), ammo keyingi detail call use type yubormaydi (`frontend/src/pages/ResponsePages.tsx:15-19`). Backend detail eligibilityni literal `"research"` bilan tekshiradi (`src/api/routers/read.py:171-191`). `ResearchView`da `use_type` ham yo‘q (`src/schemas/api.py:173-180`).
- **Minimal fix:** version detail eligibilityni pinned research context/use_type bilan tekshiradigan endpointdan oling yoki validated `use_type` query qo‘shing; `ResearchView`ga use_type kiriting; education/clinical E2E contract testi.

### F-10 — Licence restrictions tanlash/aktivatsiyadan oldin ko‘rsatilmaydi

**Severity: Medium**

- **Scenario:** researcher faqat `verified` va disclosure nomini ko‘rib research yaratadi; huquq egasi, allowed use/org/region va `restrictions_i18n`ni ko‘rmaydi. Compliance sharti ongli tasdiqlanmaydi.
- **Evidence:** backend detail licence restrictionlarni beradi (`src/schemas/read.py:19-39`), picker faqat version/minute/statusni chiqaradi (`frontend/src/pages/ResearchPages.tsx:16-18`), methodology detail faqat status va disclosure’ni chiqaradi (`frontend/src/pages/AdminPages.tsx:28-30`). Result disclaimer server snapshotidan ko‘rsatilishi ijobiy (`frontend/src/pages/ResultImportPages.tsx:25-26`).
- **Minimal fix:** selected version uchun licence summary/restrictions/disclaimer paneli va activate oldidan review gate; stringni frontendda ixtiro qilmasdan server snapshotidan oling.

### F-11 — Session token XSSga o‘qiladigan storage’da; CSP faqat hujjatda

**Severity: Medium**

- **Scenario:** kelajakdagi XSS `sessionStorage.psychogram_token`ni o‘qib, 60 daqiqagacha Bearer sifatida ishlatadi. Repo SPA response’iga CSP/security headerni o‘zi o‘rnatmaydi; bu reverse proxyga tashlab qo‘yilgan.
- **Evidence:** token sessionStorage’da saqlanadi (`frontend/src/context/AuthContext.tsx:9-18`). Minimum CSP faqat deployment ko‘rsatmasida (`frontend/README.md:17-31`); `frontend/index.html:1-10`da CSP meta yo‘q va FastAPI faqat CORS middleware qo‘shadi (`src/main.py:42-55`). React default escaping va `dangerouslySetInnerHTML` yo‘qligi riskni kamaytiradi, lekin tokenni XSSdan himoya qilmaydi.
- **Minimal fix:** productionda `HttpOnly; Secure; SameSite` server session/BFFni afzal ko‘ring; kamida deployment testida CSP, HSTS, `X-Content-Type-Options`, `Referrer-Policy` headerlarini assert qiling. Token storage cheklovini threat modelda explicit accept qiling.

### F-12 — Login/PII-admin access uchun brute-force va strong-auth gate yo‘q

**Severity: Medium**

- **Scenario:** attacker email topgach cheklanmagan login urinishlari qiladi; owner/admin yoki PII vakolatli akkaunt uchun MFA/step-up yo‘q. 12 belgili parol va Argon2 foydali, ammo online brute force va credential stuffingni o‘zi to‘smaydi.
- **Evidence:** login endpoint to‘g‘ridan-to‘g‘ri authenticate qiladi, rate-limit/lockout/risk event dependency yo‘q (`src/api/routers/auth.py:58-66`). Token barcha amallar, jumladan PII reveal uchun bir xil assurance bilan ishlaydi (`src/api/dependencies.py:20-45,99-111`). Product scope admin va PII vakolatli rollar uchun kuchli autentifikatsiyani talab qiladi (`docs/01_product_scope.md:199`).
- **Minimal fix:** reverse proxy/API qatlamida IP+account rate limit, generic login failure, security audit/alert; owner/admin/PII uchun MFA yoki PII reveal/exportda step-up authentication. Rate-limit va lockout bypass testlari qo‘shilsin.

### F-13 — Audit UI timestamp contracti noto‘g‘ri

**Severity: Low**

- **Scenario:** barcha audit event vaqtlari `—` ko‘rinadi, tergovchi timeline’ni UI orqali tekshira olmaydi.
- **Evidence:** API `occurred_at` qaytaradi (`src/api/routers/v1.py:528-550`), UI `row.created_at`ni o‘qiydi (`frontend/src/pages/AdminPages.tsx:23-25`).
- **Minimal fix:** typed AuditEvent va `occurred_at` render; contract fixture testi.

### F-14 — Download error stable domain codeni yo‘qotadi

**Severity: Low**

- **Scenario:** licence/consent gate yoki unsupported format xatosida oddiy API client stable error code/detailsni ko‘rsatadi, export helper esa faqat `HTTP_4xx` generic xabar qaytaradi; foydalanuvchi recovery sababini bilmaydi.
- **Evidence:** `api()` JSON error envelope’ni parse qiladi, `download()` qilmaydi (`frontend/src/lib/api.ts:11-35`).
- **Minimal fix:** download error response’ni content-type bo‘yicha xavfsiz parse qilib ayni `ApiError` mappingdan foydalaning; response bodyni loglamang.

## 3. OpenAPI ↔ frontend coverage

Quyidagi jadval runtime frontenddagi **barcha** `/api/v1` call guruhlarini OpenAPI bilan solishtiradi. `Exact` method/path/body/query mosligini, `Partial` esa endpoint ishlashi bilan birga response/UI yoki authorization gap borligini anglatadi.

| Endpoint | FE method | Status | Izoh |
|---|---|---|---|
| `/auth/bootstrap` | POST | Partial | Body mos; F-01 deployment/auth exposure |
| `/auth/register` | POST | Exact | JSON body va token response mos |
| `/auth/login` | POST | Exact | JSON body va token response mos |
| `/auth/me` | GET | Exact | Bearer bor, tenant header ataylab yo‘q |
| `/organizations/current/members` | GET/POST | Partial | Body/response mos; route/CTA role guard F-04 |
| `/retention-policies` | GET/POST | Partial | GET type mos; POST response refetch qilinadi; role UI F-04 |
| `/methodologies` | GET/POST | Exact | GET barcha auth user; POST serverda platform admin |
| `/methodologies/{id}` | GET | Partial | Response shape mos; licence display F-10 |
| `/methodologies/{id}/versions` | POST | Exact | Platform-admin registry body mos |
| `/methodology-versions/eligible?use_type=` | GET | Exact | Query enum backend patterniga mos |
| `/methodology-versions/{id}` | GET | Partial | Type mos; use_type behavior F-09 |
| `/methodology-versions/{id}/licences` | POST | Exact | Registry body schema bilan mos |
| `/methodology-versions/{id}/publish` | POST | Exact | `{reason}` mos |
| `/researches` | GET/POST | Exact | POST barcha required fieldlarni yuboradi |
| `/researches/{id}/activate` | POST | Partial | Body yo‘q — mos; CTA role guard F-04 |
| `/researches/{id}/participants` | GET/POST | Partial | Contract mos; pagination F-08 va role UI F-04 |
| `/researches/{rid}/participants/{pid}` | GET | Exact | Path/header/response mos |
| `/researches/{rid}/participants/{pid}/consents` | GET | Exact | History shape mos |
| `/participants/{pid}/consents` | POST | Partial | Body mos; auditor CTA F-04 |
| `/researches/{rid}/participants/{pid}/pii` | GET/PUT/DELETE | Partial | Body/shape exact; no-store/plaintext lifecycle F-05 |
| `/researches/{id}/responses` | GET/POST | Partial | Body mos; pagination va role UI F-04/F-08 |
| `/responses/{id}` | GET | Exact | Detail/current revision shape mos |
| `/responses/{id}/validate` | POST | Partial | Body yo‘q — mos; auditor UI F-04 |
| `/researches/{id}/calculations` | POST | Exact | `response_revision_id` + body idempotency key mos |
| `/researches/{id}/imports/preview` | POST | Partial | JSON `csv_text` mos; F-06/F-07 |
| `/researches/{id}/imports/{import_id}/confirm` | POST | Exact | `preview_hash` mos |
| `/results` | GET | Partial | Filters mos; pagination F-08 |
| `/results/{id}` | GET | Exact | Result/scales/trace response compatible |
| `/results/{id}/export?format=` | GET | Partial | JSON/CSV query mos; RBAC F-02 va error F-14 |
| `/audit-events` | GET | Partial | Array mos; timestamp F-13 |

Frontend chaqirmaydigan, lekin OpenAPI’da mavjud querylar: `/organizations/current`, methodology version list, licence history/current, response revision create/history/detail. UI ular mavjuddek phantom action ko‘rsatmaydi.

**B07–B10/B12 tekshiruvi:** pause/close/archive, member edit/revoke, server audit pagination/filter, XLSX/PDF/template download/mapping va correlation-IDga tayangan UI action topilmadi. UI faqat JSON/CSV export qiladi; README va import ekrani cheklovni ochiq aytadi. Backend xlsx/pdf queryni explicit 415 qiladi, lekin frontend yubormaydi.

## 4. Auth, tenant va security control natijalari

| Control | Natija | Evidence |
|---|---|---|
| Bearer header | PASS | `api.ts:16`, unit test `api.test.ts:6` |
| `X-Organization-ID` | PASS | Tenant calllarda `useApi`; auth/me’da ataylab yo‘q; unit tests `api.test.ts:6,8` |
| Backend tenant membership | PASS | `src/api/dependencies.py:62-86`; cross-tenant PII test 404 (`tests/test_ux_backend_gaps.py:367-392`) |
| Platform admin tenant bypass yo‘q | PASS | `_catalog_tenant` membershipsiz admin uchun faqat global catalogga `None`; tenant data `tenant_context` talab qiladi (`src/api/routers/read.py:651-678`) |
| PII role + separate flag | PASS | role va `can_view_pii` ikki gate (`src/api/dependencies.py:99-111`) |
| AES-GCM at rest | PASS | 32-byte key validation, 12-byte nonce, tenant/research/participant/key-version AAD (`src/core/config.py:59-78`, `src/services/pii.py:20-91`) |
| PII audit | PASS | create/update/view/delete eventlar faqat field nomlarini yozadi (`src/services/pii.py:83-99,131-141,183-193`) |
| PII legal hold | PASS | active research hold delete’ni 409 bilan bloklaydi (`src/services/pii.py:151-172`) |
| CSV PII header block | PASS | PII header allow-deny (`src/services/imports.py:20-36,88-91`) |
| CSV formula injection export | PASS | `= + - @ TAB CR` apostrof bilan neutralizatsiya (`src/services/exports.py:12-20`); test `tests/test_ux_backend_gaps.py:262-265` |
| Licence/disclaimer scoring | PASS | scoring va export current licence gate; result server disclaimer snapshotini UI ko‘rsatadi |
| Error envelope | PARTIAL | Domain error stable; FastAPI 422 `detail` generic UIga tushadi; export helper code’ni yo‘qotadi |
| CORS | PASS/config-dependent | Wildcard reject, explicit origins, limited methods/headers (`src/core/config.py:37-42`; `src/main.py:42-55`) |
| Iconify privacy | PASS with disclosure | Faqat `<img>`, fixed Lucide path, `no-referrer`, anonymous CORS, local fallback; remote server IP/icon nomini ko‘radi (`RemoteIcon.tsx:3-8`) |
| CSP/security headers | NOT VERIFIED at deployment | Policy README’da bor; actual hosting/reverse-proxy config workspace’da yo‘q (F-11) |

## 5. Dependency va test holati

| Check | Natija |
|---|---|
| Backend pytest | **42 passed**, 1 Starlette TestClient deprecation warning, 12.14s (`--basetemp=.pytest-audit-tmp`) |
| Frontend Vitest | **17 passed**, 6 files |
| TypeScript typecheck | PASS |
| ESLint (`--max-warnings 0`) | PASS |
| Vite production build | PASS, 506 modules, JS 141.27 kB gzip, CSS 5.82 kB gzip |
| `pip check` | PASS — no broken requirements |
| `npm audit --omit=dev` | PASS — **0 vulnerabilities** |

Izoh: birinchi `npm audit` sandbox network/cache cheklovi sabab registry endpointiga bora olmadi; user-approved escalated network bilan qayta bajarilib 0 vulnerability olindi. Birinchi pytest run barcha 42 testni bajardi, lekin Windows global temp `pytest-current` symlink cleanup permission bilan exit 1 bo‘ldi; workspace `--basetemp` bilan qayta run toza exit 0 berdi. Bu test failure emas, runner temp permission cheklovi.

## 6. Minimal release ketma-ketligi

1. F-01 bootstrap takeover va F-02 auditor export authorizationni tuzatish; deny/integration testlar.
2. Tenant switch query cancellation + tenant-scoped cache keylar (F-03), so‘ng ikki tenantli race test.
3. Role capability map va phantom CTA’larni yopish (F-04).
4. PII no-store/security headers hamda production CSP/BFF qarori (F-05/F-11).
5. CSV size/encoding/error contract va pagination (F-06–F-08).
6. use_type/licence disclosure, strong auth va low contract mismatchlar (F-09, F-10, F-12–F-14).

Shu findinglar yopilgach backend pytest, frontend type/lint/test/build, cross-tenant/race, auditor export deny, PII cache-header va deployment header smoke testlarini qayta bajarish kerak.

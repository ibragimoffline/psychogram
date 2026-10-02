# F bosqichi: pilotni ishga tushirish va ekspluatatsiya qo'llanmasi

Sana: 2026-10-02. Asos: [08_mvp_pilot_scope.md](08_mvp_pilot_scope.md), 8-bo'lim va F bosqichi.

Bu hujjat pilotni server muhitida ishga tushiradigan va qo'llab-quvvatlaydigan odam uchun:
o'rnatish ketma-ketligi, ma'lumotlar bazasi huquqlari, backup va tiklash, rollback, loglar,
saqlash muddati va qabul sinovlarining dalillari. 5-bo'limdagi sinov natijalari bir martalik
lokal PostgreSQL klasterida olingan. Haqiqiy server, proxy va real foydalanuvchilar bilan
sinov hali o'tkazilmagan (9-bo'lim).

## 1. Muhit

| Komponent | Talab | Tekshirilgan |
|---|---|---|
| Python | 3.14, `requirements.txt` | 3.14.3 |
| PostgreSQL | 16+ tavsiya; UTF-8 baza | 18.1 |
| Reverse proxy | TLS, HSTS, body limit, login rate limit | Namuna: [deploy/nginx/psychogram.conf.example](../deploy/nginx/psychogram.conf.example) (sinalmagan) |
| Frontend | `npm run build` natijasi (`frontend/dist`) | build o'tadi |

## 2. Secret va sozlamalar

Barcha qiymatlar secret manager orqali beriladi; repository yoki loglarga yozilmaydi.

| O'zgaruvchi | Pilot qiymati | Izoh |
|---|---|---|
| `PSYCHOGRAM_ENVIRONMENT` | `production` | Secret'larni qat'iy tekshiradi |
| `PSYCHOGRAM_DATABASE_URL` | `postgresql+psycopg2://psychogram_app:…@host/psychogram` | API **faqat** `psychogram_app` bilan ulanadi |
| `PSYCHOGRAM_JWT_SECRET` | ≥32 tasodifiy belgi | Almashtirilsa barcha sessiyalar tugaydi |
| `PSYCHOGRAM_BOOTSTRAP_ENABLED` / `_TOKEN` | faqat birinchi o'rnatishda `true` | Keyin `false` qilib qayta ishga tushiriladi |
| `PSYCHOGRAM_REGISTRATION_ENABLED` | `false` | Tashkilotni admin yaratadi |
| `PSYCHOGRAM_CSV_IMPORT_ENABLED` | `false` | Birinchi relizda import yo'q |
| `PSYCHOGRAM_PII_ENCRYPTION_KEY` / `_KEY_VERSION` | 32 bayt Base64 / `v1` | Pilot PII ishlatmaydi; berilmasa PII endpointlari 503 |
| `PSYCHOGRAM_CORS_ORIGINS` | pilot domeni | Frontend bir xil domenda bo'lsa ham aniq ko'rsatiladi |
| `VITE_ENABLE_REGISTRATION`, `VITE_ENABLE_CSV_IMPORT` | `false` | Build vaqtida |

Kalit yaratish: `python -c "import base64,os;print(base64.b64encode(os.urandom(32)).decode())"`,
token: `python -c "import secrets;print(secrets.token_urlsafe(48))"`.

**PII kaliti backup'dan alohida saqlanadi.** Kalitsiz shifrlangan PII'ni tiklab bo'lmaydi;
kalit va backup birga saqlansa, backup sizib chiqqanda shifrlash ma'nosini yo'qotadi.

## 3. Birinchi o'rnatish

1. **Baza va owner rol.** DBA `psychogram` bazasini va unga egalik qiluvchi migratsiya rolini
   (masalan, `psychogram_owner`) yaratadi.
2. **Migratsiya** owner rol bilan: `PSYCHOGRAM_DATABASE_URL=<owner url> alembic upgrade head`.
3. **Ilova roli:** `psql -d psychogram -v app_password='…' -f deploy/postgres/app_role.sql`.
   Skript har migratsiyadan keyin qayta ishga tushiriladi (idempotent).
4. **API** `psychogram_app` URL bilan, bootstrap yoqilgan holda ishga tushiriladi.
5. `POST /api/v1/auth/bootstrap` — platform administrator.
6. Bootstrap o'chiriladi (`PSYCHOGRAM_BOOTSTRAP_ENABLED=false`), API qayta ishga tushiriladi.
7. Administrator `POST /api/v1/organizations` bilan pilot tashkilotini va owner'ni yaratadi; owner
   tadqiqotchilarni `POST /api/v1/organizations/current/members` bilan qo'shadi va retention
   siyosatini yaratadi.
8. Administrator pilot metodikasini ([docs/10](10_methodology_package.md)) kiritib publish qiladi.
9. Frontend build proxy orqali beriladi; proxy talablari 6-bo'limda.

**Smoke sinovi.** [scripts/pilot_smoke.py](../scripts/pilot_smoke.py) butun pilot oqimini
ishlab turgan API'da tekshiradi. U bootstrap qilgani uchun **faqat bo'sh bazada** ishlaydi;
production bazada bootstrap rad etiladi va skript hech narsa yozmaydi. Staging'da:
`PSYCHOGRAM_BOOTSTRAP_TOKEN=… python scripts/pilot_smoke.py --base-url https://staging…`,
keyin staging bazasi o'chiriladi.

## 4. Ma'lumotlar bazasi huquqlari

[deploy/postgres/app_role.sql](../deploy/postgres/app_role.sql):

- barcha jadvallarda `SELECT`, `INSERT`;
- `UPDATE` faqat kod joyida yangilaydigan 7 jadvalda: `researches`, `responses`,
  `response_revisions`, `calculation_runs`, `import_jobs`, `methodology_versions`, `participant_pii`;
- `DELETE` faqat `participant_pii`da (legal hold bo'lsa API baribir bloklaydi);
- `alembic_version` va sxemaga yozish huquqi yo'q.

Kodga yangi `UPDATE` yoki `DELETE` yo'li qo'shilsa, skript ham yangilanadi; aks holda API
`permission denied` bilan 500 qaytaradi. Smoke sinovi barcha ruxsat etilgan yo'llarni qamraydi.

`response_revisions` va `methodology_versions`da `UPDATE` huquqi bor (qoralama holatini
o'zgartirish uchun). Tasdiqlangan revision va nashr qilingan versiyani esa `0003` migratsiyasidagi
trigger'lar har qanday rol uchun, jumladan owner uchun ham, bloklaydi.

## 5. 2026-10-02 dagi sinov dalillari

Bir martalik PostgreSQL 18.1 klasteri (`initdb`, port 55432) ishlatildi; foydalanuvchining mavjud
PostgreSQL xizmatiga tegilmagan.

| Tekshiruv | Natija |
|---|---|
| `alembic upgrade head` → `downgrade base` → `upgrade head` | O'tdi, 34 jadval |
| `alembic check` (model ↔ migratsiya) | "No new upgrade operations detected" |
| Butun API test to'plami PostgreSQL'da (`PSYCHOGRAM_TEST_DATABASE_URL`) | 74 passed |
| `app_role.sql` ikki marta ketma-ket | Xatosiz; huquqlar kutilgandek |
| API `psychogram_app` bilan, `production` rejimida, `pilot_smoke.py --with-pii` | 16/16 PASS |
| `psychogram_app` bilan to'g'ridan-to'g'ri `UPDATE results`, `UPDATE scale_results`, `UPDATE consent_records`, `DELETE audit_events`, `DELETE trace_steps`, `DELETE response_revisions`, `DROP TABLE`, `CREATE TABLE`, `UPDATE alembic_version` | Hammasi rad etildi |
| `pg_dump -Fc` (122 KB) → yangi bazaga `pg_restore --exit-on-error` | O'tdi |
| `scripts/compare_databases.py` manba ↔ tiklangan | 34/34 jadval mos (soni va checksum) |
| Solishtirishning sezgirligi: tiklangan bazada bitta qator o'zgartirildi | `DIFF organizations` |
| `0003` trigger'lari: upgrade → downgrade -1 → upgrade, `alembic check` | O'tdi, farq yo'q |
| Trigger'lar bilan `pilot_smoke.py --with-pii` (app rol) | 16/16 PASS |
| `UPDATE` tasdiqlangan revision / nashr qilingan versiya (app rol va owner) | Rad etildi: "… is immutable" |
| `UPDATE` validatsiyadan o'tmagan revision (app rol) | Ruxsat berildi (ORM qoidasi bilan bir xil) |
| API to'xtatilib qayta ishga tushirildi (asl baza) | Ma'lumotlar joyida; o'qish va yozish ishladi |
| Tiklangan bazada API, xuddi shu PII kaliti bilan | Tadqiqot CSV eksporti bayt-ma-bayt bir xil; natija, yopilgan holat va shifrlangan PII bir xil |
| Server loglarida PII, javob, parol yoki token qidiruvi | Topilmadi (faqat so'rov qatorlari) |

## 6. Reverse proxy talablari

API o'zi rate limit, MFA yoki TLS bermaydi. Ommaviy tarmoqqa chiqishdan oldin proxy:

- **TLS va HSTS**, HTTP→HTTPS yo'naltirish;
- **body limit** `PSYCHOGRAM_MAX_REQUEST_BODY_BYTES` dan oshmasin (namunada `3m`), JSON parse'dan oldin `413`;
- **login rate limit** IP bo'yicha (namunada 5/daqiqa, `429`); kredensial to'ldirib urinishlar kuzatiladi;
- **SPA** `try_files … /index.html` va frontend README'dagi CSP;
- **access log** query string'siz (respondent kodi qidiruvda query'da keladi).

Namuna konfiguratsiya sinalmagan; ishga tushirishdan oldin `nginx -t`, so'ng `curl -I` bilan
HSTS/CSP header'lari, katta body uchun `413` va ketma-ket login uchun `429` tekshiriladi.

## 7. Backup, tiklash va rollback

**Backup** (owner rol bilan, kuniga kamida bir marta):

```sh
pg_dump -h <host> -U psychogram_owner -Fc -f psychogram-$(date +%F).dump psychogram
```

Fayllar shifrlangan, boshqa joydagi saqlashga ko'chiriladi; saqlash muddati va mas'ul belgilanadi.
`pg_dump` rollarni o'z ichiga olmaydi.

**Tiklash:**

1. Yangi bazani yarating; yangi serverda avval owner rolni yarating.
2. `pg_restore -d <yangi baza> --exit-on-error psychogram-….dump`.
3. `psql -d <yangi baza> -v app_password=… -f deploy/postgres/app_role.sql`.
4. `python scripts/compare_databases.py <manba url> <yangi url>` (manba mavjud bo'lsa) — `0 mismatch`.
5. API'ni yangi bazaga, **o'sha PII kaliti** bilan ulang; `/health`, login, bitta natija va
   tadqiqot eksportini oching.

**Tiklash mashqi** kamida pilot boshlanishidan oldin va keyin har oy bir marta bajariladi;
natija sana bilan shu hujjatga yoki operatsion jurnalga yoziladi.

**Migratsiya va rollback:**

1. Migratsiyadan oldin backup oling va uni tiklab bo'lishini tekshiring.
2. `alembic upgrade head`, keyin `app_role.sql`, keyin API'ning yangi versiyasi.
3. Rollback uchun **backup'dan tiklash va oldingi versiyani qaytarish** afzal. `alembic downgrade`
   ma'lumotni yo'qotishi mumkin: masalan, `0002` downgrade `participant_pii`dagi `nonce`,
   `key_version` va boshqa ustunlarni o'chiradi, bu esa shifrlangan PII'ni o'qib bo'lmaydigan qiladi.

## 8. Saqlash muddati, loglar va mas'uliyat

- **Retention worker yo'q.** Retention siyosati faqat bazadagi yozuv; uni o'zi bajarmaydi.
  Pilot boshlanishidan oldin **mas'ul shaxs** tayinlanadi va qo'lda bajariladigan jarayon
  yoziladi: qachon ko'rib chiqiladi, nima o'chiriladi, kim tasdiqlaydi, qayerda qayd etiladi.
  MVP'da natija va javoblarni o'chiradigan vosita yo'q (ular ataylab immutable). Muddat tugashidan
  oldin o'chirish usuli alohida kelishib olinishi kerak; bu ochiq masala.
- **Loglar:** uvicorn access log metod, yo'l, query string va status kodini yozadi. Yo'llarda faqat
  UUID'lar bor; query string'da respondent kodi bo'lishi mumkin, shuning uchun proxy logida u
  yozilmaydi (6-bo'lim). 500 xatoliklarning traceback'ida baza cheklovi xabari (masalan, takroriy
  kod qiymati) bo'lishi mumkin. Log saqlash muddati va ularga kirish huquqi cheklanadi.
- **Audit:** `GET /api/v1/audit-events` (owner/admin/auditor) — oxirgi 200 hodisa; xom javob va
  PII yozilmaydi.

## 9. Pilot qabul sinovlari va dalillar

| № | Sinov ([08](08_mvp_pilot_scope.md), 10-bo'lim) | Avtomatik dalil | Qo'lda qoladigan qism |
|---|---|---|---|
| 1 | Kirish, metodika tanlash, tadqiqot boshlash | `researchLifecycle`/`flows` frontend testlari, `test_registration_is_closed_and_admin_creates_organizations`, smoke | Real foydalanuvchi bilan |
| 2 | Roziliksiz hisoblash yo'q; rozilik aniq kiritiladi | `test_consent_and_research_pin_gates`, frontend "does not create anything until consent is confirmed" | — |
| 3 | 20 respondent, qoralama, qayta ochish | frontend "saves a draft…", "reopens saved answers…" | 20 ta respondent bilan qo'lda |
| 4 | ≥3 mustaqil etalon natija mos | `test_contract_scoring_vectors` (sintetik) | **Haqiqiy metodika bilan (B bosqichi)** |
| 5 | Xatolar savol yonida | `test_validation_issues_are_returned_per_item`, frontend "shows validation errors next to the question…" | Ekranda ko'rib chiqish |
| 6 | Takror bosish va tarmoq uzilishi nusxa yaratmaydi | `test_scoring_disclaimer_and_idempotency`, frontend "retries after a lost network response…" | — |
| 7 | Tuzatishda eski natija saqlanadi, "Qayta hisoblash kerak", eksport eskisini bermaydi | `test_response_list_reports…`, `test_result_marks…`, `test_corrected_answers_are_not_exported…` | — |
| 8 | Boshqa tashkilot kira olmaydi | `test_rbac_and_cross_tenant_denial`, `test_export_respects_roles_and_tenant` | — |
| 9 | Rozilik/litsenziya bekor qilinsa bloklanadi | `test_withdrawn_consent_blocks_cached…`, `test_revoked_licence_blocks_cached…`, `test_export_is_refused_when_the_licence_is_revoked` | — |
| 10 | CSV ekranga mos, sahifalashdan katta to'plamda qator yo'qolmaydi | `test_export_has_one_row…`, `test_export_includes_every_respondent_beyond_page_size` (105) | **Excel'da ochish** (o'zbek/rus locale'da vergul ajratgich) |
| 11 | Yopilgan tadqiqot: kiritish yo'q, natija va eksport bor | `test_closed_research_blocks_changes_but_keeps_results_readable`, frontend yakunlash testlari | — |
| 12 | Qayta ishga tushirish va backup'dan tiklash | 5-bo'lim (lokal mashq) | **Haqiqiy serverda mashq** |

**Real foydalanuvchi sinovi** (F bosqichining yakuni): 1–2 tadqiqotchi pilot metodikasi bilan
kamida 20 respondentni kiritadi, bittasini tuzatadi, CSV'ni Excel/SPSS'da ochadi va tadqiqotni
yakunlaydi. Har bir qadamda kuzatilgan muammo va vaqt yoziladi.

## 10. Ochiq qolganlar

- B: haqiqiy metodika paketi va etalon misollar.
- Haqiqiy server, proxy konfiguratsiyasi va TLS'ni sinash; tiklash mashqini shu muhitda takrorlash.
- Excel'da CSV ko'rinishi; kerak bo'lsa nuqta-vergulli variant.
- Retention bo'yicha mas'ul va o'chirish jarayoni.
- MFA yoki step-up authentication (README'dagi release gate) — IdP/proxy darajasida.

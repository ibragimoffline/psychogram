# A bosqichi: kod va hujjat solishtiruvi, lokal ishga tushirish

Sana: 2026-10-02. Asos: [08_mvp_pilot_scope.md](08_mvp_pilot_scope.md), 9-bo'lim, A bosqichi.
Tekshiruv paytida kodga o'zgarish kiritilmagan.

**Holat (2026-10-02, branch `fix/stage-a-gates`):** F-01, F-02 — `ad77bcb`; F-03, F-04 — `d74f81a`;
F-05 — `8490da5`; F-07 — `9861703`; F-08 — `8ccd3b2`; F-15 — repository GitHub'ga ulandi (`712826f`).
C bosqichi (branch `feat/stage-c-onboarding`): F-09 — `568b045`; F-12 — `0542e2f`.
Qolganlari ochiq.

## 1. Muhit

| Narsa | Holat |
|---|---|
| Python | 3.14.3, `.venv` tayyor, `requirements.txt` o'rnatilgan |
| Node | `frontend/node_modules` o'rnatilgan |
| `.env` | Yo'q; sinov env o'zgaruvchilari bilan o'tkazildi |
| Git | `.git` papkasi **bo'sh**: repository emas, versiya tarixi yo'q |
| AGENTS ko'rsatmalari | `.agents` papkasi **bo'sh**, ko'rsatma yo'q |

## 2. Tekshiruvlar natijasi

| Tekshiruv | Buyruq | Natija |
|---|---|---|
| Backend testlari | `python -m pytest -q` | **52 passed** (43 test funksiyasi, parametrlangan holatlar bilan 52) |
| Migratsiya | `alembic upgrade head` → `downgrade base` → `upgrade head` (toza SQLite) | O'tdi; rollback ishlaydi |
| Server | `uvicorn src.main:app`, `GET /health` | `{"status":"healthy","database":"reachable"}` |
| Frontend typecheck / lint / build | `npm run typecheck`, `lint`, `build` | O'tdi (JS 461 kB, gzip 144 kB) |
| Frontend testlari | `npm run test` | 30 tadan 29 o'tdi; 1 ta **beqaror** (§3, F-08) |
| Jonli HTTP smoke | 32 ta tekshiruv, pilot oqimi boshidan oxirigacha | 29 o'tdi, 3 ta yiqildi (§3) |

Smoke oqimi: bootstrap → registratsiya → tadqiqotchi va auditor qo'shish → metodika, versiya,
litsenziya, publish → retention → tadqiqot yaratish va aktivlash → respondent → rozilik →
qoralama → validatsiya xatosi → tuzatish → hisoblash (takror bosish) → CSV eksport →
javobni tuzatish va qayta hisoblash → rozilikni qaytarib olish → boshqa tashkilotdan kirish urinishi.

Ishlashi tasdiqlangan: rozilik bo'lmasa javob bloklanadi; reverse scoring to'g'ri (maksimum 10.00);
takroriy hisoblash bitta natija beradi; disclaimer bor; eski natija tuzatishdan keyin saqlanadi;
boshqa tashkilot natija va javobga 404, begona `X-Organization-ID` bilan 403 oladi;
auditor eksporti backendda 403.

## 3. Kod va hujjat orasidagi farqlar

Ustuvorlik: **P0** — pilot qabul sinovini to'g'ridan-to'g'ri buzadi; **P1** — oqimga xalaqit beradi;
**P2** — sifat yoki texnik qarz.

| ID | Ustuvorlik | Topilma | Dalil | Bog'liq joy |
|---|---|---|---|---|
| F-01 | P0 | Rozilik qaytarib olingach ham shu `idempotency_key` bilan hisoblash 200 va eski natijani qaytaradi | Smoke: `calculations` → 200; [orchestration.py:559-594](../src/services/orchestration.py#L559-L594) cache gate'lardan oldin | Qabul sinovi 9 |
| F-02 | P0 | Rozilik qaytarib olingach `GET /results/{id}` hali ham 200 qaytaradi (eksport esa to'g'ri, 409) | Smoke | Qabul sinovi 9 |
| F-03 | P0 | Takroriy respondent kodi **500 Internal Server Error** beradi, 409 emas | Smoke + log: `UNIQUE constraint failed: participants...`; `create_participant` oldindan tekshirmaydi | Funksiya 3 |
| F-04 | P1 | Takroriy retention policy kodi ham 500 beradi | Jonli so'rov | Tadqiqot sozlash |
| F-05 | P0 | Validatsiya xatolari (`ResponseValidationIssue`) bazaga yoziladi, lekin **hech bir API qaytarmaydi**; faqat `error_count` bor. "Xato savol yonida" talabini bajarib bo'lmaydi | `grep ResponseValidationIssue` faqat yozishda; smoke | Funksiya 4, qabul sinovi 5 |
| F-06 | P1 | Frontend trace'dan `step_name/operation/step_type` o'qiydi, backend `step_code` qaytaradi — real trace qadamlari "Bosqich N" bo'lib chiqadi | Smoke; [ResultImportPages.tsx:43](../frontend/src/pages/ResultImportPages.tsx#L43); test mock'i backend shakliga mos emas | Natija ekrani |
| F-07 | P1 | Frontend auditorga `result:export` beradi, backend 403 qaytaradi | [capabilities.ts](../frontend/src/lib/capabilities.ts); smoke | 2-bo'lim, E bosqichi |
| F-08 | P2 | `flows.test.tsx` → "keeps disclaimer visible…" beqaror: 3 ta ishga tushirishdan 1 tasida yiqildi; trace `motion` animatsiyasi `opacity:0` dan boshlanadi | Vitest qayta ishga tushirish | CI ishonchliligi |
| F-09 | P1 | `/auth/register` ochiq va uni o'chiradigan sozlama yo'q — istalgan odam tashkilot yaratadi | Smoke: 201; `Settings`da flag yo'q | 6-bo'lim, ochiq registratsiya |
| F-10 | P1 | Research'da `closed` holati, `POST /researches/{id}/close` va `GET /researches/{id}/export` yo'q | Smoke: 404/405 | Funksiya 6, qabul sinovlari 10–11 |
| F-11 | P1 | Natijalar ro'yxati `limit ≤ 100`; tadqiqot bo'yicha to'liq eksport sahifalashsiz yo'q | `limit=500` → 422 | Qabul sinovi 10 |
| F-12 | P1 | Tadqiqot yaratish `ready`, aktivlash alohida chaqiruv | Smoke | Ekran 3, "Yaratish va boshlash" |
| F-13 | P1 | Haqiqiy pilot metodikasi yo'q; faqat test fixture'i `synth_balance_demo` (sintetik norm va talqin) | `tests/conftest.py` | B bosqichi |
| F-14 | P2 | Metodika kontrakti aniq bitta `total` shkalani talab qiladi | `validate_snapshot` | B bosqichi metodika tanlovi |
| F-15 | P2 | Repository yo'q (`.git` bo'sh) — o'zgarishlarni kuzatish va qaytarish imkoni yo'q | `git status` → not a repository | Barcha bosqichlar |
| F-16 | P2 | Testlar `httpx` + `starlette.testclient` bo'yicha deprecation ogohlantirishi beradi | pytest warning | Texnik qarz |

Javob holati to'g'ri ishlaydi: tuzatishdan keyin response `scored` emas, `validated` bo'ladi.
Bu "Qayta hisoblash kerak" belgisini frontendda ko'rsatish uchun yetarli asos (C/D bosqichlari).

## 4. Keyingi qadamlar bo'yicha tavsiya

1. **F-15:** kod o'zgarishidan oldin `git init` va boshlang'ich commit qilish.
2. **E bosqichidagi tuzatishlarni oldinroq olish:** F-01/F-02 (gate'lar cache'dan oldin),
   F-03/F-04 (unique xatolarni 409 ga aylantirish), F-07. Ular kichik va qabul sinovlarini to'g'ridan-to'g'ri buzadi.
3. **D bosqichidan oldin F-05:** validatsiya xatolarini revision detail javobiga qo'shish.
4. **B bosqichi** (F-13, F-14): haqiqiy metodika paketi tashqaridan kelishi kerak — kalit, norm,
   litsenziya asosi va kamida 3 ta etalon misol.

## 5. Takrorlash

Smoke skripti sessiyaning vaqtinchalik papkasida edi. Testlar: `pytest -q`;
frontend: `npm run typecheck && npm run lint && npm run test && npm run build`;
migratsiya: `alembic upgrade head`, `alembic downgrade base`.

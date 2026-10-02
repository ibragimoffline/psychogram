# Release remediation va yakuniy verifikatsiya

Sana: 2026-07-16  
Holat: **kod gate'lari PASS; real browser va production deployment gate'lari PENDING**

## Natija

`05_accessibility_responsive_qa.md` va `06_contract_security_qa.md` auditlarida qayd
etilgan critical/high findinglar hamda asosiy medium findinglar tuzatildi. Eski audit
fayllari boshlang'ich holatning tarixiy dalili sifatida saqlandi; ushbu hujjat esa
remediationdan keyingi holatni qayd etadi.

## Backend remediation

- Bootstrap default o'chiq. Uni yoqish explicit flag va kamida 32 belgili tokenni
  talab qiladi; token digestlari constant-time taqqoslanadi.
- Result eksporti faqat owner, admin va researcher capability'lariga berildi;
  auditor va operator server tomonidan rad etiladi.
- PII, result, calculation va export javoblariga `no-store`, `private`, `nosniff`
  hamda umumiy API security headerlari qo'shildi.
- Import preview declared charset va `Content-Length`ni body parse'dan oldin
  tekshiradi. Reverse proxy body limiti alohida deployment gate sifatida hujjatlandi.
- Research read kontraktiga `use_type` qo'shildi. Methodology version eligibility
  validated `use_type` yoki server-authoritative pinned `research_id` orqali
  hisoblanadi.
- Login rate-limit, MFA/step-up, HTTPS va HSTS reverse proxy/IdP release
  majburiyatlari README'da qayd etildi.

## Frontend remediation

- Backend bilan bir xil markaziy capability xaritasi route, navigation va CTA'larda
  ishlatiladi; auditor eksporti va operatorga tegishli bo'lmagan amallar yashiriladi.
- Bootstrap sahifasi/linki faqat development va explicit feature flag bilan ochiladi.
- Tenant switch `cancelQueries -> clear -> select` tartibida ishlaydi; tenant query
  keylari organization ID bilan izolyatsiyalangan va PII state remountda tozalanadi.
- Tablet navigatsiyasi accessible nom, tooltip va tenant switchni saqlaydi;
  breakpointlar 768/1200 dizayn kontraktiga moslashtirildi.
- `ErrorSummary`, field ARIA association, reusable keyboard-safe `ConfirmAction`,
  labelled responsive recordlar, route focus/title va live async status qo'shildi.
- PII reveal uchun explicit remask, 44px touch target, focused dropzone va
  reduced-motion trace holati qo'shildi.
- CSV import clientda size va fatal UTF-8 tekshiruvidan o'tadi; issue maydonlari API
  kontraktiga mos. Participant, response va result listlarida pagination mavjud.
- Licence snapshot, audit `occurred_at` va download `DomainError` diagnostikasi
  to'g'rilandi.

## Yakuniy avtomatlashtirilgan verifikatsiya

| Tekshiruv | Natija |
| --- | --- |
| Backend Pytest | PASS — 52 test |
| Black | PASS — 41 file o'zgarishsiz |
| Flake8 | PASS |
| Mypy | PASS — 29 source file |
| Python dependency check | PASS — broken requirement yo'q |
| Fresh migration va `0001 -> head` | PASS; head `0002_pii_aes_gcm` |
| Frontend TypeScript | PASS |
| ESLint | PASS — warning yo'q |
| Vitest | PASS — 8 file, 30 test |
| Vite production build | PASS — 510 modul |
| Production npm dependency audit | PASS — 0 vulnerability |

Build o'lchami: JS 461.41 kB / 143.65 kB gzip; CSS 30.56 kB / 6.38 kB gzip.
Generatsiya qilingan `dist` va vaqtinchalik test kataloglari verifikatsiyadan keyin
tozalandi.

## Release oldidan qolgan tashqi gate'lar

Quyidagilar ushbu sessiyada browser runtime mavjud bo'lmagani yoki production
infratuzilmasi workspace doirasida bo'lmagani sabab PASS deb belgilanmadi:

1. In-app browserda real login va asosiy UI oqimlari, browser console/network holati.
2. 320 px reflow, 768/1024/1200 viewportlar va 200% zoom visual tekshiruvi.
3. Keyboard-only, real screen reader va Axe/Lighthouse auditi.
4. Remote Iconify fallback va `prefers-reduced-motion` runtime tekshiruvi.
5. Production reverse proxyda CSP, HTTPS/HSTS, request-body limit va login
   rate-limit; IdP/MFA/step-up konfiguratsiyasi.

Shuning uchun kod bazasi keyingi integratsiya bosqichiga tayyor, ammo internetga
ochiq production release yuqoridagi browser va deployment gate'lari bajarilmaguncha
shartli hisoblanadi.

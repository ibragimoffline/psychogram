# Browser E2E va visual QA hisoboti

Sana: 2026-07-16  
Holat: **qisman bajarildi — API/runtime qatlam o‘tdi, in-app browser auditi tool blocker sabab bajarilmadi**

## Qamrov va muhit

- Faqat lokal sintetik ma’lumot ishlatildi; real foydalanuvchi yoki real PII ishlatilmadi.
- Alohida vaqtinchalik SQLite bazaga Alembic `head` (`0001 -> 0002_pii_aes_gcm`) qo‘llandi.
- Production-mode konfiguratsiya, 32+ belgili sintetik JWT secret, 32-baytli Base64 sintetik PII kalit va bootstrap token ishlatildi.
- Parallel agentlar ishlayotgani sabab `127.0.0.1:5173` boshqa Node process tomonidan band edi; `127.0.0.1:8000` bind ham Windows tomonidan rad etildi. Begona processlar to‘xtatilmadi.
- Izolyatsiyalangan audit instansiyasi backend `127.0.0.1:8011`, frontend `127.0.0.1:5174`da ishga tushirildi. Frontend `VITE_API_ORIGIN=http://127.0.0.1:8011` bilan xizmat qildi.
- Frontend `/login`: HTTP `200`, `text/html`, React root mavjud.

## Verifikatsiya cheklovi

`browser-use` yo‘riqnomasi bo‘yicha majburiy `iab` workflow tanlandi. Biroq ushbu subagent sessiyasida `iab`ni boshqaradigan Node JavaScript execution vositasi (`mcp__node_repl__js`) tool katalogida mavjud emas edi. Skill ko‘rsatmasiga muvofiq standalone Playwright, Selenium yoki boshqa tashqi browser-control backendga o‘tilmadi.

Shu sabab quyidagilar **tekshirilmagan**, ularni pass deb hisoblash mumkin emas:

- real UI login va sessiya hydration;
- tenant shell, sidebar, tab va navigatsiya;
- barcha form, modal/drawer va toast oqimlari;
- browser console error/warninglari va browser network failurelari;
- Iconify remote icon hamda accessible fallback;
- loading, empty va error state ko‘rinishlari;
- keyboard tab order, focus trap/restoration va Escape;
- desktop screenshot visual audit;
- tablet/mobile viewport va responsive audit;
- animatsiya hamda `prefers-reduced-motion` runtime xatti-harakati.

## Finding

### QA-ENV-01 — In-app browser runtime mavjud emas

- Severity: **high (release-verification blocker; product defect emas)**
- Route: barcha frontend route’lari, boshlang‘ich `http://127.0.0.1:5174/login`
- Reproduction:
  1. `browser-use` skillidagi setup tartibini tanlash.
  2. Tool katalogidan `node_repl js`, `mcp__node_repl__js`, `js` yoki “Node JavaScript execution”ni qidirish.
  3. Hech biri expose qilinmaganini kuzatish.
- Expected: `iab` browserga ulanib, fresh DOM snapshot asosida unique locatorlar bilan UI oqimlarini bajarish.
- Actual: browser runtimega ulanish mumkin emas; browser action bajarilmadi.
- Screenshot/DOM dalili: mavjud emas — blocker aynan screenshot va DOM snapshot olish qobiliyatini yo‘qqa chiqardi.
- Tavsiya: `mcp__node_repl__js` mavjud root/agent sessiyasida ushbu auditni qayta ishga tushirish; quyidagi tayyor sintetik fixture oqimini UI orqali takrorlash. Release gate uchun visual, responsive va accessibility bandlari pass bo‘lmaguncha browser QAni yakunlangan deb belgilamaslik.

## O‘tgan runtime/API oqimlari

Quyidagi natijalar backend kontrakti va frontend uchun zarur data mavjudligini tasdiqlaydi; ular UI interaction passini anglatmaydi.

| Oqim | Dalil | Natija |
|---|---|---|
| Health | `GET /health` | `200` |
| Bootstrap | `POST /api/v1/auth/bootstrap` | `201` |
| Owner register/login/me | `POST /auth/register`, `POST /auth/login`, `GET /auth/me` | `201/200/200` |
| Methodology/version/licence/publish | Registry POST endpointlari | `201/201/201/200` |
| Retention | `POST/GET /api/v1/retention-policies` | `201/200` |
| Research create/activate/list | `/researches` va `/researches/{id}/activate` | `201/200/200` |
| Participant/consent | participant va consent POST endpointlari | `201` |
| PII save/reveal/delete | `PUT/GET/DELETE .../pii` | `200/200/204` |
| Manual response | `POST .../responses` | `201` |
| Validate | `POST /responses/{id}/validate` | `200` |
| Calculate | `POST /researches/{id}/calculations` | `200` |
| CSV preview/confirm | `/imports/preview`, `/imports/{id}/confirm` | `201/200` |
| Results list/detail | `GET /results`, `GET /results/{id}` | `200/200` |
| Trace/disclaimer | result detail | 15 trace step; `uz-Latn`: “Bu natija tibbiy tashxis emas.” |
| JSON export | `GET /results/{id}/export?format=json` | `200`, attachment, `application/json`, 4346 byte |
| CSV export | `GET /results/{id}/export?format=csv` | `200`, attachment, `text/csv; charset=utf-8`, 579 byte |
| Methodology screen API | `GET /methodologies` | `200` |
| Team screen API | `GET /organizations/current/members` | `200` |
| Audit screen API | `GET /audit-events` | `200` |

Sintetik fixture yakunida 3 participant, 2 response (manual va CSV), 1 calculated result, shifrlangan PII reveal uchun 2 field va alohida PII delete holati yaratildi.

## Route bo‘yicha browser status

| Talab qilingan UI qamrovi | API/runtime tayyorligi | Browser holati |
|---|---|---|
| `/login` | login API `200`; HTML `200` | Blocked |
| `/researches`, `/researches/new` | create/list `201/200` | Blocked |
| `/researches/{id}` workbench | active research mavjud | Blocked |
| `/researches/{id}/participants`, participant detail | participant, consent va PII fixture mavjud | Blocked |
| `/researches/{id}/responses`, `/responses/{id}` | manual response + validated revision mavjud | Blocked |
| `/researches/{id}/import` | preview/confirm o‘tdi | Blocked |
| `/results`, `/results/{id}` | list/detail/trace/disclaimer/export o‘tdi | Blocked |
| `/methodologies`, `/registry` | published synthetic methodology mavjud | Blocked |
| `/team` | members API `200` | Blocked |
| `/audit` | audit API `200` | Blocked |

## Release xulosasi

Backend va frontend serving qatlami sintetik E2E fixture bilan ishladi; kerakli screen APIlarida 5xx yoki kontrakt uzilishi kuzatilmadi. Ammo browser interaction, visual, responsive va accessibility tekshiruvlari bajarilmagan. Shu sabab bu bosqich uchun yakuniy release qarori: **browser QA pending**.

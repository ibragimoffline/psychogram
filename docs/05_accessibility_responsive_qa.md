# Psychogram frontend: accessibility, responsive va motion QA

## 1. Audit xulosasi

**Holat: release gate — FAIL.** Production build va mavjud 17 unit/integration test o'tadi, lekin WCAG 2.2 AA va `03_ux_design_spec.md`ning 14-bo'limi uchun 4 ta yuqori, 8 ta o'rta va 2 ta past darajali topilma bor. Eng katta risklar 721–1100 px tablet railidagi nomsiz boshqaruvlar, form xatolarini tuzatish marshrutining yo'qligi, mobile table kontekstining yo'qolishi va PII o'chirish `alertdialog`ining fokus modelidir.

Bu audit production kodni o'zgartirmadi. Tekshirilgan manbalar: `docs/03_ux_design_spec.md`, `frontend/index.html`, `frontend/package.json`, `frontend/README.md`, `frontend/src/**` va mavjud testlar.

### Avtomatlashtirilgan tekshiruv

| Tekshiruv | Natija | Dalil |
| --- | --- | --- |
| Vitest | PASS — 6 file, 17/17 test | `npm.cmd test`, jumladan Drawer focus/Escape/restore va PII permission/delete oqimi |
| TypeScript + Vite production build | PASS — 506 modul | `npm.cmd run build`; JS 141.27 kB gzip, CSS 5.82 kB gzip |
| Axe/Lighthouse | NOT RUN | `package.json`/lock'da `axe-core`, `jest-axe`, Playwright yoki Lighthouse dependency/script yo'q |
| Kontrast | STATIC CALCULATED | WCAG sRGB relative-luminance formulasi, 8-bo'limdagi matrix |
| Real screen reader, 200% zoom, 320 px browser reflow | NOT RUN | alohida browser/AT sessiyasi kerak; statik kod risklari quyida release-fail sifatida qayd etildi |

Severity ta'rifi: **High** — asosiy vazifa yoki maxfiy/destructive oqimni AT/keyboard foydalanuvchisi mustaqil bajara olmaydi; **Medium** — sezilarli accessibility/responsive buzilish yoki release talabi bajarilmagan; **Low** — polish/deployment assurance kamchiligi.

## 2. Topilmalar

### A11Y-01 — High — tablet rail boshqaruvlari accessible nomsiz, tenant switch esa yo'q

- **Dalil:** `frontend/src/styles.css:13` 1100 pxgacha `.rail nav a span` va `.rail-user .button span`ni `display:none` qiladi, `.tenant-select`ni butunlay yashiradi. `frontend/src/components/AppShell.tsx:23-24`da nav link nomi faqat shu yashirilgan `span`da; icon `frontend/src/components/RemoteIcon.tsx:6-7`da label berilmasa `aria-hidden=true`. Logout buttonda icon ham yo'q. Topbar tenant selector bermaydi (`AppShell.tsx:26`).
- **Ta'sir qiladigan muhit:** 721–1100 px; screen reader, speech/voice control, keyboard va ko'radigan touch foydalanuvchi.
- **Impact:** nav linklar va “Chiqish” accessible name'siz qoladi; sighted foydalanuvchida tooltip yo'q; tashkilotni almashtirish imkoni yo'q. Bu tenant konteksti xatosi xavfini oshiradi.
- **Aniq fix:** har `NavLink`/logoutga doimiy `aria-label` bering, matnni `display:none` emas `.visually-hidden` bilan ATda saqlang va hover/focus tooltip qo'shing. Tablet topbar yoki accessible Drawer ichiga tenant selectorni ko'chiring. 721, 768, 1024 va 1100 pxda accessible-name va tenant-switch test yozing.

### A11Y-02 — High — server form xatolari ErrorSummary va field association bermaydi

- **Dalil:** umumiy `Notice` faqat `role="alert"` beradi (`frontend/src/components/UI.tsx:9`); `Field` hint/error ID, `aria-describedby` yoki `aria-invalid` yaratmaydi (`UI.tsx:21`). Login, research create, participant, consent, response, registry va import submit xatolari bitta global Notice sifatida chiqariladi (`AuthPages.tsx:12,17,22`; `ResearchPages.tsx:18`; `ParticipantPages.tsx:18,32`; `ResponsePages.tsx:20,32`; `AdminPages.tsx:15,20,36`; `ResultImportPages.tsx:16`). Submitdan keyin fokus summaryga yoki birinchi xato maydoniga o'tmaydi.
- **Ta'sir qiladigan muhit:** barcha viewportlar; screen reader, keyboard, cognitive disability.
- **Impact:** foydalanuvchi qaysi maydonni tuzatishni va xato bilan maydon orasidagi bog'lanishni topa olmaydi. Uzun manual instrument/registry formida vazifa amalda bloklanadi.
- **Aniq fix:** backend field issue'larini normalizatsiya qiladigan `ErrorSummary` yarating (`role="alert"`, `tabIndex={-1}`, submit faildan so'ng `.focus()`); har xatoni `href="#field-id"` qiling. `Field`ga stable input/hint/error ID, `aria-invalid` va birlashtirilgan `aria-describedby` qo'shing; link aktiv bo'lganda maydonga fokus borsin. Auth → manual entry → validate oqimini faqat keyboard va SR bilan test qiling.

### A11Y-03 — High — mobile table transform ustun kontekstini yo'qotadi

- **Dalil:** `frontend/src/styles.css:14` 720 pxgacha `table`, `thead`, `tbody`, `tr`, `th`, `td`ni `display:block` qiladi va `thead`ni clip bilan yashiradi. Celllarda `data-label`, row `dl` yoki takroriy visible label yo'q (`ParticipantPages.tsx:18`, `ResponsePages.tsx:11`, `AdminPages.tsx:15`, `ResultImportPages.tsx:16`). Masalan, “Faol / Rozilik berilgan / Mavjud / sana” qiymatlarining Processing, Consent yoki PII ekanini sighted mobile foydalanuvchi aniqlay olmaydi.
- **Ta'sir qiladigan muhit:** 320–720 px va 200% zoom reflow; sighted mobile, low vision, VoiceOver/Safari table semantics.
- **Impact:** qatordagi status va sanalar kontekstsiz; CSS table display override ayrim browser/AT kombinatsiyalarida table semantikasini ham zaiflashtiradi.
- **Aniq fix:** mobile uchun alohida `ResponsiveDataView`/stacked `<dl>` record render qiling yoki har cellga visible label qo'shing; desktop native `<table>`ni saqlang. Action headerga “Amal” accessible nomi bering. 320, 360 va 400 pxda participant/response/import error recordlarni tekshiring.

### A11Y-04 — High — PII delete `alertdialog` dialog keyboard modeliga ega emas

- **Dalil:** `frontend/src/pages/ParticipantPages.tsx:32` inline `role="alertdialog" aria-label=...` yaratadi, lekin fokusni “Ha...” yoki “Bekor qilish”ga ko'chirmaydi, fokus trap, Escape cancel va openerga restore yo'q. Drawer uchun bular to'g'ri implement qilingan va testlangan (`frontend/src/components/UI.tsx:14-20`, `Drawer.test.tsx:11-13`), delete confirmation esa shu primitive'dan foydalanmaydi.
- **Ta'sir qiladigan muhit:** barcha viewportlar; keyboard va screen reader; destructive PII oqimi.
- **Impact:** dialog paydo bo'lgani/qaror talab qilinayotgani ishonchli anglashilmaydi, fokus ortdagi PII formda qoladi; maxfiy destructive action uchun noto'g'ri target xavfi bor.
- **Aniq fix:** reusable `ConfirmAction` alertdialog yarating: `aria-labelledby` + `aria-describedby`, initial fokus “Bekor qilish”da, Tab trap, Escape faqat cancel, close'da opener restore; background inert. PII delete testiga focus, Shift+Tab, Escape va restore assertionlarini qo'shing.

### A11Y-05 — Medium — PII ochilgach qayta maskalash/tozalash amali yo'q

- **Dalil:** `ParticipantPages.tsx:28-30` reveal/save'dan keyin `showPii=true` va plaintext `pii` state'da qoladi; `ParticipantPages.tsx:32` revealed branch faqat save/delete beradi, “Yashirish” yo'q. Plaintext faqat delete yoki route unmountda tozalanadi.
- **Ta'sir qiladigan muhit:** barcha viewportlar; shared-screen/privacy foydalanuvchilari.
- **Impact:** explicit reveal to'g'ri va permission bo'lmasa endpoint umuman chaqirilmaydi (test PASS), ammo shoulder-surfing riskini tez yopish imkoni yo'q.
- **Aniq fix:** “PIIni yashirish” control qo'shib `setShowPii(false); setPii(null); setConfirmDelete(false)` qiling; tenant/logout/route cleanupni test qiling. Browser title, URL va announcementda qiymat ishlatilmasin.

### A11Y-06 — Medium — ko'p interactive target 44×44 minimumdan kichik

- **Dalil:** `.button` va form control minimumi 42 px (`frontend/src/styles.css:4,7`); `.back-link` faqat 4 px padding (`styles.css:8`); table “Ochish”, auth links va trace `<summary>` uchun 44 px target belgilanmagan (`ParticipantPages.tsx:18`, `ResponsePages.tsx:11`, `AuthPages.tsx:12`, `ResultImportPages.tsx:28`). Faqat `.choice` 44 px va mobile bottom nav 48 px (`styles.css:7,14`).
- **Ta'sir qiladigan muhit:** touch/coarse pointer, ayniqsa 320–767 px; motor impairment.
- **Impact:** frequent actions UX spesifikatsiyasidagi ≥44 px va 8 px adjacent spacing talabini bajarmaydi.
- **Aniq fix:** touch breakpointda barcha button/input/select/textarea/link-action va summary uchun `min-block-size:44px`; inline table actionsga padded action class; back linkga kamida 44×44 hitbox. `pointer:coarse` testida computed rectlarni assert qiling.

### RESP-01 — Medium — breakpointlar tasdiqlangan blueprint bilan mos emas

- **Dalil:** UX mobile 360–767 va tablet 768–1199 deb belgilaydi (`docs/03_ux_design_spec.md:78-92`); CSS esa 1100 va 720dan kesadi (`frontend/src/styles.css:13-14`). Natijada 721–767 pxda mobile bottom nav yo'q va compact rail qoladi; 1101–1199 pxda 248 px rail qoladi. Tablet tenant topbari/accessible tooltip ham implement qilinmagan.
- **Ta'sir qiladigan muhit:** 721–767 va 1101–1199 px; zoom natijasidagi shu effective widthlar.
- **Impact:** layout/navigation spesifikatsiyadan boshqa rejimga tushadi va mavjud A11Y-01ni kengaytiradi.
- **Aniq fix:** breakpoint tokenlarini 768/1200 chegaralariga moslang yoki dizayn hujjatini dalil bilan qayta tasdiqlang; 767/768 va 1199/1200 boundary screenshot + keyboard regression qo'shing.

### A11Y-07 — Medium — standalone Natijalar route'ida `h1` yo'q va SPA route focus boshqarilmaydi

- **Dalil:** `/results` `AppShell` ostida mustaqil route (`frontend/src/App.tsx:13`), lekin `ResultsPage` faqat `<h2>` beradi (`ResultImportPages.tsx:21`). `Page` h1 yaratadi (`UI.tsx:12`), bu screen undan foydalanmaydi. Route change'da yangi h1/main'ga fokus o'tkazuvchi hook yo'q (`AppShell.tsx:15-29`).
- **Ta'sir qiladigan muhit:** global `/results`; screen reader va keyboard SPA navigatsiyasi.
- **Impact:** “har route h1” acceptance buziladi; navigatsiyadan so'ng fokus eski linkda qolib, yangi sahifa e'lon qilinmasligi mumkin.
- **Aniq fix:** standalone `ResultsPage`ni `Page` bilan o'rang yoki route mode bo'yicha h1 bering. Location change'da main/h1ni `tabIndex={-1}` bilan fokuslang (hash/deep-link va user form focusini buzmasdan) va document title yangilang.

### A11Y-08 — Medium — import/file async statuslari ishonchli live modelga ega emas

- **Dalil:** `Notice` har bir info/warning/privacy blokka ham `role="status"` beradi (`UI.tsx:9`), shuning uchun statik sahifa izohlari live region sifatida ortiqcha announce bo'lishi mumkin. Import busy holati faqat focused button textini almashtiradi; preview ledger `aria-label`li oddiy `div`, `aria-live`/`aria-busy` yo'q (`ResultImportPages.tsx:16`).
- **Ta'sir qiladigan muhit:** import va boshqa async form oqimlari; screen reader.
- **Impact:** statik noticelar shovqin qiladi, muhim “server tekshiryapti / preview tayyor / confirm tugadi” transitioni esa kafolatli e'lon qilinmaydi.
- **Aniq fix:** statik `Notice`dan live role'ni olib, faqat state transition uchun alohida `LiveStatus aria-live="polite" aria-atomic="true"` ishlating; blocking error `role=alert` bo'lib qolsin. Import containerga `aria-busy`, processingga text+spinner status, preview summaryga bitta atomic announcement bering.

### A11Y-09 — Medium — file dropzone keyboard fokus indikatori ko'rinmaydi

- **Dalil:** file input opacity 0 va absolute, `pointer-events:none` (`frontend/src/styles.css:10`). Keyboard focus inputga tushadi, lekin global `:focus-visible` outline aynan ko'rinmas inputda chiziladi; label/dropzone uchun `:focus-within` style yo'q. Input label orqali nomlangan (`ResultImportPages.tsx:16`), shuning uchun accessible name bor.
- **Ta'sir qiladigan muhit:** barcha viewportlar; keyboard va low vision.
- **Impact:** foydalanuvchi file picker triggerida fokus qayerdaligini ko'rmaydi.
- **Aniq fix:** `.dropzone:focus-within { outline:3px solid var(--focus); outline-offset:2px; }`; inputni visually-hidden reusable class bilan yashiring, focusabilityni saqlang. Keyboard Enter/Space va visible focus test qo'shing.

### MOTION-01 — Medium — reduced-motion trace reveal hali default Motion animatsiyasiga tayanadi

- **Dalil:** route va Drawer `useReducedMotion` bilan translate'ni olib tashlab 80 ms opacity beradi (`UI.tsx:12,15-19`), CSS spinner/transitionsni deyarli instant qiladi (`styles.css:15`). Ammo trace `<motion.ol>` reduced holatda ham `initial={{opacity:0}} → animate={{opacity:1}}` qiladi va explicit transition yo'q (`ResultImportPages.tsx:25,28`); Motion default duration ishlaydi.
- **Ta'sir qiladigan muhit:** `prefers-reduced-motion: reduce`; vestibular/cognitive sensitivity.
- **Impact:** barcha non-essential movement/transition ≤80 ms bo'lishi isbotlanmagan. Trace normal mode duration ham 220 ms tokeniga explicit bog'lanmagan.
- **Aniq fix:** reduced holatda `initial={false}` yoki `{opacity:1}` qiling; normalda `transition={{duration:.22}}`, reducedda 0/.08. Testda `useReducedMotion=true` uchun trace style/transitionni assert qiling.

### COLOR-01 — Medium — tenant selector resting boundary 3:1ga yetmaydi

- **Dalil:** rail `#112A26`, select background `#1B3933`, border `#49635C` (`frontend/src/styles.css:3`). Hisob: border/rail **2.33:1**, border/select background **1.92:1**, select background/rail **1.21:1**. Label va native arrow yordam beradi, focus ring railga **3.07:1** bilan o'tadi, lekin resting control boundary 1.4.11 uchun zaif.
- **Ta'sir qiladigan muhit:** desktop rail; low vision/contrast sensitivity.
- **Impact:** tenant switchning chegarasi va interaktivligi past kontrastda yo'qolishi mumkin.
- **Aniq fix:** border yoki backgroundni shunday almashtiringki boundary rail va control ichki foniga nisbatan kamida 3:1 bo'lsin; hover/focus/disabled state'larni qayta hisoblang.

### A11Y-10 — Low — disabled control sababi va readability izchil emas

- **Dalil:** `.button:disabled{opacity:.55}` (`styles.css:4`). Canvasda blended primary disabled contrast taxminan **2.55:1**, surfacedagi **2.49:1**; danger mos ravishda **2.70/2.65:1**. Inactive controls WCAG text/non-text contrastdan istisno, lekin UX spesifikatsiyasi disabled action sababini visible qilishni talab qiladi. Research create va registry buttonlari ko'pincha faqat disabled (`ResearchPages.tsx:18`, `AdminPages.tsx:44`).
- **Ta'sir qiladigan muhit:** barcha viewportlar; low vision va cognitive users.
- **Impact:** “nima uchun davom etib bo'lmaydi” har doim aniq emas; past opacity matn o'qilishini yomonlashtiradi.
- **Aniq fix:** opacity bilan butun controlni pasaytirmang; accessible dark disabled text/background token bering va har domain-disabled action yonida sabab + keyingi qadamni ko'rsating. Native `disabled` sabab focus kerak bo'lsa, focusable explanatory wrapper ishlating.

### DEPLOY-01 — Low — CSP faqat hujjatlashtirilgan, buildda enforcement dalili yo'q

- **Dalil:** Iconify URL/fixed size/referrer/fallback to'g'ri (`RemoteIcon.tsx:3-8`) va fontlar local package import (`main.tsx:4-6`). Ammo `index.html:3-9`da CSP meta yo'q, Vite config CSP header bermaydi; siyosat faqat `frontend/README.md:23-31`da deployment ko'rsatmasi.
- **Ta'sir qiladigan muhit:** production deployment.
- **Impact:** acceptance'dagi “CSP ishlaydi” repo ichidan PASS deb tasdiqlanmaydi; noto'g'ri server config iconlarni bloklashi yoki siyosatni umuman qo'llamasligi mumkin.
- **Aniq fix:** deploy server/IaCda CSP headerni version-control qiling va production smoke testda response header hamda Iconify allowlistni assert qiling. Meta CSP `frame-ancestors` o'rnini bosmaydi.

## 3. PASS bo'lgan dalillar

- Landmarks: authenticated shell'da skip link birinchi fokus elementi, `aside`, nomlangan navlar, `header` va `main#main` bor (`AppShell.tsx:18-27`). Auth sahifalari bitta `main` va h1 beradi (`AuthPages.tsx:24`).
- Formlarning asosiy accessible name'i wrapping `<label>`/`fieldset`/`legend` bilan berilgan (`UI.tsx:21`, `ResponsePages.tsx:22`); native required/type/pattern constraintlar ishlaydi.
- Drawer initial focus, Tab/Shift+Tab trap, Escape va opener restore implement qilingan hamda testdan o'tgan (`UI.tsx:14-20`, `Drawer.test.tsx:12`).
- Status rangga yolg'iz tayanmaydi: dot bilan birga human-readable text bor (`UI.tsx:7-8`), test mavjud (`UI.test.tsx:6`). Notice icon + title + matn beradi.
- PII permission bo'lmasa endpoint chaqirilmaydi va plaintext DOMga kelmaydi; explicit reveal va ikki bosqichli delete functional testi o'tadi (`flows.test.tsx:49-54`). PII/score/consent/licence count-up yoki dramatik animatsiya yo'q.
- Table desktopda native `<table>/<thead>/<tbody>/<th>`; wide context/provenance/tabs o'z regionida `overflow:auto`, `safe-json` wrap+scroll qiladi (`styles.css:7-10`).
- Motion route 6 px/220 ms, Drawer 30 px/220 ms va scrim 160 ms; CSS hover 80/140 ms tokenlarga yaqin. CSS reduced-motion spinner va transitionlarni instant qiladi (`UI.tsx:12,18-19`, `styles.css:4,6,10,15`).
- Source Sans 3, Newsreader va IBM Plex Mono local bundle; remote font/CDN yo'q (`main.tsx:4-6`, build asset list). Quiet Instrument tokenlari canvas/spruce/teal/copper, kam radius, divider density va overlay-only shadow bilan implement qilingan (`styles.css:1-12`).

## 4. Kontrast matrixi

Normal text threshold 4.5:1; large text/UI/non-text threshold 3.0:1. Qiymatlar actual CSS HEXlardan qayta hisoblandi.

| Pair | Ratio | Talab/status | Izoh |
| --- | ---: | --- | --- |
| ink-strong `#17231F` / canvas `#F4F1E8` | 14.34 | PASS text | body/root |
| ink `#34443F` / canvas | 9.09 | PASS text | secondary body |
| ink-muted `#5A6964` / canvas | 5.11 | PASS text | 12 px metadata ham 4.5dan yuqori |
| ink-muted / surface `#FFFEFA` | 5.72 | PASS text | field hints/table headers |
| primary `#176B5B` / surface | 6.32 | PASS text | links/quiet controls |
| primary / canvas | 5.65 | PASS text | links |
| white / primary | 6.38 | PASS text | primary button |
| white / danger `#9A3741` | 7.01 | PASS text | danger button |
| copper `#A84F2A` / surface | 5.45 | PASS text | eyebrow/data accent |
| copper / canvas | 4.87 | PASS text | eyebrow |
| ink / primary-soft `#D8E9E2` | 8.15 | PASS text | selected row |
| info dark / info-soft | 9.20 | PASS text | notice |
| warning dark / warning-soft | 7.34 | PASS text | notice |
| danger dark / danger-soft | 7.71 | PASS text | notice |
| success dark / success-soft | 7.53 | PASS text | notice |
| privacy dark / privacy-soft | 8.26 | PASS text | PII zone |
| rail text `#F8F5ED` / rail `#112A26` | 13.94 | PASS text | rail |
| rail muted `#C8D4CF` / rail | 9.96 | PASS text | nav |
| active marker `#E7A16F` / active bg `#23483F` | 4.70 | PASS UI/text | selected nav |
| focus `#0B78A6` / canvas | 4.37 | PASS UI | 3 px ring |
| focus / surface | 4.89 | PASS UI | 3 px ring |
| focus / rail | 3.07 | PASS UI, marginal | 3 px ring |
| line-strong `#86948E` / surface | 3.13 | PASS UI | input interior boundary |
| line-strong / canvas | 2.80 | contextual risk | control interior contrast passes; exterior alone <3 |
| line `#C9CEC6` / canvas | 1.42 | decorative only | divider meaningful bo'lsa 3:1 kerak |
| line / surface | 1.59 | decorative only | row/panel rule |
| tenant border `#49635C` / rail | 2.33 | **FAIL UI** | COLOR-01 |
| tenant border / select bg `#1B3933` | 1.92 | **FAIL UI** | COLOR-01 |
| disabled primary blended / canvas-surface | 2.55 / 2.49 | WCAG-exempt inactive | usability warning A11Y-10 |
| disabled danger blended / canvas-surface | 2.70 / 2.65 | WCAG-exempt inactive | usability warning A11Y-10 |

`line` low contrasti o'zi decorative separator bo'lsa failure emas; agar row/sectionni anglash uchun yagona cue bo'lsa 3:1ga ko'tarilishi kerak. Status dotlar success/danger/copper ranglari va visible matn bilan birga keladi, shuning uchun color-only failure yo'q.

## 5. Responsive/reflow matrixi

| Viewport/effective width | Statik natija | Release holati |
| --- | --- | --- |
| ≥1200 | 248 px fixed rail, minmax workspace, wide grid | Asosan PASS; tenant border contrast fix kerak |
| 1101–1199 | 248 px rail qoladi; UX tablet 72 px kutgan | FAIL blueprint |
| 768–1100 | 72 px rail va single-column workbench | FAIL nav accessible names/tenant switch |
| 721–767 | 72 px rail; mobile bottom nav yo'q | FAIL boundary/navigation |
| 360–720 | bottom nav, single-column forms; strips local-scroll | PARTIAL; table labels va 44 px targets fail |
| 320–359 | body 320 minimum, 14 px side padding | NOT VERIFIED browser; auth links nowrap va stacked content real reflow test talab qiladi |
| 200% zoom | effective widthga media query ishlaydi | NOT VERIFIED; yuqoridagi 721/720 boundary va mobile table risklari qoladi |

Page-level `min-width:320px` bor, `workspace{min-width:0}`, gridlarda `minmax(0,...)`, `overflow-wrap:anywhere` va local scroll regions katta gorizontal page overflow riskini kamaytiradi. Biroq real browserda 320 px, browser scrollbar, long Uzbek localization va 200% zoom bilan `documentElement.scrollWidth === clientWidth` assertioni hali yo'q.

## 6. UX 14-bo'lim acceptance mapping

### Functional va contract

| Acceptance | Holat | Dalil/izoh |
| --- | --- | --- |
| Authorization + tenant header; switch cache/reveal clear | PASS | `AuthContext.tsx:15-17`, `AppShell.tsx:22`; integration test PASS |
| Role nav/CTA; 403 authoritative | **FAIL** | desktop baseNav filter bor, lekin mobile “Ko'proq” doim `/team`; tablet names/tenant A11Y-01 |
| Asosiy backend schema exact | PARTIAL | mavjud flow tests create/import/result/PII qismini qoplaydi; bu audit barcha endpoint schema'ni qayta validatsiya qilmadi |
| Decimal score server string | PASS | `ResultImportPages.tsx:28` `score_display`ni to'g'ridan-to'g'ri chiqaradi |
| Calculate retry idempotency key saqlanadi | PASS | `ResponsePages.tsx:26,30`; key state'da va failda o'zgarmaydi |
| Confirm server preview_hash bilan | PASS | `ResultImportPages.tsx:14`; integration test PASS |
| Fake data/API yo'q gap state | PASS static | runtime fixture/fake datasource topilmadi |

### Privacy va safety

| Acceptance | Holat | Dalil/izoh |
| --- | --- | --- |
| Permission yo'q PII DOM/URL/log/clipboardga kirmaydi | PASS | `ParticipantPages.tsx:28,32`; negative endpoint-call test PASS |
| Encryption integratsiyasiz identified disabled | PARTIAL | backend PII integration mavjud va fail-closed; create UI config readinessni oldindan ko'rsatmaydi |
| Consent/licence/research gate bypass yo'q | PARTIAL | consent optionlari disabled va server authoritative; barcha lifecycle gate'lar bu auditda E2E qilinmadi |
| Result/export disclaimer visible | PASS UI | result note + disclaimer snapshot visible; eksport artifact kontenti server mas'uliyati |
| Trace disclosuredan ortiq emas | PARTIAL | UI server trace'ni aynan ko'rsatadi; server disclosure contracti bu audit doirasida qayta sinovdan o'tmadi |
| Sintetik demo selectable emas | PASS static | runtime demo catalog topilmadi |

### Visual va anti-template

| Acceptance | Holat | Dalil/izoh |
| --- | --- | --- |
| Generic hero/orb/glass/3-card yo'q | PASS | workbench/ledger composition |
| Divider/alignment/density hierarchy | PASS | `styles.css:7-10`; uniform card grid yo'q |
| Semantik palitra, moral score rang yo'q | PARTIAL | score dramatizatsiyasi yo'q; tenant boundary contrast COLOR-01 |
| External icon/fallback/fixed size/CSP | PARTIAL | Iconify implementation/test PASS; CSP deployment enforcement yo'q (DEPLOY-01) |
| Desktop/tablet/mobile blueprint | **FAIL** | RESP-01, A11Y-01, A11Y-03 |

### Accessibility va motion

| Acceptance | Holat | Dalil/izoh |
| --- | --- | --- |
| Axe critical yo'q + contrast matrix | **FAIL / UNVERIFIED** | axe yo'q; matrixda tenant control failure bor |
| Keyboard auth → entry → validate → result → trace | **FAIL** | core native controls ishlaydi, lekin tablet nav, error correction va PII alertdialog fail |
| 200% zoom, 320 reflow, touch targets | **FAIL / UNVERIFIED** | browser test yo'q; statik 42 px target va table/breakpoint failures bor |
| SR error summary, table, status, trace | **FAIL** | Status/trace text bor; ErrorSummary yo'q va mobile table labels yo'q |
| Reduced-motion barcha non-essential movementni o'chiradi | PARTIAL | CSS/Page/Drawer pass; trace default opacity animation MOTION-01 |
| Score/PII/consent/licence dramatizatsiyasi yo'q | PASS | count-up/morph/shake/parallax topilmadi |

## 7. Tavsiya etilgan tuzatish ketma-ketligi

1. A11Y-01, A11Y-02, A11Y-03 va A11Y-04ni release-blocker sifatida yoping.
2. PII remask, 44 px target, breakpoint va route heading/focusni yoping.
3. Live status, dropzone focus, reduced-motion trace va tenant contrastni tuzating.
4. `axe-core`/Playwright accessibility smoke test qo'shing; 320/360/720/721/767/768/1024/1100/1101/1199/1200 viewport matrixini avtomatlashtiring.
5. NVDA+Firefox yoki Chrome, VoiceOver+Safari, keyboard-only, 200% zoom va coarse touch bo'yicha manual regression o'tkazing; production CSP headerni smoke-test qiling.

**QA qarori:** build sog'lom va vizual yo'nalish spetsifikatsiyaga yaqin, ammo hozirgi holatda accessibility/responsive acceptance release uchun yopilmagan.

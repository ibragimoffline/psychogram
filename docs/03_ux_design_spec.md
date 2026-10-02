# Psychogram MVP: UX dizayn spetsifikatsiyasi

## 0. Maqsad, maqom va amalga oshirish chegarasi

Bu hujjat `01_product_scope.md`, `02_methodology_contract.md`, `README.md` va amaldagi FastAPI `/api/v1` kontrakti asosida UI subagent uchun implementatsiya spetsifikatsiyasidir. U frontend kodi emas. Bu bosqichda mavjud fayllar o'zgartirilmagan.

Mahsulotning asosiy metaforasi **research instrument / workbench**: professional foydalanuvchi ma'lumotni yig'adi, tekshiradi, hisoblaydi va kelib chiqishini isbotlaydi. Interfeys marketing sayti yoki “AI dashboard” emas; u sokin, zich, izchil va audit qilinadigan ish muhiti bo'lishi kerak.

Muhim kontrakt chegarasi: backend hozir create/action endpointlarining ko'pini beradi, ammo ayrim zarur query endpointlari yo'q. UI soxta data, production demo metodika yoki mavjud bo'lmagan API'ni ixtiro qilmaydi. 16-bo'limda tayyor, cheklangan va backend kengayishini talab qiladigan ekranlar ajratilgan.

## 1. UX prinsiplar

### 1.1. Asosiy prinsiplar

1. **Holat harakatdan oldin.** Research, consent, response, licence va revision holati CTA yonida ko'rinadi; bloklangan amal sabab va keyingi qadam bilan tushuntiriladi.
2. **Avval pseudonim.** Participant ro'yxati va natijada tashqi pseudonim kod asosiy identifikator. PII bo'lsa ham default yashirin, alohida hudud va huquq bilan ochiladi.
3. **Tasdiqdan oldin preview.** Import, activation, hisoblash va eksportda foydalanuvchi oqibatni ko'radi; irreversible yoki audit qilinadigan amal tasodifan bajarilmaydi.
4. **Izoh natijaning qismi.** “Qanday hisoblandi?” yordamchi modal emas; natijaning birinchi darajali, deep-link qilinadigan ikkinchi ko'rinishi.
5. **Kontekst yo'qolmaydi.** Har doim faol tashkilot, research, metodika versiyasi va rol ko'rinadi. Tenant almashtirish navigatsiyani xavfsiz qayta yuklaydi.
6. **Xato — tuzatish marshruti.** Har bir xabar `nima bo'ldi → nimaga ta'sir qildi → qanday tuzatiladi` shaklida. Raw PII va javob xato telemetry yoki toastga tushmaydi.
7. **Zichlik boshqariladi.** Overview'da xulosa, workbench'da jadval va inspector; foydalanuvchi bir xil yumaloq kartalar dengiziga majbur qilinmaydi.
8. **Rang semantik va kam.** Rang navigatsiya, holat, maxfiylik chegarasi va feedback uchun; dekorativ gradient yoki “glow” uchun emas.
9. **Motion sababli.** Animatsiya spatial o'zgarish, progress va trace ketma-ketligini anglatadi. Ball, validity yoki ogohlantirishni dramatizatsiya qilmaydi.
10. **Auditga mos aniqlik.** “Saqlandi”, “valid”, “hisoblandi” faqat server tasdiqlagach aytiladi. Optimistik UI domain statuslarida ishlatilmaydi.

### 1.2. Qat'iy anti-patternlar

- Generic gradient hero, yaltiragan orb, glassmorphism, ortiqcha blur va neon ishlatilmaydi.
- “3 ta bir xil feature card”, katta bo'sh dashboard, barcha bloklarga 20–24 px radius berish yo'q.
- Chatbot, sparkles, “AI insight”, uydirma tavsiya yoki generativ klinik matn yo'q.
- Ballni speedometer/gauge bilan “yaxshi–yomon” dramatizatsiya qilish yo'q; metodika buni belgilamasa qizil/yashil moral baho berilmaydi.
- Skeletonni haqiqiy qiymatga o'xshatib, PII yoki natijani miltillatish yo'q.
- Faqat rang bilan holat ajratilmaydi; label va ikon ham bor.
- Disabled tugma izohsiz qolmaydi. Zarur bo'lsa trigger focusable bo'lib, sababni ochadi.
- Toast muhim validatsiya yoki consent/licence gate uchun yagona xabar bo'lmaydi.
- Modal ichida uzoq form, nested modal, hover-only action, icon-only noaniq CTA yo'q.
- Sintetik fixture katalogda production metodika sifatida ko'rsatilmaydi; fixture topilsa “Faqat test muhiti” belgisi bilan katalog tanlovidan chiqariladi.

## 2. Persona va role asosidagi jobs-to-be-done

| Persona / rol | Asosiy JTBD | Muvaffaqiyat signali | UX himoyasi |
| --- | --- | --- | --- |
| Tashkilot egasi/admini | Jamoa, retention, PII huquqi va research readiness'ni boshqarish | Kim nimaga kira olishi va nimasi bloklanganini 1 ko'rishda biladi | PII ruxsatini roldan alohida; xavfli amal uchun sabab va audit preview |
| Tadqiqotchi/psixolog | Yaroqli metodika bilan research yaratish, valid javobni hisoblash, natijani izohlash | Natija qaysi revision/versiyadan chiqqani isbotlanadi | Licence/consent gate, immutable provenance, non-diagnostic disclaimer |
| Operator | Participant, consent va javoblarni tez, xatosiz qo'lda yoki CSV orqali kiritish | Xato qatori/maydoni va tuzatish yo'li aniq | Sticky progress, inline error summary, PII masking, autosave faqat draft uchun |
| Auditor | Hodisalar va natija provenance'ini o'zgartirmasdan tekshirish | Actor, vaqt, obyekt, natija va reason topiladi | Read-only shell, raw answers/PII auditda yo'q, filter holati saqlanadi |
| Platform administrator | Metodika, versiya, licence va publish gate'ni boshqarish | Noto'liq/yaroqsiz kontent publish bo'lmaydi | Tenant PII'dan ajratilgan global registry shell, reason-required publish |
| Ko'p tashkilot a'zosi | Faol tenantni xatosiz almashtirish | Qaysi tenantda ishlayotgani doim ravshan | Persistent tenant switcher, switch paytida draft guard, cache/query reset |

Ishtirokchi MVP foydalanuvchisi emas; participant-facing portal va self-service oqimi chizilmaydi.

## 3. Axborot arxitekturasi va navigatsiya

### 3.1. Global IA

```text
Auth
├─ Kirish
├─ Tashkilot yaratish (owner registration)
└─ Platformani bootstrap qilish (faqat bo'sh instance/admin)

Tenant workbench
├─ Tadqiqotlar
│  ├─ Research overview
│  ├─ Ishtirokchilar va consent
│  ├─ Javoblar: qo'lda / import
│  └─ Natijalar / hisoblash izi
├─ Metodikalar katalogi (read-only tanlov)
├─ Jamoa (owner/admin)
├─ Retention siyosatlari (owner/admin)
└─ Audit (owner/admin/auditor)

Platform registry (platform admin)
├─ Metodikalar
├─ Versiyalar va snapshot
├─ Licence revision
└─ Publish gate
```

### 3.2. Desktop shell, ≥1200 px

- 248 px chap “rail”: yuqorida wordmark, uning ostida faol tashkilot selector, keyin role-filterlangan navigation. Pastda user/rol va session menyusi.
- 1 px vertical divider; sidebar `surface-ink`, content `canvas`.
- Yuqori content bar 56 px: breadcrumb, research holati, command/search joyi; global marketing header yo'q.
- Asosiy maydon max-width bilan sun'iy toraytirilmaydi: form 760 px, result 1180 px, data grid mavjud kenglikdan foydalanadi.
- Detail/workbench ekranida 12-column grid: asosiy 8–9 column, sticky context inspector 3–4 column.

### 3.3. Tablet, 768–1199 px

- Rail 72 px icon + accessible tooltip holatiga qisqaradi; tenant nomi top bar'da.
- Inspector inline accordion yoki 320 px dismissible drawerga o'tadi.
- Jadval ustunlari prioritet asosida yashiriladi; column chooser mavjud, horizontal scroll so'nggi chora.

### 3.4. Mobile, 360–767 px

- Bu native app emas, lekin operatorning qisqa vazifalari ishlaydi.
- Top app bar: menu, research qisqa nomi, status. Bottom bar faqat 4 asosiy destination: Research, Kiritish, Natija, Ko'proq.
- Data grid stacked record listga aylanadi; har recordda pseudonim kod, status, sana va bitta primary action.
- Uzun manual instrumentda sticky `Oldingi / Keyingi` va bo'lim progressi; raqamli keyboard uchun inputmode.
- Platform registry snapshot authoring va katta import error tahlili mobil ekranda read-only/“desktop tavsiya etiladi”; asosiy ish bloklanmasdan sabab beriladi.

## 4. End-to-end task flowlar

### F0 — Login, bootstrap va tenant konteksti

1. `/login`: email + parol; submitdan keyin server javobi kutiladi.
2. Token olinsa `/auth/me`; bitta membership bo'lsa tenant avtomatik tanlanadi, bir nechta bo'lsa tashkilot chooser.
3. Har tenant requestga `X-Organization-ID`; switch bo'lsa barcha tenant query cache, selection va PII reveal state tozalanadi.
4. Membership bo'lmasa access recovery state; platform admin uchun registry shell.
5. Bo'sh instance bootstrap oddiy login ekranida reklama qilinmaydi; deployment operator ochadigan `/setup/bootstrap`, bootstrap token va “faqat bir marta” izohi bilan.
6. Owner registration `/register` orqali organization yaratadi; code format live tekshiriladi, ammo unique natija faqat serverdan keyin aytiladi.

### F1 — Research yaratish va faollashtirish

1. Research ro'yxatidan `Yangi tadqiqot`.
2. Step 1: nom, maqsad, use type.
3. Step 2: methodology/version picker; faqat published + verified + kontekstga mos variant tanlanadi. Backend query gap tufayli version picker implementatsiyasi 16-bo'limdagi B01/B02'ga bog'liq.
4. Step 3: PII mode. Default `pseudonymous`; `identified` hozir `PII_STORAGE_NOT_CONFIGURED` sabab disabled va aniq izohli. `anonymous` tanlansa bevosita PII yig'ilmasligi ko'rsatiladi.
5. Step 4: consent reference/version va retention policy.
6. Review: metodika versiyasi, privacy, retention va immutable-after-activation ogohlantirishi.
7. `Draft yaratish`; server successdan keyin overview. Amaldagi API researchni `draft` yaratadi.
8. `Faollashtirish` bosilganda readiness checklist; POST activate. Xato bo'lsa gate panel aynan reason code bo'yicha ochiladi.

### F2 — Participant, consent va manual response

1. Research Active ekanini tekshirish; boshqa statusda entry CTA bloklanadi.
2. `Ishtirokchi qo'shish`: external code. Anonymous/pseudonymous zonada PII maydon yo'q; identified backend tayyor bo'lmaguncha unavailable.
3. Participant yaratilgach darhol consent step: status, reference, version, obtained date/time; `not_required_with_basis`da basis shart.
4. Consent `granted` yoki tasdiqlangan basis bo'lmasa response form ochilmaydi; record saqlanishi mumkin, processing blok holatda.
5. Manual response: instrument bo'limlarga ajratiladi, savol code yordamchi, prompt licence disclosure'ga mos. Draft `finalize=false`; final submit `finalize=true`.
6. Frontend constraintlari tez feedback beradi, lekin server validation canonical. POST validate natijasi `validation_failed` bo'lsa summary fokuslanadi va birinchi xato maydoniga link beradi.
7. Validated revision researcher roli uchun `Natijani hisoblash` CTA; operatorga “Tadqiqotchi hisoblashi kerak” read-only status.
8. Hisoblash requestiga UUID idempotency key clientda bir logical action uchun bir marta yaratiladi; retry shu keyni qayta ishlatadi.
9. Success result ID bilan result sahifasiga o'tadi; double-submit yangi natija yaratmaydi.

### F3 — CSV preview va confirm

1. Import ekranida tanlangan research/metodika/version qat'iy ko'rinadi. Amaldagi backend fayl upload emas, UTF-8 CSV text qabul qiladi; UI file'ni browserda text sifatida o'qib `csv_text` yuboradi.
2. Dropzone `.csv`ni qabul qiladi; type/size client check faqat erta feedback. XLSX MVPda “Qo'llab-quvvatlanmaydi”.
3. File browserda o'qilgach raw kontent UI/logda qayta aks ettirilmaydi; faqat fayl nomi, byte va lokal qator soni.
4. `Tekshirish` → preview endpoint. Processing animation progressni taxminiy foiz sifatida ko'rsatmaydi; indeterminate “Server tekshiryapti”.
5. Preview: jami/valid/invalid/duplicate counters, xatolar data grid'i, PII mask. Fatal header/file error bo'lsa confirm yo'q.
6. Valid row bo'lsa `Yaroqli N qatorni saqlash`; modal emas, sticky confirmation bar. Invalid rowlar saqlanmasligi aniq.
7. Confirm aynan `preview_hash` bilan. Hash mismatch/stale preview bo'lsa faylni qayta tekshirish taklif qilinadi.
8. Success summary server sonlari bilan; UI importni “hammasi saqlandi” demaydi, `summary`ni ko'rsatadi.

### F4 — Result va “Qanday hisoblandi?”

1. Result header: participant pseudonim, result status, calculated time; methodology/revision/result hash provenance strip.
2. Birinchi qatlam: scale natijalari, unit, validity, answered/missing va oldindan yozilgan interpretation. Score band rangsiz ham tushunarli label bilan.
3. “Bu natija tibbiy tashxis emas” contextual note doim visible; 7-bo'limdagi copy ishlatiladi.
4. `Qanday hisoblandi?` tab/anchor ikkinchi qatlamni ochadi: pipeline summary, disclosure level, reason codes.
5. Scale tanlansa shu scale trace filterlanadi. Step ochilganda input/output/rule ko'rinadi; redacted qiymatga “Litsenziya darajasi sabab yashirilgan” izohi.
6. `summary_only`da item step uchun bo'sh placeholder emas — scale-level tushuntirish beriladi. `derived_only`da raw answer/prompt ko'rsatilmaydi.
7. Invalid/insufficient scale uchun talqin o'rniga reason va qaysi bosqich skipped ekani ko'rsatiladi; uydirma qiymat yo'q.

### F5 — Jamoa, audit va platform registry

- Owner/admin member yaratadi; rol va `can_view_pii` ikki alohida control. PII huquqi tanlansa inline risk note.
- Auditor audit jadvalida action/outcome/date/actor/research bo'yicha client-side filter qiladi; backend faqat so'nggi 200 eventni beradi, UI buni “oxirgi 200 ta” deb aytadi.
- Platform admin metodika → version snapshot → licence revision → publish ketma-ketligida ishlaydi. Publishdan oldin server gate; reason required. Tenant workbench PII bilan registry aralashmaydi.

## 5. Ekran inventory: hierarchy, state va CTA

| ID | Ekran | Vizual hierarchy | Majburiy state'lar | Primary CTA |
| --- | --- | --- | --- | --- |
| S01 | Login | Wordmark → fieldset → session xato | idle/submitting/invalid/auth failed | Kirish |
| S02 | Owner registration | Account → organization → review | field/server conflict/success | Tashkilot yaratish |
| S03 | Bootstrap | Instance warning → admin fields → token | already initialized/token invalid/success | Platformani ishga tayyorlash |
| S04 | Tenant chooser | User → membership list → role | single/multiple/no active membership | Tashkilotga kirish |
| S05 | Research list | Title+filters → status lanes/table → empty | loading/empty/error/populated | Yangi tadqiqot |
| S06 | Research create | Stepper → form → sticky review summary | draft/field error/gate unavailable | Draft yaratish |
| S07 | Research overview | Identity+status → readiness strip → activity/work areas | draft/active/blocked/read-only | Faollashtirish yoki Javob kiritish |
| S08 | Methodology catalog/picker | Search/filter → compact rows → inspector | empty/licence blocked/eligible | Versiyani tanlash |
| S09 | Participants | Privacy boundary → compact list → detail inspector | no participant/consent blocked/masked | Ishtirokchi qo'shish |
| S10 | Consent record | Participant pseudonim → status → reference fields | granted/declined/withdrawn/basis required | Rozilikni qayd etish |
| S11 | Manual response | Section nav → item form → validation rail | draft/saving/validation failed/validated/conflict | Tekshirish va yakunlash |
| S12 | CSV import | Context → dropzone → preview grid → confirm bar | unsupported/parsing/fatal/partial/ready/confirmed | Tekshirish / Yaroqli qatorlarni saqlash |
| S13 | Calculation gate | Revision summary → gate checklist → action | not validated/licence/consent/research blocked/running | Natijani hisoblash |
| S14 | Result | Provenance → scale results → interpretation → disclaimer | complete/uninterpreted/invalid/loading/error | Qanday hisoblandi? |
| S15 | Trace | Disclosure note → pipeline → scale/step detail | full/derived/summary/redacted/skipped/failed | Bosqichni ochish |
| S16 | Team | Member table → role/PII inspector | empty/error/permission denied | A'zo qo'shish |
| S17 | Retention policies | Policy list → create form → usage note | empty/invalid/created | Siyosat yaratish |
| S18 | Audit | Scope note → filters → event table/detail | empty/loading/last-200/error | Event tafsiloti |
| S19 | Platform registry | Methodology list → version → licence/publish inspector | draft/in review/published/gate failed | Publish |
| S20 | Access/error | Safe code → human message → recovery | 401/403/404/409/422/5xx/offline | Qayta urinish yoki xavfsiz qaytish |

## 6. Kritik state va interaction spetsifikatsiyasi

### 6.1. Universal async state'lar

- **Loading:** shell va oldingi xavfsiz kontekst qoladi; 400 msdan qisqa requestda skeleton ko'rsatilmaydi. Uzoq list uchun 3–5 neutral skeleton row, natija uchun “Natija olinmoqda” text + spinner.
- **Empty:** sababga mos: “Tadqiqot hali yo'q” + authorized CTA; filter emptyda `Filtrni tozalash`; permission empty sifatida maskalanmaydi.
- **Error:** inline error well; safe `error.code`, tarjima qilingan izoh, correlation reference bo'lsa ko'rsatiladi. Raw server payload yoki stack yo'q.
- **Success:** yaratishdan keyin persistent object status va qisqa live-region xabari. Domain success faqat 2xxdan so'ng.
- **Offline/timeout:** saqlanmagan local form state qoladi; “Server bilan aloqa yo'q, hali saqlanmadi.” Retry idempotent actionlarda shu key bilan.
- **409 conflict:** silent overwrite yo'q; yangi server state'ni yuklash va local draftni copy qilish imkoniyati.

### 6.2. Manual response

- Chap/yuqori section index item completionni `12/20` kabi ko'rsatadi, score yoki interpretationni oldindan ko'rsatmaydi.
- Required marker matnli legend bilan. Inputdan chiqqanda client validation; submitda server error summary.
- Draft badge: `Mahalliy o'zgarish`, `Serverga saqlanmoqda`, `Draft saqlandi`, `Saqlanmadi` aniq farqlanadi. Backend create/revision semanticsga mos bo'lmagan autosave ishlatilmaydi.
- Validated revision locked ko'rinishga o'tadi. Correction yangi revision va `correction_reason`; eski natija o'zgarmasligi reviewda ko'rsatiladi.

### 6.3. CSV preview/confirm

- Counterlar bir xil card emas, bitta “ledger strip”: `Jami 120 | Yaroqli 108 | Xatoli 10 | Duplikat 2`.
- Error grid ustunlari: row, safe participant ref (mask), column/item, severity, human message, action. Raw rejected value default ko'rsatilmaydi.
- Error code copyable, ammo screen reader uchun human label birinchi.
- Confirm bar: “108 yaroqli qator saqlanadi; 12 qator saqlanmaydi.” `preview_hash` UI'da qisqartirilgan audit ref sifatida optional.
- Zero valid → confirm disabled emas, umuman ko'rsatilmaydi; `Faylni tuzatib qayta tekshirish` primary.

### 6.4. Consent va licence gate

- Gate banner status rangi + icon + heading + sabab + next actiondan iborat.
- Consent declined/withdrawn qizil “danger” dramatizatsiyasi emas; **processing blocked** semantikasi. “Yangi javob, hisoblash va eksport to'xtatilgan.”
- Licence `expired/revoked/unknown/restricted`da oldingi result read-only bo'lishi mumkin; “Natijani o'chirish” yoki “baribir hisoblash” CTA yo'q.
- Gate checklar: Research Active, current revision Validated, consent valid, methodology Published, licence Verified, pinned hash mos. Backend qaytarmagan check “Tekshirilmagan” deb ko'rsatiladi, “Passed” deb taxmin qilinmaydi.

### 6.5. Maxfiylik zonalari

- PII zonasi `privacy-surface` va chap 3 px border bilan javob/natijadan vizual ajratiladi; title'da `shield` icon va “Shaxsni aniqlovchi ma'lumot” label.
- `can_view_pii=false`: qiymat DOMga umuman kelmasligi kerak; blur CSS bilan “yashirish” taqiqlanadi.
- `can_view_pii=true`: default mask; `Ko'rsatish` explicit action audit endpoint mavjud bo'lgandagina. Route, query string, analytics event, browser title va clipboard success message'da PII yo'q.
- Tenant switch PII reveal va selected participant state'ni darhol tozalaydi.
- Hozir backend PII encryption integratsiyasiz direct PII payloadni rad etadi; identified collection UI disabled va “Serverda PII saqlash sozlanmagan” deb ko'rsatiladi.

## 7. Result progressive disclosure va disclaimer

### 7.1. Uch qatlam

**Qatlam A — Qarash:** scale nomi/code, `score_display`, unit, validity label, norm band mavjud bo'lsa label, answered/missing. 5 soniyada o'qiladi.

**Qatlam B — Talqin:** faqat server snapshotidagi `interpretation_snapshot_i18n`; yetarli ma'lumot bo'lmasa reason. Interpretation platforma tavsiyasi yoki tashxis sifatida yozilmaydi.

**Qatlam C — Hisob izi:** provenance va ordered trace. Default pipeline groups: Gate → Javoblarni tayyorlash → Item o'zgartirish → Scale hisoblash → Validity/norm → Talqin → Display/persist. Har group ichida step accordion.

### 7.2. Trace row anatomiyasi

`sequence` → status icon + lokalizatsiya qilingan step nomi → entity ref → bir qator xulosa → expand affordance. Expanded: rule ref, safe input/output, reason code, redaction izohi. `skipped/blocked/failed` status text bilan; step tartibi animatsiyadan mustaqil.

`full`, `derived_only`, `summary_only` ekranning yuqorisida disclosure badge va tushuntirishga ega. Role disclosure'ni kengaytirmaydi. PII trace'ga hech qachon kirmaydi.

### 7.3. Non-diagnostic copy

Natijada doim, birinchi viewport ichida neutral note:

> **Natijaning qo'llanish chegarasi**  
> Bu natija tibbiy tashxis emas. U tanlangan metodika va ko'rsatilgan javoblar asosidagi tadqiqot natijasidir; professional kontekst bilan talqin qiling.

Bu matn warning-red banner emas, `info-subtle` surface va `info` icon bilan. “Xavf”, “kasallik” yoki qo'rqituvchi copy ishlatilmaydi. Export mavjud bo'lganda ayni disclaimer snapshot bilan kiritiladi.

## 8. Distinctive visual direction — “Quiet Instrument”

### 8.1. Rang tokenlari

Palitra iliq qog'oz, chuqur archa-yashil va oksidlangan mis aksentiga asoslanadi. Katta gradient yo'q. Rang juftlari WCAG AA normal textga mo'ljallangan; implementatsiyada automated contrast test majburiy.

| Token | HEX | Qo'llanish |
| --- | --- | --- |
| `canvas` | `#F4F1E8` | Asosiy iliq fon |
| `surface` | `#FFFEFA` | Form, inspector, table header emas |
| `surface-muted` | `#E9ECE5` | Group/disabled/subtle note |
| `surface-ink` | `#112A26` | Desktop rail, high-emphasis strip |
| `ink-strong` | `#17231F` | Asosiy text |
| `ink` | `#34443F` | Secondary text |
| `ink-muted` | `#5A6964` | Metadata; faqat large yoki surface bilan tekshirib |
| `line` | `#C9CEC6` | Divider, table rule |
| `line-strong` | `#86948E` | Input border/focus-adjacent |
| `primary` | `#176B5B` | Primary action/link on light |
| `primary-hover` | `#105548` | Hover/pressed |
| `primary-soft` | `#D8E9E2` | Selected row/background; text `#174C42` |
| `copper` | `#A84F2A` | Workbench accent, active trace marker |
| `copper-soft` | `#F1DED2` | Attention/subtle provenance |
| `info` | `#286487` | Informational status |
| `info-soft` | `#DCEAF2` | Disclaimer/info well |
| `success` | `#276A4D` | Server-confirmed success |
| `success-soft` | `#DDEBE2` | Success background |
| `warning` | `#845B12` | Gate attention |
| `warning-soft` | `#F3E8C9` | Warning background |
| `danger` | `#9A3741` | Validation/destructive/error |
| `danger-soft` | `#F3DEE0` | Error background |
| `privacy` | `#59458A` | PII boundary only |
| `privacy-soft` | `#E8E2F2` | PII zone background |
| `focus` | `#0B78A6` | 3 px focus ring |

`surface-ink` ustida text `#F8F5ED`, muted `#C8D4CF`, active marker `#E7A16F`. White text `primary`, `danger`, `info`, `success` backgroundida contrast testdan o'tishi shart; soft surface'larda dark semantic text ishlatiladi.

Hisoblangan normal-text kontrastlari: `ink-strong/canvas` 14.34:1, `ink-muted/canvas` 5.11:1, `primary/surface` 6.32:1, `copper/surface` 5.45:1, `info/surface` 6.38:1, `success/surface` 6.39:1, `warning/surface` 5.97:1, `danger/surface` 6.94:1, `privacy/surface` 7.87:1, rail text/rail 13.94:1 va rail muted/rail 9.96:1. Bu qiymatlar WCAG sRGB formulasi bo'yicha; real component opacity, disabled state va browser rendering alohida test qilinadi.

### 8.2. Typography

- UI/body: **Source Sans 3**, self-hosted package/WOF2; fallback `Segoe UI, Arial, sans-serif`.
- Section/title: **Newsreader**, 500/600, faqat page title va result scale heading; body yoki buttonda emas. Bu editorial/research ohang beradi.
- Data/code/hash: **IBM Plex Mono**, self-hosted, tabular nums; fallback `Consolas, monospace`.
- External font CDN ishlatilmaydi; privacy va layout shift uchun assetlar app bilan build qilinadi.
- Scale: 12 metadata, 14 compact/table, 16 body, 18 section, 24 page, 34 auth/title. Body line-height 1.5; compact grid 1.35. Score 36–44 px, lekin dekorativ KPI gigant emas.

### 8.3. Spacing, geometry va depth

- 4 px base; spacing: `4, 8, 12, 16, 24, 32, 48, 64`.
- Control height: compact 36, default 42, touch 44 minimum. Table row 44–52.
- Radius: input/button 6 px; panel 8 px; overlay 12 px; pill faqat status/tag. Barcha content “card” emas — sectionlar divider va whitespace bilan ajratiladi.
- Border: 1 px `line`; selected/PII/trace'da 3 px leading rule. Tableda zebra emas, row divider va selected tint.
- Shadow faqat overlay: `0 12px 32px rgba(17,42,38,.14)`; normal panel shadow yo'q yoki `0 1px 2px rgba(...,.06)`.
- Background texture, decorative blobs va glass blur yo'q. Auth ekranida tipografik grid/rule va kichik copper registration mark yetarli.

## 9. External icon server policy

### 9.1. Manba va foydalanish

- Primary icon source: rasmiy **Iconify API**, Lucide collection: `https://api.iconify.design/lucide/{name}.svg`.
- Iconlar `<img>`/framework image component orqali olinadi; remote JS, icon web component yoki CDN script kiritilmaydi.
- Misol: `https://api.iconify.design/lucide/flask-conical.svg?color=%2334443F&width=20&height=20`.
- Icon dekorativ bo'lsa `alt=""` va yonida visible label; icon-only button bo'lsa explicit `aria-label` + tooltip. Emoji va qo'lda chizilgan inline SVG primary icon sifatida ishlatilmaydi.

### 9.2. Semantic map

| Ma'no | Lucide nomi | Ma'no | Lucide nomi |
| --- | --- | --- | --- |
| Research | `flask-conical` | Methodology | `notebook-tabs` |
| Participant | `user-round` | Team | `users-round` |
| Manual entry | `list-pen` | CSV import | `file-up` |
| Validate | `list-checks` | Calculate | `sigma` |
| Result | `chart-no-axes-column-increasing` | Trace | `git-commit-horizontal` |
| Consent | `file-signature` | Licence | `badge-check` |
| Privacy/PII | `shield` | Audit | `scroll-text` |
| Retention | `archive` | Organization | `building-2` |
| Success | `circle-check` | Warning | `triangle-alert` |
| Error | `circle-x` | Info/disclaimer | `info` |
| Locked | `lock-keyhole` | Redacted | `eye-off` |
| Expand | `chevron-down` | More | `ellipsis` |

### 9.3. Failure, CSP, privacy va performance

- Har icon wrapper fixed `width/height` bilan layout shiftni to'xtatadi. `onerror` remote rasmni yashirib, CSS-drawn neutral 12 px square/dot yoki 2-letter text fallbackni ko'rsatadi; semantic label qoladi.
- Critical navigation faqat iconga bog'liq emas; text label server ishlamasa ham ishlaydi.
- `referrerpolicy="no-referrer"`, `crossorigin="anonymous"`; icon URLda tenant, participant, route param yoki user data bo'lmaydi.
- CSP minimum: `default-src 'self'; img-src 'self' data: https://api.iconify.design; script-src 'self'; style-src 'self'; font-src 'self'; connect-src 'self' <API_ORIGIN>; object-src 'none'; base-uri 'self'; frame-ancestors 'none'`.
- Remote icon request user IP va icon name'ni providerga ochishi mumkin; privacy review release gate. Provider nomaqbul bo'lsa UI fallback label bilan to'liq ishlaydi. Remote iconlarni o'z serveriga yashirin proxy qilish backend roziligisiz qilinmaydi.
- Bir viewda unique icon nomlari cheklanadi; browser cache ishlatiladi, non-critical icon `loading="lazy"`. Har rowda remote status icon yuklash o'rniga CSS color + text yoki oldindan yuklangan bitta semantic asset ishlatiladi.

## 10. Motion system

### 10.1. Tokenlar

| Token | Qiymat | Ishlatish |
| --- | --- | --- |
| `motion-instant` | 80 ms | Press/color feedback |
| `motion-fast` | 140 ms | Hover, focus-adjacent tint |
| `motion-base` | 220 ms | Drawer, accordion, row insert |
| `motion-slow` | 320 ms | Route content intro, overlay |
| `ease-standard` | `cubic-bezier(.2,.8,.2,1)` | Move/resize |
| `ease-enter` | `cubic-bezier(.16,1,.3,1)` | Enter |
| `ease-exit` | `cubic-bezier(.4,0,1,1)` | Exit, 140–180 ms |

### 10.2. Maqsadli motion

- Route: shell o'zgarmaydi; content 6 px translate + opacity, 220 ms. Back navigationda translate yo'q.
- Overlay/drawer: scrim 160 ms, panel 220 ms; focus transition tugashini kutmaydi.
- List create: yangi row 8 px fade-in, 220 ms; reorder animatsiyasi yo'q.
- Trace reveal: group accordion 220 ms; foydalanuvchi “Bosqichlarni ketma-ket ko'rsatish”ni tanlasa step markerlar 35 ms stagger, jami 350 msdan oshmaydi. Ball count-up yo'q.
- Upload: dropzone border/tint 140 ms; fayl qabulida icon 4 px settle. Server processing indeterminate 1.2 s linear bar, `aria-valuetext`; uydirma percent yo'q.
- Progress: haqiqiy section completion 160 ms width; status serverdan kelgach label crossfade.
- Success: check icon 140 ms scale 0.96→1, confetti/shake yo'q.
- Error: focus va border o'zgaradi; field shake qilinmaydi.

### 10.3. Animatsiya qilinmaydigan joylar

Score, norm band, interpretation, PII reveal, consent withdrawal, licence revoke va audit qiymatlari count-up/morph qilinmaydi. Data grid sort paytida rowlar uchib o'tmaydi. Loading skeleton pulse juda past kontrastli yoki static; vestibular riskli parallax/zoom yo'q.

`prefers-reduced-motion: reduce`da route translate, accordion height animation, stagger, indeterminate sweep o'chadi; instant state yoki 80 ms opacity. Funksiya va status tartibi o'zgarmaydi.

## 11. Accessibility

- WCAG 2.2 AA target. Text contrast ≥4.5:1, large/UI non-text ≥3:1; token juftlari automated va manual tekshiriladi.
- Har route'ga `h1`, logical heading order va “Asosiy kontentga o'tish” skip link.
- Keyboard: rail → topbar → main; dialog focus trap va openerga return; Escape destructive confirmni bajarmaydi. Trace accordion buttonlari Enter/Space, Arrow navigation optional.
- Visible focus 3 px `focus` + 2 px offset; focus rang yoki shadow panelda yo'qolmaydi.
- Error summary submitdan keyin fokus oladi (`tabindex=-1`), xato linklari fieldga olib boradi; `aria-describedby`da hint + error.
- Async status polite live region; calculation/import completion assertive emas, faqat blocking error `role=alert`.
- Table semantic `<table>`; sortable header `aria-sort`; mobile stacked listda labels takrorlanadi. Virtualized grid screen readerda accessible row count beradi yoki virtualization o'chadi.
- Status faqat rang emas: icon + human label. Hash/code uchun copy button accessible nomga ega.
- Touch target ≥44×44; adjacent targets ≥8 px. Swipe-only interaction yo'q.
- Locale `uz-Latn`; sana foydalanuvchi formatida, provenance tooltip/detailda ISO UTC. Decimal display server string sifatida; uni JS floatga aylantirib buzmaslik.
- Zoom 200%da reflow; 320 CSS pxda horizontal page scroll yo'q, faqat aniq belgilangan data grid region bo'lishi mumkin.
- Icon load failure semantikani yo'qotmaydi. Newsreader decorative title o'qilishga xalaqit bersa Source Sans fallback.

## 12. Text wireframe / layout blueprint

### 12.1. Desktop research workbench

```text
┌──────── 248 rail ────────┬────────────────────────────────────────────────────┐
│ PSYCHOGRAM               │ Research / R-024                         [ACTIVE]  │
│ [Org: Meridian Lab  v]   ├────────────────────────────────────────────────────┤
│                          │ R-024 Diqqat tadqiqoti       [Javob kiritish]     │
│ ▌ Tadqiqotlar            │ Metodika v2.1 • pseudonymous • 365 kun            │
│   Metodikalar            ├───────────────────────────────┬────────────────────┤
│   Jamoa                  │ Ish maydoni                   │ Kontekst            │
│   Retention              │ ┌ readiness ledger ─────────┐│ Status: Active      │
│   Audit                  │ Consent 18/20 | Valid 16     │ Licence: Verified   │
│                          │ └────────────────────────────┘│ PII: Pseudonymous   │
│                          │ Recent responses (table)      │ Retention: 365 kun  │
│                          │ P-014  Validated  14:32 [→]   │ [Audit tafsiloti]   │
│ User • Researcher        │ P-015  Draft      14:25 [→]   │                    │
└──────────────────────────┴───────────────────────────────┴────────────────────┘
```

### 12.2. Desktop result + trace

```text
┌ rail ─────────┬ P-014 / Natija                         [COMPLETE] ────────────┐
│               │ v2.1 • revision 3 • 15 Jul 2026 • hash 8ac… [copy]          │
│               ├──────────────────────────────────┬────────────────────────────┤
│               │ NATIJA                           │ PROVENANCE                 │
│               │ Total                     5.00   │ Answered 18 / Missing 2    │
│               │ [valid] [middle band]            │ Disclosure: derived only   │
│               │ Oldindan yozilgan talqin…        │ Revision hash…             │
│               │                                  │ Methodology hash…          │
│               │ [i] Natijaning qo'llanish…       │                            │
│               ├──────────────────────────────────┴────────────────────────────┤
│               │ Natija | Qanday hisoblandi?                                  │
│               │ ● Gate ─ ● Mapping ─ ● Aggregate ─ ● Norm ─ ● Display       │
│               │ 06  Scale aggregate                              [ochish v]  │
└───────────────┴───────────────────────────────────────────────────────────────┘
```

### 12.3. Tablet

```text
┌72 rail┬ Research / R-024      [ACTIVE] [⋯] ┐
│ icons │ R-024 Diqqat tadqiqoti             │
│+tips  │ readiness ledger                    │
│       │ tabs: Overview Participants Import │
│       │ full-width table / form             │
│       │ [Kontekstni ochish] → drawer        │
└───────┴─────────────────────────────────────┘
```

### 12.4. Mobile manual entry

```text
┌ menu   R-024                     [ACTIVE] ┐
│ P-014 • pseudonymous                      │
│ Consent: granted                          │
│ 2-bo'lim / 4                 8 / 20        │
│ ───────────── progress ─────────────       │
│ Q9. [prompt licence ruxsatiga mos]         │
│ ( ) Hech qachon                           │
│ ( ) Ba'zan                                │
│ ( ) Ko'pincha                             │
│                                           │
│ [Oldingi]                       [Keyingi]  │
├ Research ─ Kiritish ─ Natija ─ Ko'proq ──┤
└───────────────────────────────────────────┘
```

## 13. UI component inventory va token handoff

### 13.1. Foundations

`AppShell`, `TenantSwitcher`, `RoleAwareNav`, `TopContextBar`, `Breadcrumbs`, `PageHeader`, `SplitWorkbench`, `InspectorDrawer`, `Section`, `Divider`, `ResponsiveDataView`.

### 13.2. Controls

`Button` (primary/secondary/quiet/danger), `IconButton`, `TextField`, `PasswordField`, `Textarea`, `Select`, `Combobox`, `RadioGroup`, `Checkbox`, `DateTimeField`, `SearchField`, `FileDropzone`, `SegmentedTabs`, `Stepper`, `StickyActionBar`.

### 13.3. Domain components

`ResearchStatus`, `LicenceGate`, `ConsentGate`, `ReadinessLedger`, `MethodologyRow`, `VersionInspector`, `ParticipantRef`, `PrivacyBoundary`, `PIIMask`, `ResponseSectionNav`, `ValidationSummary`, `ImportLedger`, `ImportErrorGrid`, `CalculationGate`, `ScaleResult`, `ProvenanceStrip`, `DisclosureBadge`, `TracePipeline`, `TraceStep`, `NonDiagnosticNote`, `AuditEventDetail`.

### 13.4. Feedback

`InlineNotice`, `FieldError`, `ErrorSummary`, `EmptyState`, `LoadingRows`, `ProgressBar`, `Toast` (faqat ephemeral success), `ConflictPanel`, `AccessDenied`, `OfflineNotice`, `ConfirmAction`.

### 13.5. Minimal design token schema

```text
color.{canvas,surface,surface-muted,surface-ink,ink-strong,ink,ink-muted,line,line-strong,
       primary,primary-hover,primary-soft,copper,copper-soft,info,info-soft,success,
       success-soft,warning,warning-soft,danger,danger-soft,privacy,privacy-soft,focus}
space.{1=4,2=8,3=12,4=16,6=24,8=32,12=48,16=64}
radius.{control=6,panel=8,overlay=12,pill=999}
type.{ui,title,mono}.{xs,sm,md,lg,xl}
motion.{instant=80,fast=140,base=220,slow=320}.{standard,enter,exit}
size.{control-compact=36,control=42,touch=44,rail=248,rail-compact=72}
z.{base=0,sticky=10,dropdown=30,overlay=40,toast=50}
```

## 14. UI acceptance checklist

### Functional va contract

- [ ] Har tenant request `Authorization` va `X-Organization-ID` yuboradi; switch cache/reveal state'ni tozalaydi.
- [ ] Role bo'yicha navigation/CTA mos; server 403 baribir authoritative.
- [ ] Research create, activate, participant, consent, response, revision, validate, calculate, result, import preview/confirm backend schema bilan exact.
- [ ] Decimal score string sifatida ko'rsatiladi; client rounding bandni o'zgartirmaydi.
- [ ] Idempotency key bir logical calculate retryda saqlanadi.
- [ ] Preview confirm aynan server `preview_hash` bilan.
- [ ] API yo'q screen soxta data bilan to'ldirilmaydi; gap state developer flag bilan aniq.

### Privacy va safety

- [ ] PII permission bo'lmasa qiymat DOM, URL, log, analytics, error va clipboardga kirmaydi.
- [ ] Identified PII flow encryption integratsiyasiz disabled.
- [ ] Consent/licence/research gate bypass CTA yo'q.
- [ ] Result va export disclaimer doim ko'rinadi; tashxis/tavsiya copy yo'q.
- [ ] Trace licence disclosure darajasidan ortiq ma'lumot ko'rsatmaydi.
- [ ] Sintetik demo production catalogda selectable emas.

### Visual va anti-template

- [ ] Generic hero/gradient orb/glassmorphism/3-card marketing composition yo'q.
- [ ] Panel ierarxiyasi divider, alignment va density bilan; hammasi bir xil rounded card emas.
- [ ] Palitra semantik ishlaydi, score'ni moral rang bilan baholamaydi.
- [ ] External icon policy, fixed sizing, fallback va CSP ishlaydi; emoji/hand-drawn inline SVG primary emas.
- [ ] Desktop/tablet/mobile blueprintlar bajarilgan.

### Accessibility va motion

- [ ] Axe/automated testda critical violation yo'q; contrast token matrix tekshirilgan.
- [ ] Faqat keyboard bilan auth → manual entry → validate → result → trace ishlaydi.
- [ ] 200% zoom, 320 px reflow va touch targetlar tekshirilgan.
- [ ] Screen reader error summary, table, status va trace sequence'ni tushunadi.
- [ ] `prefers-reduced-motion` barcha non-essential movementni o'chiradi.
- [ ] Ball/PII/consent/licence animatsiya bilan dramatizatsiya qilinmaydi.

## 15. Backend endpoint-to-screen mapping

| Endpoint | Method | Screen/flow | UX note |
| --- | --- | --- | --- |
| `/api/v1/auth/bootstrap` | POST | S03/F0 | Bo'sh instance, 201 token; token optional configga bog'liq |
| `/api/v1/auth/register` | POST | S02/F0 | Owner + organization yaratadi |
| `/api/v1/auth/login` | POST | S01/F0 | Bearer token |
| `/api/v1/auth/me` | GET | S04/shell | Membership, role, PII flag; tenant tanlash manbai |
| `/api/v1/organizations/current` | GET | Shell | `X-Organization-ID` bilan active org |
| `/api/v1/organizations/current/members` | GET/POST | S16/F5 | Faqat owner/admin; create'da parolni admin belgilaydi |
| `/api/v1/retention-policies` | POST | S17/F1 | Create bor, list yo'q: B01 |
| `/api/v1/methodologies` | GET | S08/S19 | Global list; view modeli faqat id/code/name/status |
| `/api/v1/methodologies` | POST | S19/F5 | Platform admin |
| `/api/v1/methodologies/{id}/versions` | POST | S19/F5 | Platform admin; GET list yo'q: B02 |
| `/api/v1/methodology-versions/{id}/licences` | POST | S19/F5 | Platform admin; current licence GET yo'q: B02 |
| `/api/v1/methodology-versions/{id}/publish` | POST | S19/F5 | Platform admin, reason required |
| `/api/v1/researches` | GET | S05 | Tenant list; pagination/filter serverda yo'q |
| `/api/v1/researches` | POST | S06/F1 | owner/admin/researcher |
| `/api/v1/researches/{id}/activate` | POST | S07/F1 | Readiness error inline gatega map qilinadi |
| `/api/v1/researches/{id}/participants` | POST | S09/F2 | Create bor, list/detail yo'q: B03 |
| `/api/v1/participants/{id}/consents` | POST | S10/F2 | Create bor, GET/history yo'q: B03 |
| `/api/v1/researches/{id}/responses` | POST | S11/F2 | Create; item schema UI uchun read endpoint yo'q: B02/B04 |
| `/api/v1/responses/{id}/revisions` | POST | S11/F2 | Correction; current response GET yo'q: B04 |
| `/api/v1/responses/{id}/validate` | POST | S11/F2 | RevisionView validation summary |
| `/api/v1/researches/{id}/calculations` | POST | S13/F2 | Researcher+, response revision + idempotency key |
| `/api/v1/results/{id}` | GET | S14–S15/F4 | Result + scales + trace; ID ma'lum bo'lishi kerak |
| `/api/v1/researches/{id}/imports/preview` | POST | S12/F3 | JSON ichida UTF-8 `csv_text`, multipart emas |
| `/api/v1/researches/{id}/imports/{import_id}/confirm` | POST | S12/F3 | Preview hash exact |
| `/api/v1/audit-events` | GET | S18/F5 | Oxirgi 200, pagination/filter yo'q |
| `/health` | GET | S20/ops | UI app readiness uchun business data sifatida emas |

Barqaror API error shakli: `{"error":{"code":"...","message":"..."}}`. UI `code`ni branch qilish uchun, localized safe copy'ni ko'rsatish uchun ishlatadi; backend English `message`ni yagona UX copy sifatida bermaydi.

## 16. Ochiq savollar, backend gaplar va konservativ taxminlar

### 16.1. UI'ni to'liq ishlatishdan oldingi backend gaplar

| ID | Kerakli kontrakt | Ta'sir | Konservativ UI xulqi |
| --- | --- | --- | --- |
| B01 | `GET /retention-policies` | Research create policy tanlay olmaydi | Policy IDni qo'lda kiritish production UX emas; create wizardni gap flag bilan bloklash |
| B02 | Methodology detail/version/licence GET, published eligible versions | Catalogdan version tanlash va item prompt qurish imkonsiz | Platform admin create response'idan transient statega suyanmaslik; picker bloklangan |
| B03 | Participant list/detail va consent current/history GET | Research qayta ochilganda workflow davom etmaydi | Faqat create success sessionidan keyingi short flow; productionda endpoint talab |
| B04 | Response/detail/revision GET/list | Draft resume, correction va calculation selection yo'q | Client local draftni canonical server state deb qabul qilmaslik |
| B05 | Result list/search by research/participant/revision | Oldingi natijani topish imkonsiz | Calculate successdan ID orqali route; durable result navigation uchun endpoint talab |
| B06 | Export endpointlar | Product scope'dagi structured export yo'q | Export CTA ko'rsatilmaydi; client HTML/CSVni “official export” deb yaratmaydi |
| B07 | Research pause/close/archive, retention/legal hold endpoints | Lifecycle P1 UI amalga oshmaydi | Status read-only; mavjud bo'lmagan CTA yo'q |
| B08 | Member update/revoke/PII permission update | Team faqat list/create | Edit/remove controls yo'q |
| B09 | Server-side audit pagination/filter/detail | 200 event bilan cheklangan | “Oxirgi 200” label, client filter shu set ichida |
| B10 | Actual file/XLSX/template download/mapping endpoints | Product scope'dagi XLSX va template flow yo'q | Faqat browser-read UTF-8 CSV; XLSX disabled |
| B11 | PII encryption/view/audit endpoint | Identified mode va reveal xavfsiz emas | Identified PII collection disabled |
| B12 | Error correlation ID / field issue schema consistency | Support va inline mapping cheklangan | Safe code + generic recovery; raw payload yo'q |

### 16.2. Product/yuridik ochiq savollar

- Dastlabki yurisdiksiya, retention min/max va deletion SLA.
- Result/export formatlari va licence revoke'dan keyingi trace disclosure.
- Research-level member assignment P0 yoki barcha tenant researcherlar ko'radimi.
- Consent full documentmi yoki protected reference; `not_required_with_basis` whitelist.
- Repeat attempt, deprecated pinned versionda yangi scoring va break-glass support.
- External Iconify requestining tashkilot privacy siyosatiga mosligi; kerak bo'lsa “tashqi serverdan icon” talabi qayta ko'rib chiqiladi.

### 16.3. Konservativ UX taxminlari

- Faqat kattalar; participant self-service yo'q.
- `pseudonymous` default; PII va free text default o'chiq.
- Bitta research bitta methodology version; `initial` attempt.
- Group analytics, diagnosis, treatment recommendation va AI interpretation yo'q.
- UI locale birinchi release'da `uz-Latn`; server i18n snapshotidagi shu locale, bo'lmasa aniq fallback label.
- Auth token memory yoki xavfsiz same-site server session wrapperda; localStorage qarori security review'siz qabul qilinmaydi.

## 17. Self-review

### Anti-template

- [x] Metafora workbench/ledger/instrument; marketing hero va generic SaaS card grid rad etildi.
- [x] O'ziga xos iliq paper + spruce + copper palitra, restrained geometry va editorial/data typography berildi.
- [x] Rang/motion faqat orientation, privacy, status va feedbackga bog'landi.

### Flow coverage

- [x] Login/bootstrap/tenant, research create/activate, participant/consent, manual response, validation, calculate, CSV preview/confirm, result/trace, members/audit/registry oqimlari qoplandi.
- [x] Empty/loading/error/success, conflict, gate, partial import va disclosure state'lari berildi.
- [x] Sintetik demo productiondan ajratildi, PII va scoring natijalari UX darajasida ham ajratildi.

### Accessibility

- [x] Keyboard, focus, screen reader, touch, reflow, contrast va reduced motion talablar berildi.
- [x] Icon/rang/motion bo'lmasa ham semantics va task completion saqlanadi.

### Backend-contract mosligi

- [x] Amaldagi endpointlar request/response vazifasi bilan map qilindi.
- [x] Backendda yo'q query/export/lifecycle/PII imkoniyatlari yashirilmay, B01–B12 sifatida release gapga chiqarildi.
- [x] CSV `csv_text`, mandatory tenant header, role gates, idempotency, immutable revision/result, licence disclosure va disclaimer saqlandi.

**Self-review xulosasi:** spetsifikatsiya UI subagentga vizual va interaction yo'nalishini aniq beradi, lekin backendda mavjud bo'lmagan ma'lumotni taxmin qilmaydi. To'liq production UI uchun avval B01–B06 va B11 endpoint gaplari yopilishi kerak; qolgan ekranlar progressive delivery bilan qurilishi mumkin.

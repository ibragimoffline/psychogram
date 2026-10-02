# Psychogram MVP: metodika, scoring va data modeli kontrakti

## 0. Hujjat maqsadi va maqomi

Ushbu hujjat `docs/01_product_scope.md` dagi tasdiqlangan mahsulot doirasini metodika katalogi, scoring dvigateli, javob revisionlari, natija provenance'i va import validatsiyasi uchun implementatsiyaga tayyor domen kontraktiga aylantiradi. Hujjat backend agent uchun majburiy handoff hisoblanadi; API endpoint, ORM, database vendor yoki UI texnologiyasini belgilamaydi.

MVP individual ishtirokchi javobini deterministik hisoblaydi va izohlaydi. U tibbiy tashxis, davolash tavsiyasi yoki klinik qarorni avtomatlashtirmaydi. Har bir ko'rinadigan natija va eksport quyidagi ma'nodagi disclaimer'ni o'z ichiga olishi shart: **“Bu natija tibbiy tashxis emas.”**

Bu kontraktdagi sintetik misol faqat dasturiy test va tushuntirish uchun yaratilgan, mualliflik huquqidan xoli. U validatsiyalangan psixometrik vosita emas va production tadqiqoti yoki klinik foydalanish uchun yaroqsiz.

## 1. Terminlar va bounded context

### 1.1. Terminlar

| Termin | Aniq ma'no |
| --- | --- |
| `Methodology` | Bir psixometrik vositaning versiyalardan mustaqil katalog identiteti va umumiy metadata'si. |
| `MethodologyVersion` | Savollar, variantlar, shkalalar, scoring qoidalari, normlar va interpretatsiyaning immutable snapshot'i. |
| `Scale` | Item ballaridan hosil qilinadigan umumiy yoki subshkala o'lchovi. |
| `Item` | Ishtirokchidan bitta strukturali javob talab qiladigan versiyalangan element. |
| `ResponseOption` | Kategorik item uchun ruxsat etilgan barqaror kod va uning scoring qiymati. |
| `NormSet` | Score'ni ma'lum norm profili yoki threshold to'plamiga solishtirish qoidalari. |
| `InterpretationRule` | Valid score/norm natijasiga mos, oldindan tasdiqlangan deterministik talqin. |
| `Licence` | Metodika versiyasidan qaysi kontekstda foydalanish va nimalarni oshkor qilish mumkinligini belgilovchi huquqiy metadata. |
| `Response` | Tadqiqot–ishtirokchi–attempt identitetini birlashtiruvchi, revisionlardan mustaqil konteyner. |
| `ResponseRevision` | Javoblarning ma'lum vaqtdagi immutable snapshot'i. Tuzatish yangi revision yaratadi. |
| `CalculationRun` | Bitta response revision uchun scoring dvigatelining bitta urinish/protsess yozuvi. |
| `Result` | Muvaffaqiyatli run'da hosil bo'lgan immutable umumiy natija konteyneri. |
| `ScaleResult` | Result ichidagi bitta scale score, norm va interpretatsiya natijasi. |
| `ExplainabilityTrace` | Natijaning deterministik bosqichlari, input/output va qoida reference'larining immutable izi. |
| `Provenance` | Ma'lumot qayerdan, qaysi actor/import/revision/versiya orqali kelganini isbotlovchi metadata. |
| `Release gate` | Published versiya, yaroqli licence va foydalanish konteksti bajarilmasa faollashtirish yoki yangi hisoblashni bloklovchi tekshiruv. |

### 1.2. Bounded contextlar

1. **Methodology Registry** — global katalog, versiya kontenti, publish lifecycle, content hash va licence metadata. Oddiy tenant foydalanuvchisi bu kontentni yaratmaydi.
2. **Research Configuration** — tenantga tegishli tadqiqot va aniq `methodology_version_id` pin'i, norm tanlovi, PII/consent/retention siyosati.
3. **Response Collection** — participant, response, immutable revision, manual/import provenance va validatsiya.
4. **Scoring** — release/consent/state gate, deterministik pipeline, idempotent run, result va trace.
5. **Import** — fayl, template/mapping, preview, row/cell error va foydalanuvchi confirmation'i.
6. **Governance** — tenant isolation, authorization, consent, PII vault, audit, retention/legal hold.

Contextlar bir-birining jadvalini yashirincha o'zgartirmaydi. Masalan, Scoring javobni tahrirlamaydi; Methodology Registry published snapshot'ni mutate qilmaydi; retention o'chirishlari Governance workflow orqali bajariladi.

## 2. Umumiy identifikator va format qoidalari

- Barcha ichki primary ID'lar UUID bo'ladi va API/omborda string ko'rinishida lowercase canonical UUID sifatida beriladi.
- Inson o'qiydigan `*_code` maydonlar locale'dan mustaqil, immutable va regex `^[a-z][a-z0-9_]{1,63}$` ga mos bo'ladi.
- `version_code` SemVer'ning qat'iy `MAJOR.MINOR.PATCH` ko'rinishida bo'ladi; build metadata MVPda taqiqlanadi.
- Sana-vaqt UTC ISO-8601 (`YYYY-MM-DDTHH:mm:ss.SSSZ`) ko'rinishida saqlanadi. Foydalanuvchi timezone'i faqat presentation concern.
- Sana `YYYY-MM-DD`; til BCP-47 (`uz-Latn`, `ru`, `en`); hudud ISO 3166-1 alpha-2 yoki mahsulot tasdiqlagan hudud guruhi kodi.
- Score va formula konstantalari JSON number sifatida qabul qilinsa ham backend ularni binary float emas, fixed precision decimal sifatida parse qiladi. `NaN`, `Infinity`, scientific notation va `-0` rad etiladi.
- Lokalizatsiyalangan label/prompt barqaror object ko'rinishida: `{ "uz-Latn": "...", "ru": "..." }`. Kamida versiyaning `default_locale` qiymati mavjud bo'lishi shart.
- Har bir tenant-owned yozuvda `tenant_id`; har bir research-owned yozuvda `tenant_id` va `research_id` birga saqlanadi. Foreign key va query ikkalasi ham tenantni tekshiradi.

## 3. Metodika domen modeli

Quyidagi maydonlar logical schema hisoblanadi. `required` deyilmagan nullable maydonlar aniq ko'rsatiladi; qolganlari majburiy.

### 3.1. `Methodology`

| Field | Type | Constraint |
| --- | --- | --- |
| `methodology_id` | UUID | PK |
| `methodology_code` | code | Global unique, immutable |
| `canonical_name` | string(1..200) | Trimmed |
| `purpose_summary` | string(1..2000) | Tashxis da'vosi bo'lmasligi kerak |
| `owner_name` | string(1..300) | Muallif/huquq egasi |
| `source_reference` | string(1..1000) | Bibliografik yoki himoyalangan reference |
| `catalog_status` | enum | `active`, `retired` |
| `created_at`, `created_by` | timestamp, UUID | Audit provenance |

Invariantlar:

- `methodology_code` o'zgarmaydi va qayta ishlatilmaydi.
- `retired` katalog identiteti oldingi versiya/natijalarni o'chirmaydi.
- Global katalog tenant ma'lumoti emas; tenant kontekstida foydalanish licence gate orqali aniqlanadi.

### 3.2. `MethodologyVersion`

| Field | Type | Constraint |
| --- | --- | --- |
| `methodology_version_id` | UUID | PK |
| `methodology_id` | UUID | FK `Methodology` |
| `version_code` | SemVer | Unique (`methodology_id`, `version_code`) |
| `schema_version` | string | MVPda `methodology-contract/1` |
| `default_locale` | BCP-47 | Prompt/labelda mavjud |
| `supported_locales` | string[] | Unique, non-empty |
| `target_population` | structured object | Adult-only flag, tavsif va cheklovlar |
| `estimated_minutes` | integer | 1..1440 |
| `lifecycle_status` | enum | `draft`, `in_review`, `published`, `deprecated`, `withdrawn` |
| `content_hash` | string | Published paytda canonical JSON'ning `sha256:<hex>` qiymati |
| `engine_contract_version` | string | Masalan `scoring/1` |
| `disclaimer_i18n` | localized string | “Tibbiy tashxis emas” ma'nosi majburiy |
| `published_at`, `published_by` | nullable timestamp, UUID | Faqat published yoki keyingi statusda |
| `supersedes_version_id` | nullable UUID | Shu methodology'ning oldingi versiyasi |

`target_population` minimal ko'rinishi:

```json
{
  "adults_only": true,
  "min_age": 18,
  "max_age": null,
  "description_i18n": {"uz-Latn": "18 yosh va undan katta ishtirokchilar"},
  "exclusions_i18n": {"uz-Latn": "Voyaga yetmaganlar MVPda qo'llanmaydi"}
}
```

Invariantlar:

- Published snapshot ichidagi item, option, scale, scoring, norm va interpretation yozuvlari immutable.
- `content_hash` canonicalized snapshotning barcha hisoblashga ta'sir qiluvchi kontentini qamraydi; licence statusi alohida lifecycle bo'lgani uchun hashga kirmaydi, ammo licence record/version run provenance'iga kiradi.
- Bir versiyada kamida bitta item va bitta `total` scale bo'ladi.
- `published` bo'lish publish uchun zarur, lekin yangi foydalanish uchun yetarli emas; licence gate ham o'tishi kerak.

### 3.3. `Scale`

| Field | Type | Constraint |
| --- | --- | --- |
| `scale_id` | UUID | PK |
| `methodology_version_id` | UUID | FK |
| `scale_code` | code | Unique within version |
| `scale_kind` | enum | `total`, `subscale`; aynan bitta `total` majburiy |
| `label_i18n` | localized string | Default locale majburiy |
| `unit_code` | code | Masalan `raw_point`, `percent_0_100` |
| `theoretical_min`, `theoretical_max` | decimal | `min < max` |
| `display_decimals` | integer | 0..6 |
| `aggregation` | object | 6-bo'limdagi deklarativ config |
| `transform_expr` | nullable expression AST | Aggregate score'dan display score olish |
| `validity_rules` | rule AST[] | Pre/post aggregate qoidalar |
| `norm_set_ids` | UUID[] | Shu version ichidagi normlar |
| `sort_order` | integer | Version ichida unique |

Bir item bir nechta subshkalaga kirishi mumkin, lekin har bir `ScaleItemLink` aniq weight va order beradi:

```json
{
  "scale_id": "<uuid>",
  "item_id": "<uuid>",
  "weight": "1",
  "sort_order": 1
}
```

Unique constraint: (`scale_id`, `item_id`). Weight `-1000..1000`, zero taqiqlanadi. Reverse scoring item assignment darajasida bo'lgani uchun bir item turli scale'da turlicha reverse bo'lishi kerak bo'lsa MVPda qo'llanmaydi; bunday metodika alohida derived item dizaynini talab qiladi va publish gate'dan o'tmaydi.

### 3.4. `Item`

| Field | Type | Constraint |
| --- | --- | --- |
| `item_id` | UUID | PK |
| `methodology_version_id` | UUID | FK |
| `item_code` | code | Unique within version, immutable |
| `item_type` | enum | 4-bo'limdagi whitelist |
| `prompt_i18n` | localized string | Licence disclosure'ga bo'ysunadi |
| `required` | boolean | Default `true` |
| `value_constraints` | object | Type-specific min/max/step |
| `missing_policy` | object | 6.3-bo'lim |
| `score_mapping` | object | Raw answer → decimal score |
| `reverse_scoring` | object | `none`, `range`, `explicit_map` |
| `item_transform_expr` | nullable expression AST | Reverse'dan keyingi transform |
| `sort_order` | integer | Version ichida unique |

Invariantlar:

- Item code revisionlar va import header uchun barqaror kalit; prompt text kalit emas.
- `required=true` va scale missing policy bir-biriga zid bo'lmasligi kerak: required item bo'sh bo'lsa revision validate qilinmaydi.
- `range` reverse faqat score mapping natijasining aniq finite min/max'i bo'lsa ruxsat.
- Prompt yoki label hisoblash qoidasi bo'la olmaydi.

### 3.5. `ResponseOption`

| Field | Type | Constraint |
| --- | --- | --- |
| `response_option_id` | UUID | PK |
| `item_id` | UUID | FK |
| `option_code` | code | Unique within item |
| `label_i18n` | localized string | Default locale majburiy |
| `ordinal_position` | integer | 0..1000, unique within item |
| `score_value` | decimal string | Mapping qiymati; duplicate score ruxsat |
| `is_active` | boolean | Published snapshotda doim true |

Option label import qiymati sifatida ishlatilmaydi; faqat `option_code` canonical qiymat hisoblanadi.

### 3.6. `NormSet` va `NormBand`

`NormSet`:

| Field | Type | Constraint |
| --- | --- | --- |
| `norm_set_id` | UUID | PK |
| `methodology_version_id`, `scale_id` | UUID | Bir version/scale |
| `norm_code` | code | Unique within scale |
| `label_i18n` | localized string | Required |
| `norm_kind` | enum | MVP: `threshold_bands`, `lookup_table` |
| `population_descriptor` | object | Manba, populyatsiya, hudud, yosh diapazoni |
| `selection_constraints` | object | Research config bilan exact match qilinadigan kodlar |
| `source_reference` | string | Majburiy; sintetik bo'lsa shunday belgilanadi |
| `is_default` | boolean | Har scale uchun ko'pi bilan bitta |
| `lookup_mode` | enum | `exact`; interpolatsiya MVPda yo'q |

`threshold_bands` uchun `NormBand`:

| Field | Type | Constraint |
| --- | --- | --- |
| `norm_band_id` | UUID | PK |
| `norm_set_id` | UUID | FK |
| `band_code` | code | Unique within norm set |
| `lower_bound` | nullable decimal | `null` = -∞ |
| `lower_inclusive` | boolean | Required |
| `upper_bound` | nullable decimal | `null` = +∞ |
| `upper_inclusive` | boolean | Required |
| `normalized_value` | nullable decimal | Masalan percentile emas, faqat taqdim etiladigan norm qiymati |
| `label_i18n` | localized string | Required |
| `sort_order` | integer | Unique |

Bandlar overlap qilmaydi. Published normda score domeni bo'shliqsiz qoplanishi yoki coverage tashqarisi uchun aniq `NO_NORM_MATCH` xatosi belgilanishi shart. Boundary semantikasi explicit; implicit `<=` taxmini yo'q. `lookup_table` exact raw-key → normalized-value jadvali bo'lib, duplicate key taqiqlanadi.

Demografiyaga asoslangan normni avtomatik tanlash MVPda yo'q. Research `norm_set_id` ni Active bo'lishdan oldin explicit pin qiladi. Agar kerakli norm profili ishtirokchi demografiyasiga mosligi tekshirilsa, faqat oldindan ruxsat etilgan strukturali maydon ishlatiladi; PII yoki erkin matn formula input'i bo'lmaydi.

### 3.7. `InterpretationRule`

| Field | Type | Constraint |
| --- | --- | --- |
| `interpretation_rule_id` | UUID | PK |
| `methodology_version_id`, `scale_id` | UUID | FK |
| `rule_code` | code | Unique within scale |
| `priority` | integer | 1..10000, unique within scale |
| `when` | rule AST | Boolean natija |
| `interpretation_code` | code | Stable output code |
| `title_i18n`, `text_i18n` | localized string | Oldindan tasdiqlangan, generativ emas |
| `disclaimer_i18n` | localized string | Version disclaimer'ini bekor qila olmaydi |
| `requires_valid_result` | boolean | MVPda doim true |

Rules priority bo'yicha tekshiriladi; birinchi true rule tanlanadi. Publish validator bir xil input uchun ikki rule bir priority'da ishlamasligini va kutilgan score domeni coverage'ini tekshiradi. Hech biri mos kelmasa talqin yaratilmaydi, `NO_INTERPRETATION_MATCH` reason saqlanadi; score o'zi valid qolishi mumkin.

### 3.8. `Licence`

| Field | Type | Constraint |
| --- | --- | --- |
| `licence_id` | UUID | PK |
| `methodology_version_id` | UUID | FK; har version uchun kamida bitta record |
| `licence_revision` | integer | 1 dan monoton oshadi; immutable revision |
| `status` | enum | `verified`, `restricted`, `expired`, `revoked`, `unknown` |
| `copyright_status` | enum | `copyrighted`, `public_domain`, `permission_granted`, `unknown` |
| `rights_holder` | string | Required |
| `evidence_reference` | protected string/reference | Required; oddiy userga ochilmaydi |
| `allowed_use_types` | enum[] | `research`, `education`, `clinical`; non-empty |
| `allowed_org_types` | enum[] | Product scope'dagi org kodlari |
| `allowed_regions` | string[] | Non-empty; global uchun `GLOBAL` |
| `content_disclosure_level` | enum | `full`, `derived_only`, `summary_only` |
| `allow_item_display` | boolean | Prompt UIda ko'rinishi |
| `allow_item_export` | boolean | Prompt/answer label eksporti |
| `allow_trace_item_values` | boolean | Trace'da item-level raw/scored qiymatlar |
| `valid_from`, `valid_until` | date | `valid_until` nullable; from ≤ until |
| `required_disclaimer_i18n` | localized string | Required |
| `restrictions_i18n` | localized string | Required |
| `verified_by`, `verified_at` | UUID, timestamp | Platform admin |
| `change_reason` | string | Har revisionda required |

Release gate o'tishi uchun eng yangi licence revision: `status=verified`, current UTC date interval ichida, research use type/org type/region bilan mos va barcha majburiy metadata'ga ega bo'lishi kerak. `restricted` ma'lumot beruvchi holat, ammo MVP release gate uchun yaroqsiz. Status o'zgarishi published methodology snapshot'ni mutate qilmaydi; yangi hisoblashni darhol bloklaydi, oldingi resultni read-only saqlaydi.

## 4. Item va answer turlari: MVP whitelist

| `item_type` | Canonical answer | Validatsiya | Scoring |
| --- | --- | --- | --- |
| `single_choice` | `option_code` string | Option shu itemga tegishli | Option `score_value` |
| `integer` | JSON integer / CSV base-10 integer | Inclusive min/max; step | Identity yoki expression |
| `decimal` | Canonical decimal string | Inclusive min/max; scale ≤ 6 | Identity yoki expression |
| `boolean` | JSON boolean / CSV `true` yoki `false` | Boshqa literal yo'q | Explicit `{true, false}` map |

MVP cheklovlari:

- `multi_select`, ranking, matrix/grid, free text, file, audio/video, biometrika, sana/vaqt va computed branching item yo'q.
- Free text default o'chiq va bu kontraktda scoring input'i emas.
- Bir itemga bitta answer; takror column yoki takror item answer validatsiya xatosi.
- Locale label (`Ha`, `Да`, `Yes`) canonical boolean/option o'rnida qabul qilinmaydi.
- Skip logic va adaptive testing yo'q. Barcha itemlar versiondagi statik tartibda.

Canonical answer object:

```json
{
  "item_code": "q1",
  "value": {"type": "single_choice", "option_code": "often"}
}
```

Missing answer item objectini tashlab ketish yoki `value: null` bilan ifodalanadi; ikkalasi normalization paytida yagona `MISSING` holatga o'tadi. Empty string score qiymati emas.

## 5. Xavfsiz deklarativ formula va rule formati

### 5.1. Asosiy prinsip

Formula JSON AST bo'ladi. Arbitrary source code, Python/JavaScript expression, template execution, SQL fragment, dynamic import, reflection va har qanday `eval`/`exec` qat'iyan taqiqlanadi. AST faqat whitelist operator va typed reference'lardan tuziladi.

Expression node'lari:

```json
{"op": "const", "value": "10"}
{"op": "ref", "kind": "aggregate", "code": "total"}
{"op": "add", "args": [{"op": "ref", "kind": "aggregate", "code": "total"}, {"op": "const", "value": "1"}]}
{"op": "div", "left": {"op": "ref", "kind": "aggregate", "code": "total"}, "right": {"op": "const", "value": "12"}}
```

MVP numeric operator whitelist:

- `const`, `ref`
- `add`, `sub`, `mul`, `div`
- `min`, `max`, `abs`
- `round` (`decimals` 0..6, mode faqat `half_up`)

MVP boolean/rule whitelist:

- `eq`, `ne`, `lt`, `lte`, `gt`, `gte`
- `and`, `or`, `not`
- `is_missing`, `is_valid`
- `in` — faqat compile-time literal scalar array, maksimum 100 element

Operator node shape'i qat'iy; qo'shimcha field (`additionalProperties`) ruxsat etilmaydi:

| Operator | Majburiy field | Arity/natija |
| --- | --- | --- |
| `const` | `value` | Numeric kontekstda canonical decimal string; rule kontekstida string/boolean ham mumkin |
| `ref` | `kind`, `code` kerak bo'lsa | Typed scalar; `code` faqat declared entity code |
| `add`, `mul`, `min`, `max` | `args` | 2..100 numeric node; numeric |
| `sub`, `div` | `left`, `right` | Aynan 2 numeric node; numeric |
| `abs` | `value` | 1 numeric node; numeric |
| `round` | `value`, `decimals`, `mode` | 1 numeric node; `mode=half_up` |
| `eq`, `ne`, `lt`, `lte`, `gt`, `gte` | `left`, `right` | Aynan bir xil compatible typed scalarlar; boolean |
| `and`, `or` | `args` | 2..100 boolean node; boolean, source orderda short-circuit |
| `not` | `value` | 1 boolean node; boolean |
| `is_missing` | `value` | 1 allowed ref; boolean |
| `is_valid` | `value` | 1 scale/validity ref; boolean |
| `in` | `value`, `set` | 1 scalar node va 1..100 unique literal; boolean |

AST evaluator object key tartibiga tayanmaydi; `args` array tartibi saqlanadi. `sub` va `div` hech qachon n-ary talqin qilinmaydi.

Allowed `ref.kind` va scope:

- item transformda: `item_raw_score`, `item_reversed_score`;
- scale transformda: `aggregate` va aynan joriy `scale_code`;
- validity'da: `answered_count`, `missing_count`, `item_score`, `aggregate`, `transformed_score`;
- interpretation'da: `transformed_score`, `norm_band_code`, `normalized_value`, `validity_status`.

Path traversal (`a.b`), arbitrary object property, environment variable, clock, random, network va database query reference sifatida ruxsat etilmaydi. Joriy sana faqat licence gate input'i bo'lib, formula input'i emas.

### 5.2. Compile/publish validatsiyasi

Publish oldidan validator:

1. JSON Schema va operator whitelist'ni tekshiradi.
2. Reference mavjudligini, to'g'ri scope/type va dependency cycle yo'qligini tekshiradi.
3. Node chuqurligi ≤ 20, jami node ≤ 500, `args` ≤ 100 bo'lishini tekshiradi.
4. Nolga bo'lish ehtimolini statik yoki test domain bilan aniqlasa publish'ni bloklaydi; runtime'da qolsa `DIVISION_BY_ZERO` bilan run fail bo'ladi.
5. Decimal konstantaning precision'i ≤ 18, scale'i ≤ 6 bo'lishini tekshiradi.
6. Formula result'i declared theoretical range'dan chiqmasligini test vectorlar orqali tekshiradi; isbotlanmasa admin review talab qiladi.
7. Noma'lum field/operatorni forward-compatible deb jim qabul qilmaydi; qat'iy rad etadi.

Runtime interpreter faqat compiled, content hash bilan tasdiqlangan ASTni bajaradi. Timeout/step budget oshsa `RULE_LIMIT_EXCEEDED`; partial score yoki interpretatsiya saqlanmaydi.

## 6. Deterministik scoring pipeline

Har run quyidagi tartibda bajariladi. Bosqich o'tkazib yuborilsa ham trace'da `skipped` va sabab bo'ladi.

### 6.1. 0-bosqich: execution gate

Quyidagilardan biri bajarilmasa run boshlanmaydi yoki `blocked` tugaydi:

- tenant/research authorization yaroqli;
- research `Active`;
- participant processing holati yaroqli;
- consent `granted` yoki admin tasdiqlagan `not_required_with_basis` va withdrawal yo'q;
- revision `validated` va current response head revision bilan mos;
- pinned version `published`; licence ayni hisoblash vaqtida release gate'dan o'tadi;
- pinned version/content hash va norm set research konfiguratsiyasi bilan mos.

`Paused`, `Closed`, `Archived`, deletion pending researchda yangi hisoblash yo'q. Konservativ MVP qoidasi bo'yicha `deprecated` yoki `withdrawn` versiya ham yangi runni bloklaydi. Licence `revoked/expired/unknown/restricted` bo'lsa oldingi result ko'rinishi mumkin, yangi run bloklanadi.

### 6.2. 1-bosqich: structural va value validation

- Item code'lar aynan pinned versionga tegishli.
- Duplicate va noma'lum item yo'q.
- Type, range, step va option membership to'g'ri.
- Required item missing emas.
- Bir revisionning canonical answer payload hash'i qayta hisoblanadi.

Xato bo'lsa revision `validation_failed`; scoring chaqiruvi `RESPONSE_NOT_VALIDATED` bilan rad qilinadi.

### 6.3. 2-bosqich: normalization va missing

Normalization locale'dan mustaqil: integer/decimal parse, boolean literal, option code. Missing faqat absent/null/CSV empty cell orqali keladi; `NA`, `N/A`, `null`, `-`, `0` magic missing code emas.

Item `missing_policy`:

```json
{
  "mode": "allow",
  "counts_as_missing": true
}
```

`mode`: `forbid` yoki `allow`. Scale aggregation qo'shimcha ravishda:

```json
{
  "op": "sum_prorated",
  "min_answered": 3,
  "max_missing": 1,
  "target_item_count": 4
}
```

Aggregation whitelist: `sum`, `mean`, `weighted_sum`, `sum_prorated`. Median, z-score estimation va model-based imputation MVPda yo'q.

- `sum`: missing mavjud bo'lsa faqat `max_missing` ichida; missing item sumga qo'shilmaydi.
- `mean`: answered scorelar arifmetik o'rtachasi.
- `weighted_sum`: `Σ(score × weight)`; missing weight denominatorga kirmaydi.
- `sum_prorated`: `sum(answered scores) / answered_count × target_item_count`.

`min_answered` va `max_missing` ikkalasi bajarilishi shart. Bajarilmasa scale `insufficient_data`, transform/norm/interpretation skipped. Missing qiymatga yashirincha zero berilmaydi.

### 6.4. 3-bosqich: option mapping va raw item score

- `single_choice`: exact option code → `score_value`.
- numeric: default identity yoki declared mapping/expression.
- boolean: explicit map; masalan `{ "true": "1", "false": "0" }`.
- Mapping topilmasa `MAPPING_NOT_FOUND`; run `failed`, uydirma score yo'q.

### 6.5. 4-bosqich: reverse scoring

`none`: score o'zgarmaydi.

`range`:

```json
{"mode": "range", "min_score": "0", "max_score": "3"}
```

Formula qat'iy: `reversed = min_score + max_score - raw_item_score`.

`explicit_map`:

```json
{
  "mode": "explicit_map",
  "map": {"0": "3", "1": "2", "2": "1", "3": "0"}
}
```

Explicit map barcha mumkin scorelarni qoplashi kerak. Reverse mapping raw answerga emas, 3-bosqichdagi decimal scorega qo'llanadi. Missing missingligicha qoladi.

### 6.6. 5-bosqich: item transform

Optional `item_transform_expr` reverse'dan keyin ishlaydi. Expression yo'q bo'lsa transformed item score = reversed (yoki raw, reverse yo'q bo'lsa). Item-level rounding qilinmaydi, faqat formula explicit `round` operator ishlatsa qilinadi.

### 6.7. 6-bosqich: scale aggregate

`ScaleItemLink` tartibida item scorelar olinadi, missing qoidalari tekshiriladi va declared aggregation bajariladi. Decimal amallar precision 28 kontekstda, overflow limit ±`10^18` bilan. Natija `aggregate_score_unrounded` sifatida trace qilinadi.

### 6.8. 7-bosqich: scale transform

`transform_expr` aggregate score'ni scale birligiga o'tkazadi. Transform yo'q bo'lsa score aggregate'ning o'zi. Result `score_unrounded` sifatida saqlanadi. Theoretical range'dan tashqari qiymat `SCORE_OUT_OF_RANGE` bilan scale'ni invalid qiladi.

### 6.9. 8-bosqich: validity

Validity qoidalar ikki paytda ishlashi mumkin:

- `pre_aggregate`: answered/missing va item score consistency;
- `post_transform`: transformed score diapazoni yoki deklarativ consistency.

Natija enum: `valid`, `insufficient_data`, `invalid_response_pattern`, `calculation_error`. Validity false bo'lsa norm va interpretatsiya berilmaydi. MVPda “lie scale” yoki klinik validity flag faqat metodika versiyasida qonuniy va psixometrik asos bilan oldindan deklaratsiya qilingan bo'lsa qo'llanadi; platforma o'zi bunday qoidani ixtiro qilmaydi.

### 6.10. 9-bosqich: norm/threshold

- Research pin qilgan `norm_set_id` aynan shu version/scale'ga tegishli ekanligi tekshiriladi.
- Threshold taqqoslash `score_unrounded` bilan bajariladi.
- Boundary explicit inclusive/exclusive qoidaga amal qiladi.
- Bir banddan ko'p mos kelsa `NORM_OVERLAP` — publish paytida ushlanishi kerak bo'lgan fatal config error.
- Mos band yo'q bo'lsa score saqlanadi, norm `not_available` va interpretatsiya skipped.
- Lookup faqat exact; interpolatsiya va extrapolatsiya yo'q.

### 6.11. 10-bosqich: interpretatsiya

Faqat valid score uchun priority tartibida `InterpretationRule.when` ishlaydi. Birinchi true tanlanadi. Text oldindan versionda mavjud; AI/generativ text yo'q. Rule natijasi tibbiy tashxis sifatida nomlanmaydi va required disclaimer doim biriktiriladi.

### 6.12. 11-bosqich: rounding, persist va hash

- Hisob, threshold va rule evaluation doim unrounded decimal bilan.
- Faqat yakuniy presentation `score_display = round(score_unrounded, display_decimals, HALF_UP)`.
- `score_unrounded` canonical decimal string sifatida precision'i bilan saqlanadi; `score_display` ham string.
- Result, scale result, trace va provenance bitta transaction boundary'da immutable saqlanadi. Partial successful result yo'q.
- `result_hash = SHA-256(canonical result payload + trace hash + methodology content hash + engine version)`.

## 7. Explainability trace va disclosure

### 7.1. Trace modeli

```json
{
  "trace_id": "<uuid>",
  "calculation_run_id": "<uuid>",
  "trace_schema_version": "explainability/1",
  "disclosure_level_applied": "derived_only",
  "methodology_content_hash": "sha256:...",
  "response_revision_hash": "sha256:...",
  "steps": [
    {
      "sequence": 1,
      "step_code": "item_reverse",
      "status": "completed",
      "entity_ref": {"kind": "item", "code": "q2"},
      "rule_ref": "reverse:range:0:3",
      "inputs": [{"name": "raw_score", "value": "3"}],
      "outputs": [{"name": "reversed_score", "value": "0"}],
      "reason_code": null,
      "message_key": "trace.item_reverse.range",
      "redactions": []
    }
  ],
  "trace_hash": "sha256:..."
}
```

Har stepda `sequence` contiguous va unique; `status`: `completed`, `skipped`, `blocked`, `failed`. `reason_code` skipped/blocked/failed uchun majburiy. `message_key` lokalizatsiya kaliti, hisoblash haqiqati esa structured input/output'da. Trace UI matniga bog'liq emas.

Majburiy step code'lar: `execution_gate`, `response_validation`, `normalize_answer`, `missing_check`, `option_mapping`, `item_reverse`, `item_transform`, `scale_aggregate`, `scale_transform`, `validity_check`, `norm_select`, `norm_match`, `interpretation_select`, `round_display`, `result_persist`.

### 7.2. Disclosure darajalari

Effective disclosure licence restrictionlarining eng qat'iysi bilan aniqlanadi; user roli uni kengaytira olmaydi.

| Level | Ko'rinadigan mazmun |
| --- | --- |
| `full` | Licence ruxsat bersa item code/prompt, raw answer, mapping, reverse va barcha oraliq qiymat. PII baribir yo'q. |
| `derived_only` | Item code va numeric derived scorelar; prompt/option label/raw textual answer redacted. |
| `summary_only` | Scale-level answered/missing count, aggregation/transform turi, final score, norm va reason; item-level qiymatlar yo'q. |

Trace storage'da ham “ko'rsatmay turib to'liq sirni saqlash” avtomatik ruxsat emas. `allow_trace_item_values=false` bo'lsa persisted public trace item qiymatlarini saqlamaydi; hisoblash uchun zarur internal event maxfiy operational logga ko'chirilmaydi. Audit trace scoring sirini yoki PII'ni nusxalamaydi.

Export aynan effective disclosure'ga amal qiladi. Oldingi result uchun licence keyin toraytirilsa, immutable internal trace saqlanishi retentionga bog'liq, ammo keyingi view/export yangi disclosure policy bilan redakt qilinadi.

## 8. Version lifecycle, pinning va reproducibility

### 8.1. Lifecycle

Allowed transitionlar:

```text
draft -> in_review -> published -> deprecated -> withdrawn
  ^        |
  +--------+  (review rad etilib draftga, sabab bilan)
```

- `draft`: tahrirlanadi, researchga pin qilinmaydi.
- `in_review`: kontent freeze; reviewer approve yoki sabab bilan draftga qaytaradi.
- `published`: immutable va yangi researchga licence gate bilan tanlanadi.
- `deprecated`: immutable; yangi researchga pin va yangi run konservativ MVP qoidasi bo'yicha bloklanadi. Product/yuridik siyosat keyin ruxsat bersa bu alohida kontrakt versiyasida o'zgartiriladi.
- `withdrawn`: yangi pin va yangi hisoblash bloklanadi; oldingi result audit/retention uchun read-only.

Published versiyaga typo tuzatish ham yangi `version_code` talab qiladi. Locale text, scoring rule, norm yoki disclosure-relevant kontent o'zgarishi yangi snapshotdir.

### 8.2. Research pinning

Research konfiguratsiyasi quyidagilarni saqlaydi:

```json
{
  "methodology_version_id": "<uuid>",
  "methodology_content_hash": "sha256:...",
  "norm_selection": {"total": "<norm_set_uuid>"},
  "pinned_at": "2026-07-15T12:00:00.000Z",
  "pinned_by": "<user_uuid>"
}
```

Research `Active` bo'lgach bu maydonlar immutable. Boshqa versiya/norm uchun yangi research kerak. Har run pinned ID va hashni qayta tekshiradi; mismatch fatal integrity error.

### 8.3. Reproducibility tuple

Bir natijani qayta isbotlash uchun kamida:

`tenant_id + research_id + response_revision_id + response_revision_hash + methodology_version_id + methodology_content_hash + norm_set_ids + licence_id/licence_revision_at_run + scoring_engine_version + rule_interpreter_version + rounding_policy_version`.

Engine upgrade oldingi resultni avtomatik qayta yozmaydi. Aynan bir tuple bilan recalculation bir xil canonical result hash berishi shart. Engine versioni o'zgarsa bu yangi computation provenance; product ruxsatisiz tarixiy revisionga “yangilangan” natija yaratmaydi.

## 9. Response, revision, run va result modeli

### 9.1. Bog'lanish

```text
Research 1 ── * Participant 1 ── * Response 1 ── * ResponseRevision
                                      │                    │
                                      │                    └── * CalculationRun 0..1 Result
                                      └── current_revision_id
```

### 9.2. `Response`

| Field | Type | Constraint |
| --- | --- | --- |
| `response_id` | UUID | PK |
| `tenant_id`, `research_id`, `participant_id` | UUID | Same-tenant composite FK |
| `attempt_key` | code/string | Unique (`research_id`,`participant_id`,`attempt_key`) |
| `methodology_version_id` | UUID | Research pin bilan teng |
| `current_revision_id` | nullable UUID | Shu response revisioni |
| `status` | enum | `draft`, `validation_failed`, `validated`, `scored`, `withdrawn`, `anonymized`, `deleted` |
| `lock_version` | integer | Optimistic concurrency |
| `created_at`, `created_by` | provenance | Required |

Default `attempt_key=initial`. Takroriy o'lchov product qarorigacha default bloklangan; ruxsat berilsa explicit unique attempt key talab qilinadi.

### 9.3. `ResponseRevision`

| Field | Type | Constraint |
| --- | --- | --- |
| `response_revision_id` | UUID | PK |
| `tenant_id`, `research_id`, `response_id` | UUID | Composite scope |
| `revision_number` | integer | 1 dan monoton; unique per response |
| `answers` | canonical JSON | Item code bo'yicha sorted snapshot |
| `answer_payload_hash` | SHA-256 | Canonical answers hash |
| `status` | enum | `draft`, `validation_failed`, `validated`, `superseded`, `withdrawn` |
| `validation_summary` | object | Error/warning counts va validator version |
| `source_type` | enum | `manual`, `csv_import`, `xlsx_import` |
| `source_ref` | nullable UUID | Import row yoki manual event |
| `correction_reason` | nullable string | Revision > 1 uchun required |
| `created_at`, `created_by` | provenance | Required |
| `validated_at`, `validated_by` | nullable | Validated uchun required |

Validated revision immutable. Tuzatish clone + change orqali yangi draft revision; avvalgi `superseded`, unga bog'langan result o'zgarmaydi. Concurrent update `lock_version` mismatch bo'lsa `REVISION_CONFLICT`.

### 9.4. `CalculationRun`

| Field | Type | Constraint |
| --- | --- | --- |
| `calculation_run_id` | UUID | PK |
| `tenant_id`, `research_id`, `response_revision_id` | UUID | Scoped FK |
| `idempotency_key` | string(1..200) | Client request key |
| `computation_key` | SHA-256 | Quyidagi canonical tuple hash |
| `status` | enum | `queued`, `running`, `succeeded`, `blocked`, `failed` |
| `engine_version`, `rule_interpreter_version` | string | Required |
| `methodology_version_id`, `methodology_content_hash` | value | Required |
| `licence_id`, `licence_revision` | value | Gate'da ishlatilgan revision |
| `started_at`, `finished_at` | nullable timestamp | State'ga mos |
| `initiated_by` | UUID | Actor/service principal |
| `failure_code` | nullable code | No sensitive detail |
| `diagnostic_ref` | nullable opaque ID | Internal, PII yo'q |
| `retry_count` | integer | Default 0; faqat allowlisted transient failure uchun oshadi |

`computation_key = hash(tenant_id, research_id, response_revision_id, answer_payload_hash, methodology_content_hash, norm_selection, engine_version, interpreter_version, rounding_policy_version)`.

Unique constraint (`tenant_id`, `computation_key`) bo'yicha aynan bitta logical run bo'lishini ta'minlaydi. Atomic insert/claim sabab bir xil key bilan parallel so'rovdan bittasi hisoblaydi, boshqasi ongoing yoki mavjud resultga yo'naltiriladi. Allowlisted transient texnik xatoda shu run audit bilan qayta navbatga qo'yiladi va `retry_count` oshadi; yangi logical run/result yaratilmaydi. Bir xil `idempotency_key` boshqa payload/computation key bilan kelsa `IDEMPOTENCY_KEY_REUSED`.

### 9.5. `Result` va `ScaleResult`

`Result`:

- `result_id`, `tenant_id`, `research_id`, `participant_id`, `response_id`, `response_revision_id`, `calculation_run_id`;
- `methodology_version_id`, `methodology_content_hash`;
- `status`: `complete`, `complete_with_uninterpreted_scales`; failed result record yaratilmaydi;
- `disclaimer_i18n_snapshot`, `calculated_at`, `calculated_by`;
- `trace_id`, `result_hash`, `retention_classification`.

`ScaleResult`:

- `scale_result_id`, `result_id`, `scale_id`, `scale_code`;
- `validity_status`, `reason_codes[]`;
- `answered_count`, `missing_count`;
- `aggregate_score_unrounded`, `score_unrounded`, `score_display`, `unit_code`;
- `norm_set_id`, `norm_band_code`, `normalized_value` nullable;
- `interpretation_rule_id`, `interpretation_code`, `interpretation_snapshot_i18n` nullable;
- `disclosure_level_applied`.

Unique (`result_id`, `scale_id`). Result immutable; correction yangi revision/run/result yaratadi. “Latest result” derived query bo'lib, tarixiy natijani o'chirmaydi.

## 10. CSV import kontrakti

### 10.1. Canonical CSV

- Encoding: UTF-8, BOM optional; delimiter comma; RFC 4180 quoting; header exactly once.
- Import limit konfiguratsion; limit oshsa hech bir row persist qilinmaydi.
- Canonical reserved columns:

```csv
_methodology_code,_version_code,_template_id,participant_external_code,attempt_key,collected_at,item.q1,item.q2,item.q3,item.q4
synth_balance_demo,1.0.0,tmpl_abc123,P-001,initial,2026-07-15T10:30:00.000Z,2,3,1,0
```

Majburiy: `_methodology_code`, `_version_code`, `_template_id`, `participant_external_code`, barcha required `item.<item_code>`. `attempt_key` bo'sh bo'lsa `initial`; `collected_at` optional. Metadata qiymatlari har rowda bir xil va research pin bilan exact match.

Anonymous researchda `participant_external_code` platforma tashqarisidagi qayta identifikatsiya kaliti bo'lmasligi kerak; tizim uni research-scoped opaque code deb qabul qiladi. Ism, email, telefon kabi PII canonical response CSVda yo'q. Participant/consent avval mavjud bo'lishi yoki alohida vakolatli participant import workflow'da yaratilishi kerak; response CSV consent yaratmaydi.

Canonical cell qoidalari:

- missing = empty unquoted/quoted cell;
- `single_choice` = option code;
- `integer` = `-12`, `0`, `42`; `1.0` rad;
- `decimal` = nuqta separatorli base-10 (`12.5`); comma decimal va scientific notation rad;
- `boolean` = lowercase `true`/`false`;
- whitespace trim qilinadi, ammo trim collision/empty validation qilinadi.

Unknown column default fatal `UNKNOWN_COLUMN`; anonymous researchda PIIga o'xshash header `PII_COLUMN_FORBIDDEN`. Duplicate header fatal. Bir faylda participant code + attempt key duplicate bo'lsa ikkala row xato; auto-merge yo'q.

### 10.2. Mapping

Canonical template afzal. Tashqi header mapping faqat preview bosqichida explicit yaratiladi:

```json
{
  "mapping_id": "<uuid>",
  "methodology_version_id": "<uuid>",
  "template_id": "tmpl_abc123",
  "source_headers_hash": "sha256:...",
  "columns": [
    {"source": "Participant", "target": "participant_external_code"},
    {"source": "Question 1", "target": "item.q1"}
  ],
  "created_by": "<uuid>",
  "created_at": "2026-07-15T10:00:00.000Z"
}
```

Bir source faqat bir targetga, bir target faqat bir sourcega. Required targetlarning barchasi map qilinadi. Mapping label/position asosida taxminiy auto-match qilmaydi; suggested mapping bo'lsa user explicit tasdiqlaydi. Mapping version-specific va boshqa content hashda ishlamaydi.

### 10.3. Import state va atomiklik

```text
uploaded -> parsing -> preview_ready -> confirmed -> committing -> completed
                 \-> failed       \-> cancelled       \-> failed
```

- `uploaded/parsing`da permanent response yo'q.
- `preview_ready` staging encrypted va qisqa retention bilan; valid/invalid/duplicate count ko'rinadi.
- Confirmation actor, vaqt va preview hash bilan audit qilinadi.
- Confirm'dan keyin faqat previewda valid bo'lgan rowlar transactionally response/revisionga aylanadi. Bir valid rowning persist xatosi o'sha rowni rad etadi; boshqalari davom etishi mumkin, yakuniy summary aniq bo'ladi.
- Xato row hech qachon Response yaratmaydi.
- Bir xil file hash + research + template qayta yuklansa duplicate import ogohlantiriladi; explicit confirm bo'lmasa persist yo'q.

### 10.4. Validation/error modeli

```json
{
  "import_id": "<uuid>",
  "status": "preview_ready",
  "summary": {"total_rows": 10, "valid_rows": 7, "invalid_rows": 2, "duplicate_rows": 1},
  "errors": [
    {
      "row_number": 4,
      "column_name": "item.q2",
      "item_code": "q2",
      "error_code": "OPTION_NOT_ALLOWED",
      "severity": "error",
      "message_key": "import.option_not_allowed",
      "safe_params": {"allowed_option_codes": ["never", "sometimes", "often", "always"]},
      "rejected_value_preview": "***",
      "suggested_action": "Ruxsat etilgan option_code qiymatidan foydalaning"
    }
  ]
}
```

Validation qatlamlari tartibi: file → header/template → row identity/tenant/research → participant/consent → cell type/range/option → completeness → duplicate → cross-row summary. Fatal file/header xatoda row parse persist qilinmaydi.

Barqaror error code'lar: `FILE_TYPE_UNSUPPORTED`, `FILE_TOO_LARGE`, `ENCODING_INVALID`, `CSV_MALFORMED`, `TEMPLATE_MISMATCH`, `DUPLICATE_HEADER`, `UNKNOWN_COLUMN`, `UNKNOWN_ITEM`, `PII_COLUMN_FORBIDDEN`, `REQUIRED_COLUMN_MISSING`, `ROW_DUPLICATE`, `PARTICIPANT_NOT_FOUND`, `CONSENT_NOT_VALID`, `ITEM_REQUIRED`, `TYPE_INVALID`, `VALUE_OUT_OF_RANGE`, `STEP_INVALID`, `OPTION_NOT_ALLOWED`, `BOOLEAN_LITERAL_INVALID`, `REVISION_CONFLICT`.

Error report PII ruxsatiga qarab participant code'ni maskalaydi; rejected raw PII/value logga yozilmaydi.

## 11. Consent, PII, tenant, audit va retentionning modelga ta'siri

### 11.1. Consent

- `ResponseRevision` validate va `CalculationRun` gate paytida active `ConsentRecord` reference tekshiriladi.
- Run provenance consentning `consent_record_id`, immutable version/reference va status-at-run qiymatini saqlaydi; consent matnini resultga ko'chirmaydi.
- `withdrawn/declined` yoki asossiz `not_required_with_basis` yangi finalize, validation, scoring va exportni bloklaydi.
- Withdrawal oldingi resultni mutate qilmaydi; access policy bloklaydi va deletion/anonymization workflow boshlanadi.

### 11.2. PII separation

- Participant PII alohida store/contextda; Response, Revision, Result va Trace faqat `participant_id`/pseudonim reference saqlaydi.
- Formula, norm va interpretation PII fieldlarni reference qila olmaydi.
- Anonymous researchda PII record va platformadagi re-identification key yo'q.
- Audit/error/trace raw PII saqlamaydi; eksport default pseudonim.

### 11.3. Tenant isolation

- Har bir tenant-owned entity composite FK bilan bir tenant ichida bog'lanadi.
- Global methodology ID tenant querysiga qo'shilishi tenant isolationni chetlab o'tmaydi; research va response tenant-scoped.
- Idempotency/computation key tenantni o'z ichiga oladi.
- Cross-tenant participant merge yoki result share yo'q.

### 11.4. Audit

Kamida: methodology publish/status, licence revision/gate, research pin, response create/revision/validation, import preview/confirm, run start/end/block/fail, result view/export, correction, consent change, anonymize/delete audit qilinadi. Audit: actor, UTC vaqt, tenant/research/object ID, action, outcome, reason code, correlation ID; raw answer va PII yo'q. Oddiy user auditni mutate/delete qila olmaydi.

### 11.5. Retention va deletion

- Response/Revision/Result/Trace/Import staging research retention classification'iga ega.
- Legal hold deletionni bloklaydi, scoringga avtomatik ruxsat bermaydi.
- Staging/import raw file uchun asosiy research data'dan qisqaroq configurable retention qo'llanadi.
- `anonymized`: PII link qayta tiklab bo'lmaydigan tarzda uziladi; research policy ruxsat etsa pseudonim result qolishi mumkin.
- `deleted`: domain payload yo'q qilinadi; minimal non-PII tombstone/audit qonuniy siyosat bo'yicha qoladi. Deleted ID qayta ishlatilmaydi.
- Backup purge asinxron va alohida siyosat; UI darhol barcha backupdan o'chdi deb da'vo qilmaydi.

## 12. Status va state transitionlar

| Entity | Allowed transition | Guard |
| --- | --- | --- |
| MethodologyVersion | `draft→in_review` | Schema/formula/test validation |
| MethodologyVersion | `in_review→published` | Reviewer, content hash, licence metadata complete |
| MethodologyVersion | `in_review→draft` | Rejection reason |
| MethodologyVersion | `published→deprecated→withdrawn` | Platform admin reason + audit |
| Response | `draft→validation_failed→validated` yoki `draft→validated` | Consent, schema validation |
| Response | `validated→scored` | Successful current-revision result |
| Response | `validated/scored→draft` | Correction uchun yangi head revision; oldingi revision/result immutable |
| Response | `*→withdrawn/anonymized/deleted` | Governance workflow; terminal constraints |
| ResponseRevision | `draft→validation_failed→validated` | Validator output |
| ResponseRevision | `validated→superseded` | New revision created; old immutable |
| CalculationRun | `queued→running→succeeded` | Atomic result persist |
| CalculationRun | `queued/running→blocked` | Business gate failed |
| CalculationRun | `running→failed` | Deterministic engine/config yoki transient infrastructure error |
| CalculationRun | `failed→queued` | Faqat allowlisted transient infrastructure xatosi, retry limiti va audit bilan |
| Import | 10.3-bo'limdagi flow | Preview confirm va authorization |

`blocked` business holat (`LICENCE_NOT_VALID`, `CONSENT_NOT_VALID`, `RESEARCH_NOT_ACTIVE`); `failed` texnik yoki published config integrity xatosi. Failed/blocked run'dan Result yaratilmaydi.

Research lifecycle `01_product_scope.md` dagidek qoladi. Ushbu kontrakt uni qayta ta'riflamaydi, faqat scoring guard sifatida `Active`ni talab qiladi.

## 13. Sintetik end-to-end misol

> **Ogohlantirish:** `synth_balance_demo` — faqat avtomatlashtirilgan test uchun o'ylab topilgan demo. U haqiqiy psixologik konstruktni o'lchamaydi, validatsiyalanmagan va production/klinik/tadqiqot foydalanishi uchun yaroqsiz.

### 13.1. Snapshot

```json
{
  "methodology_code": "synth_balance_demo",
  "version_code": "1.0.0",
  "default_locale": "uz-Latn",
  "items": [
    {"item_code": "q1", "item_type": "integer", "required": false, "value_constraints": {"min": 0, "max": 3, "step": 1}, "score_mapping": {"mode": "identity"}, "reverse_scoring": {"mode": "none"}},
    {"item_code": "q2", "item_type": "integer", "required": false, "value_constraints": {"min": 0, "max": 3, "step": 1}, "score_mapping": {"mode": "identity"}, "reverse_scoring": {"mode": "range", "min_score": "0", "max_score": "3"}},
    {"item_code": "q3", "item_type": "integer", "required": false, "value_constraints": {"min": 0, "max": 3, "step": 1}, "score_mapping": {"mode": "identity"}, "reverse_scoring": {"mode": "none"}},
    {"item_code": "q4", "item_type": "integer", "required": false, "value_constraints": {"min": 0, "max": 3, "step": 1}, "score_mapping": {"mode": "identity"}, "reverse_scoring": {"mode": "range", "min_score": "0", "max_score": "3"}}
  ],
  "scales": [
    {
      "scale_code": "total",
      "scale_kind": "total",
      "unit_code": "demo_0_10",
      "theoretical_min": "0",
      "theoretical_max": "10",
      "display_decimals": 2,
      "aggregation": {"op": "sum_prorated", "min_answered": 3, "max_missing": 1, "target_item_count": 4},
      "transform_expr": {
        "op": "mul",
        "args": [
          {"op": "div", "left": {"op": "ref", "kind": "aggregate", "code": "total"}, "right": {"op": "const", "value": "12"}},
          {"op": "const", "value": "10"}
        ]
      }
    }
  ],
  "norm": {
    "norm_code": "synthetic_default",
    "norm_kind": "threshold_bands",
    "source_reference": "SYNTHETIC_TEST_ONLY",
    "bands": [
      {"band_code": "demo_lower", "lower_bound": "0", "lower_inclusive": true, "upper_bound": "3.333333", "upper_inclusive": false},
      {"band_code": "demo_middle", "lower_bound": "3.333333", "lower_inclusive": true, "upper_bound": "6.666667", "upper_inclusive": false},
      {"band_code": "demo_upper", "lower_bound": "6.666667", "lower_inclusive": true, "upper_bound": "10", "upper_inclusive": true}
    ]
  },
  "interpretations": [
    {"rule_code": "lower_rule", "priority": 1, "when": {"op": "eq", "left": {"op": "ref", "kind": "norm_band_code", "code": "total"}, "right": {"op": "const", "value": "demo_lower"}}, "interpretation_code": "demo_lower_text", "text_i18n": {"uz-Latn": "Faqat sintetik pastki demo diapazoni."}},
    {"rule_code": "middle_rule", "priority": 2, "when": {"op": "eq", "left": {"op": "ref", "kind": "norm_band_code", "code": "total"}, "right": {"op": "const", "value": "demo_middle"}}, "interpretation_code": "demo_middle_text", "text_i18n": {"uz-Latn": "Faqat sintetik o'rta demo diapazoni."}},
    {"rule_code": "upper_rule", "priority": 3, "when": {"op": "eq", "left": {"op": "ref", "kind": "norm_band_code", "code": "total"}, "right": {"op": "const", "value": "demo_upper"}}, "interpretation_code": "demo_upper_text", "text_i18n": {"uz-Latn": "Faqat sintetik yuqori demo diapazoni."}}
  ]
}
```

Demo itemlar required emas, ammo scale kamida 3 javobni talab qiladi. Bu production metodika dizayni uchun tavsiya emas.

### 13.2. Input va hisob

Input revision: `q1=2, q2=3, q3=1, q4=0`.

1. Mapping: `[2, 3, 1, 0]`.
2. Reverse q2: `0+3-3=0`; q4: `0+3-0=3`.
3. Transformed item scores: `[2, 0, 1, 3]`.
4. Answered 4, missing 0; valid.
5. `sum_prorated = (2+0+1+3)/4×4 = 6`.
6. Scale transform: `6/12×10 = 5`.
7. Unrounded `5` `demo_middle` bandga tushadi.
8. Display HALF_UP 2 decimal: `5.00`.
9. Interpretation: oldindan yozilgan `demo_middle_text`; “tibbiy tashxis emas” disclaimer bilan.

### 13.3. Qisqartirilgan full trace

```json
{
  "disclosure_level_applied": "full",
  "steps": [
    {"sequence": 1, "step_code": "execution_gate", "status": "completed", "outputs": [{"name": "gate", "value": "passed"}]},
    {"sequence": 2, "step_code": "option_mapping", "status": "completed", "entity_ref": {"kind": "item", "code": "q2"}, "inputs": [{"name": "answer", "value": "3"}], "outputs": [{"name": "raw_score", "value": "3"}]},
    {"sequence": 3, "step_code": "item_reverse", "status": "completed", "entity_ref": {"kind": "item", "code": "q2"}, "rule_ref": "range:0:3", "inputs": [{"name": "raw_score", "value": "3"}], "outputs": [{"name": "reversed_score", "value": "0"}]},
    {"sequence": 4, "step_code": "item_reverse", "status": "completed", "entity_ref": {"kind": "item", "code": "q4"}, "rule_ref": "range:0:3", "inputs": [{"name": "raw_score", "value": "0"}], "outputs": [{"name": "reversed_score", "value": "3"}]},
    {"sequence": 5, "step_code": "scale_aggregate", "status": "completed", "entity_ref": {"kind": "scale", "code": "total"}, "inputs": [{"name": "item_scores", "value": ["2", "0", "1", "3"]}], "outputs": [{"name": "aggregate_score_unrounded", "value": "6"}]},
    {"sequence": 6, "step_code": "scale_transform", "status": "completed", "rule_ref": "aggregate/12*10", "inputs": [{"name": "aggregate", "value": "6"}], "outputs": [{"name": "score_unrounded", "value": "5"}]},
    {"sequence": 7, "step_code": "norm_match", "status": "completed", "inputs": [{"name": "score_unrounded", "value": "5"}], "outputs": [{"name": "norm_band_code", "value": "demo_middle"}]},
    {"sequence": 8, "step_code": "interpretation_select", "status": "completed", "outputs": [{"name": "interpretation_code", "value": "demo_middle_text"}]},
    {"sequence": 9, "step_code": "round_display", "status": "completed", "inputs": [{"name": "score_unrounded", "value": "5"}], "outputs": [{"name": "score_display", "value": "5.00"}]}
  ]
}
```

## 14. Edge case va acceptance test vektorlari

Quyidagi testlar backend unit/integration suite uchun majburiy. Demo testlari `synth_balance_demo/1.0.0` snapshotiga tegishli.

| ID | Input/holat | Kutiladigan deterministik natija |
| --- | --- | --- |
| T01 | q1=2,q2=3,q3=1,q4=0 | Aggregate 6; score `5`; display `5.00`; band `demo_middle` |
| T02 | q1=0,q2=0,q3=0,q4=0 | Reverse `[0,3,0,3]`; aggregate 6; score `5.00` |
| T03 | q1=3,q2=MISSING,q3=1,q4=0 | Scores `[3,M,1,3]`; prorated `7/3×4=9.333333...`; transformed `7.777777...`; display `7.78`; band `demo_upper` |
| T04 | Faqat q1=3,q2=0 | Answered 2 < 3; `insufficient_data`; norm va interpretation null/skipped |
| T05 | q2=4 | Revision `validation_failed`, `VALUE_OUT_OF_RANGE`; scoring so'rovi bo'lsa run `blocked`, Result yo'q |
| T06 | q2=`3.0` integer CSV | `TYPE_INVALID`; coercion yo'q |
| T07 | Option/item code noma'lum | `UNKNOWN_ITEM`/`OPTION_NOT_ALLOWED`; scoring yo'q |
| T08 | Exact score `3.333333` | Birinchi band upper exclusive, `demo_middle` lower inclusive; middle |
| T09 | Exact score `6.666667` | `demo_upper` lower inclusive; upper |
| T10 | Unrounded 6.6666666, display 6.67 | Norm unrounded qiymat bilan `demo_middle`; rounded display bandni o'zgartirmaydi |
| T11 | Bir revision uchun bir xil computation key parallel 2 marta | Bitta succeeded Result; ikkinchi mavjud/ongoing runni oladi |
| T12 | Bir idempotency key boshqa answer hash bilan | `IDEMPOTENCY_KEY_REUSED`; yangi result yo'q |
| T13 | Javob tuzatildi | Revision N/result N immutable; revision N+1 va alohida result |
| T14 | Research pinned hash DB snapshot hashga mos emas | `METHODOLOGY_HASH_MISMATCH`; fatal/block; score yo'q |
| T15 | Licence run oldidan expired | `LICENCE_NOT_VALID`; oldingi result read-only, yangi result yo'q |
| T16 | Licence run davomida revoked | Persist oldidan gate revision qayta tekshiriladi; changed bo'lsa `LICENCE_CHANGED_DURING_RUN`, result commit rollback |
| T17 | Consent run oldidan withdrawn | `CONSENT_NOT_VALID`; run blocked |
| T18 | Consent run davomida withdrawn | Persist oldidan consent version qayta tekshiriladi; result commit qilinmaydi |
| T19 | Research `Paused`/`Closed` | `RESEARCH_NOT_ACTIVE`; import va scoring blok |
| T20 | Anonymous CSVda `email` column | `PII_COLUMN_FORBIDDEN`; file/header fatal, row persist yo'q |
| T21 | Bir faylda `(participant_external_code,attempt_key)` duplicate | Ikkala row `ROW_DUPLICATE`; auto-merge yo'q |
| T22 | Boshqa `_version_code` | `TEMPLATE_MISMATCH`; hech bir row persist yo'q |
| T23 | CSV empty q2 | Missing; literal `NA` esa `TYPE_INVALID` |
| T24 | Norm band overlap config | Publish validator rad etadi; runtimega chiqmaydi |
| T25 | Interpretation rule match yo'q | Score valid; result `complete_with_uninterpreted_scales`; reason `NO_INTERPRETATION_MATCH` |
| T26 | Formula division by zero | Publish rad yoki runtime `DIVISION_BY_ZERO`; partial result yo'q |
| T27 | ASTda `eval`, unknown op yoki depth 21 | Publish/import rad: `RULE_SCHEMA_INVALID`/`RULE_LIMIT_EXCEEDED` |
| T28 | Full trace, licence `summary_only` | Effective trace summary only; item raw/score qiymati yo'q |
| T29 | Userda PII export huquqi yo'q | Natija export pseudonim; PII field yo'q; audit yoziladi |
| T30 | Legal hold + retention expired | Delete blok; mavjud access boshqa policyga ko'ra; yangi scoring avtomatik ochilmaydi |
| T31 | Decimal score 2.345, display_decimals=2 | HALF_UP display `2.35`; norm 2.345 bo'yicha |
| T32 | Published locale prompt o'zgartirish | Mutate rad; yangi methodology version talab qilinadi |

## 15. Backend agentga handoff

### 15.1. Entity/constraint minimumi

Backend kamida quyidagi logical entitylarni ajratadi:

- Global: `Methodology`, `MethodologyVersion`, `Scale`, `ScaleItemLink`, `Item`, `ResponseOption`, `NormSet`, `NormBand`/`NormLookupEntry`, `InterpretationRule`, `LicenceRevision`.
- Tenant/research: `ResearchMethodologyPin`, `Response`, `ResponseRevision`, `ResponseValidationIssue`, `CalculationRun`, `Result`, `ScaleResult`, `ExplainabilityTrace`, `TraceStep`, `ImportJob`, `ImportRow`, `ImportIssue`, `ColumnMapping`.
- Governance context reference: `Participant`, `ConsentRecord`, `AuditEvent`, `RetentionPolicy`, `LegalHold`; PII alohida store.

Majburiy database-level invariantlar:

- Unique code'lar bu hujjatdagi scope bo'yicha.
- Composite tenant FK'lar; cross-tenant link imkonsiz.
- Published child row update/delete bloklanadi.
- Validated revision update/delete bloklanadi; faqat governance purge alohida privileged path.
- Result/ScaleResult/Trace immutable.
- Research Active bo'lgach pin/hash/norm update bloklanadi.
- Successful computation key unique.
- Monoton revision/licence revision va optimistic lock.
- Result va trace atomic transaction; run status only valid transition.

### 15.2. Service boundarylar

| Service/port | Mas'uliyat | Mas'ul emas |
| --- | --- | --- |
| `MethodologyRegistryService` | Draft validation, compile, publish, hash, lifecycle | Tenant response/scoring |
| `LicenceGateService` | Context + date + latest revision gate, disclosure policy | Huquqiy qarorni o'zi chiqarish |
| `ResearchPinService` | Published version/norm pin, Active freeze | Methodology mutate |
| `ResponseRevisionService` | Draft, correction, canonicalization, hash, state | Score hisoblash |
| `ResponseValidationService` | Schema/type/range/completeness/consent checks | Result yaratish |
| `ScoringOrchestrator` | Gate, idempotency, pipeline, transaction | Raw arbitrary code bajarish |
| `RuleInterpreter` | Whitelist AST typed execution, limits | DB/network/clock access |
| `NormService` | Pinned norm exact selection/match | Demografik normni taxmin qilish |
| `TraceBuilder` | Structured steps + disclosure redaction + hash | PII loglash |
| `ImportService` | Parse, map, preview, validate, confirm/commit | Consentni CSVdan yaratish |
| `ResultQueryService` | Role/licence-aware view/export snapshot | Old result mutate |
| `GovernancePolicyPort` | Consent, tenant, authorization, retention/legal hold | Scoring formula |
| `AuditPort` | Append-only safe event | Raw answer/PII nusxasi |

### 15.3. Atomicity va qayta tekshiruv

Scoring flow: computation key reserve → gate snapshot → calculate → persist oldidan research/consent/licence concurrency tokenlarini qayta tekshirish → Result+ScaleResult+Trace persist → run succeeded. Gate o'zgarsa transaction rollback. Queue retry bir xil computation key bilan xavfsiz.

Methodology JSON import qilish kerak bo'lsa u faqat platform admin publish workflow'iga kiradi: schema validate → semantic validate → formula compile → norm coverage → test vectors → review → publish. Bu oddiy tenant metodika konstruktori emas.

## 16. Ochiq savollar va product taxminlari

### 16.1. Product/yuridik qaror talab qiladigan savollar

1. Bir participant uchun takroriy attempt MVPda ochiladimi? Hozir default faqat `initial`.
2. CSV maksimal byte/row/column limitlari va XLSXning canonical ekvivalenti qancha?
3. `deprecated` versiyada oldin Active bo'lgan research yangi scoringni davom ettira oladimi yoki faqat `published`mi?
4. Licence revoke bo'lgach oldingi trace'dan qaysi disclosure darajasi qonunan ko'rsatiladi?
5. Retention minimum/maksimum, staging fayl retentioni va backup purge SLA qanday?
6. Norm profilini research admin tanlaydimi yoki platform metodika release'i bitta default normni majburlaydimi?
7. Demografik norm selection keyinchalik kerak bo'lsa, qaysi non-PII strukturali fieldlar etik/yuridik tasdiqlanadi?
8. `not_required_with_basis` uchun qaysi basis code'lar whitelist bo'ladi?
9. PII support break-glass MVPda bormi?
10. Resultning strukturali eksport formati va trace exporti P0mi?
11. Licence evidence platform ichida encrypted documentmi yoki protected external reference'mi?
12. Published methodology'ni texnik xato sabab emergency withdraw qilish approval modeli qanday?

### 16.2. Ushbu kontraktda ishlatilgan taxminlar

- Faqat kattalar, participant self-service yo'q.
- Bitta research bitta methodology version va har scale uchun bitta pinned norm set.
- Takroriy attempt default bloklangan.
- Canonical response import PII qabul qilmaydi; participant/consent alohida workflow.
- Decimal hisob fixed precision; threshold unrounded scorega, display HALF_UPga asoslanadi.
- Norm interpolation, multi-select, free text, branching va generativ interpretation MVPdan tashqarida.
- Licence `verified` bo'lmasa, hatto `restricted` bo'lsa ham yangi foydalanish bloklanadi.
- Deprecated versiya bo'yicha yangi research yaratilmaydi; oldin pin qilingan research masalasi ochiq product qaror.
- Har qanday “validity” belgisi metodika snapshotidan keladi; platforma klinik qoida ixtiro qilmaydi.

## 17. Coverage va ichki moslik checklisti

Hujjat yakuniy self-check natijasi:

- [x] Terminlar, bounded context va service ownership ajratildi.
- [x] Methodology/Version/Scale/Item/Option/Norm/Interpretation/Licence field, ID va invariantlari berildi.
- [x] MVP item/answer whitelist va explicit non-scope belgilandi.
- [x] Missing → mapping → reverse → transform → aggregate → validity → norm → interpretation → rounding tartibi deterministik qilindi.
- [x] Arbitrary code/eval taqiqlandi; typed JSON AST, whitelist va resource limitlari berildi.
- [x] Step-level trace, hash va licence disclosure darajalari berildi.
- [x] Immutable published version, research pin va reproducibility tuple berildi.
- [x] Response/revision/run/result, provenance va idempotency constraintlari berildi.
- [x] Canonical CSV, mapping, preview/confirm, row/cell error modeli berildi.
- [x] Consent, PII separation, tenant composite scope, audit va retention ta'siri modelga kiritildi.
- [x] Status transition va guardlar berildi.
- [x] Faqat sintetik, production uchun yaroqsiz demo scoring va trace berildi.
- [x] Edge case va 32 acceptance vector berildi.
- [x] Backend entity/constraint/service handoff berildi; API/UI implementatsiyasi yozilmadi.
- [x] Ochiq savollar taxminlardan ajratildi.
- [x] `01_product_scope.md` bilan mos: multi-tenant, Active pin freeze, consent/litsenziya gate, revision history, idempotent scoring, PII separation, disclaimer va non-diagnostic chegara saqlandi.

Aniqlangan ichki zidlik yo'q. Product scope'dagi hali hal qilinmagan masalalar bu hujjatda “ochiq savol” yoki konservativ MVP taxmini sifatida aniq belgilandi; ular real klinik metodika/norm sifatida to'ldirilmadi.

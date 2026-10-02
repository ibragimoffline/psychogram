# Psychogram MVP: mahsulot doirasi va domen talablari

## 0. Hujjat maqsadi

Ushbu hujjat Psychogram platformasining birinchi ishlaydigan versiyasi (MVP) uchun mahsulot chegaralarini va psixologik tadqiqot domenidagi asosiy qoidalarni belgilaydi. U keyingi bosqichdagi domen modeli va texnik loyihalash uchun kirish hujjatidir; scoring algoritmi arxitekturasi, API kontraktlari va UI dizaynini belgilamaydi.

MVP tadqiqot va professional talqin qilishni qo‘llab-quvvatlaydi, lekin tibbiy tashxis qo‘ymaydi. Natija sahifalari va eksportlarda “Bu natija tibbiy tashxis emas” degan aniq ogohlantirish bo‘lishi shart.

## 1. Muammo va qiymat taklifi

### Muammo

Psixologlar va tadqiqotchilar ko‘pincha ishtirokchi javoblarini jadval yoki qog‘ozdan qo‘lda qayta ishlaydi. Bu jarayon:

- ko‘p vaqt oladi va hisoblash xatosiga moyil;
- metodika versiyasi, normasi va qo‘llangan qoidalarni kuzatishni qiyinlashtiradi;
- natijaning qanday hosil bo‘lganini tekshirishni murakkablashtiradi;
- rozilik, maxfiylik, audit va ma’lumotni saqlash jarayonlarini bir xil yuritmaydi;
- jamoaviy tadqiqotlarda rollar va javobgarlikni noaniq qoldiradi.

### Qiymat taklifi

Psychogram tashkilotga metodikani tanlash, tadqiqotni sozlash, javoblarni qo‘lda kiritish yoki fayldan yuklash, ma’lumotni tekshirish, natijani hisoblatish va hisoblash izohini ko‘rish uchun yagona nazorat qilinadigan jarayon beradi. Platforma:

- takroriy hisoblash ishlarini qisqartiradi;
- kiritish va import xatolarini natija hisoblanishidan oldin ko‘rsatadi;
- metodika va uning aniq versiyasini natija bilan bog‘laydi;
- natijaning kelib chiqishini audit qilishga yordam beradi;
- PII va tadqiqot javoblarini imkon qadar ajratib, maxfiylik xavfini kamaytiradi.

## 2. MVP doirasi

### 2.1. MVP scope

MVP quyidagilarni qamrab oladi:

1. Bitta platformada bir nechta, o‘zaro ajratilgan tashkilotlar bilan ishlash.
2. Tashkilot a’zolarini rollar asosida boshqarish.
3. Administrator tasdiqlagan va litsenziya holati yaroqli metodikalar katalogini ko‘rish.
4. Katalogdagi metodikaning aniq versiyasi asosida tadqiqot yaratish.
5. Tadqiqot uchun minimal metadata, consent talablari, PII rejimi va retention qoidasini belgilash.
6. Ishtirokchini ichki pseudonim identifikator bilan ro‘yxatga olish.
7. Bitta ishtirokchi javoblarini qo‘lda kiritish.
8. Oldindan belgilangan CSV/XLSX shablonidan bir nechta ishtirokchi javoblarini yuklash.
9. Majburiy maydon, format, qiymat diapazoni, takroriy identifikator va yetishmayotgan javoblarni validatsiya qilish.
10. Faqat validatsiyadan o‘tgan javoblar uchun metodika natijasini hisoblash.
11. Umumiy natija, subshkala natijalari (metodikada mavjud bo‘lsa), talqin va hisoblashning bosqichma-bosqich izohini ko‘rish.
12. Natijani kamida ekranda ko‘rish va strukturali eksport qilish; eksport tarkibi rol va PII huquqiga bo‘ysunadi.
13. Muhim amallar uchun audit izi yuritish.
14. Tadqiqotni yopish, arxivlash va retention siyosatiga muvofiq o‘chirish/anonimlashtirish jarayonini boshqarish.

### 2.2. Aniq non-scope

Quyidagilar MVPga kirmaydi:

- tibbiy yoki klinik tashxis qo‘yish, davolash tavsiyasi va favqulodda ruhiy holatni avtomatik aniqlash;
- klinik qarorlarni platforma natijasiga to‘liq avtomatik topshirish;
- yangi metodika, savol yoki scoring formulasini oddiy tashkilot foydalanuvchisi tomonidan vizual konstruktor orqali yaratish;
- AI yordamida klinik talqin yoki generativ tavsiya berish;
- real vaqt video/audio diagnostikasi va biometrik ma’lumot yig‘ish;
- ishtirokchiga ochiq self-service portal, ommaviy havola orqali bevosita so‘rov to‘ldirish yoki avtomatik taklifnoma yuborish;
- mobil native ilovalar va offline sinxronizatsiya;
- billing, obuna va marketplace;
- EHR/HIS/LMS yoki tashqi laboratoriya tizimlari bilan integratsiya;
- murakkab longitudinal tahlil, guruhlararo statistik taqqoslash va ilmiy maqola uchun to‘liq analitik paket;
- tashkilotlar o‘rtasida ishtirokchi ma’lumotini ulashish;
- metodika mualliflik huquqi yoki litsenziyasini platformaning o‘zi yuridik jihatdan aniqlab berishi.

## 3. Tashkilotlar, foydalanuvchilar va huquqlar

### 3.1. Qo‘llab-quvvatlanadigan tashkilot turlari

- mustaqil psixolog yoki kichik amaliyot;
- psixologik markaz;
- tadqiqot markazi;
- institut;
- universitet yoki uning fakultet/laboratoriyasi.

Tashkilot turi mahsulotdagi asosiy workflow’ni o‘zgartirmaydi. Har bir tashkilot alohida tenant hisoblanadi; uning foydalanuvchisi boshqa tashkilot ma’lumotini ko‘ra olmaydi. Bir shaxs bir nechta tashkilotga alohida a’zolik orqali kirishi mumkin, lekin faol tashkilot konteksti aniq bo‘lishi kerak.

### 3.2. Rollar

| Rol | Asosiy huquqlar | Cheklovlar |
| --- | --- | --- |
| Platform administrator | Global metodika metadata va release gate’ni boshqaradi; tashkilotlarni texnik qo‘llab-quvvatlaydi; platforma auditiga kiradi | Tashkilotning PII va javoblarini odatiy ish jarayonida ko‘rmaydi; favqulodda kirish alohida audit qilinadi |
| Tashkilot egasi/admini | A’zolar va rollarni boshqaradi; tashkilot siyosatlari, retention va PII ruxsatlarini belgilaydi; barcha tadqiqotlarni boshqaradi | Metodikaning global litsenziya holatini o‘zi “tasdiqlangan” qila olmaydi |
| Tadqiqotchi/psixolog | Tadqiqot yaratadi; metodika tanlaydi; participant record va javoblarni boshqaradi; hisoblashni ishga tushiradi; natija va izohni ko‘radi | A’zolar/rol va global metodika metadata’ni boshqarmaydi |
| Ma’lumot kirituvchi operator | Ruxsat berilgan tadqiqotlarda ishtirokchi va javoblarni qo‘lda kiritadi/yuklaydi; validatsiya xatolarini tuzatadi | Hisoblashni tasdiqlamaydi; talqin va PII eksportini ko‘rmaydi, agar alohida ruxsat berilmasa |
| Kuzatuvchi/auditor | Ruxsat berilgan tadqiqot, natija va audit izini faqat o‘qiydi | Kiritish, tahrirlash, hisoblash, eksport yoki o‘chirish amallarini bajarmaydi |

Ishtirokchi MVPda platforma foydalanuvchisi emas. Uning ma’lumoti vakolatli xodim tomonidan, oldindan olingan va qayd etilgan rozilik asosida kiritiladi.

### 3.3. Huquq qoidalari

- Ruxsat “eng kam zarur huquq” tamoyiliga amal qiladi.
- PII’ni ko‘rish va PII bilan eksport qilish umumiy rol huquqidan alohida ruxsat hisoblanadi.
- Tadqiqotga kirish tashkilot a’zoligining o‘zi bilan avtomatik berilmaydi; tadqiqot darajasida cheklanishi mumkin.
- Foydalanuvchi roli o‘zgarganda yoki a’zolik bekor qilinganda yangi kirishlar darhol to‘xtaydi; tarixiy amallar auditda saqlanadi.
- Hech bir tashkilot roli yaroqsiz litsenziyali metodikani release gate’dan o‘tkaza olmaydi.

## 4. Research–participant lifecycle

### 4.1. Tadqiqot lifecycle

1. **Draft** — nomi, maqsadi, metodika versiyasi, PII rejimi, consent va retention qoidalari sozlanadi. Ma’lumot kiritish mumkin emas.
2. **Ready** — majburiy sozlamalar to‘liq, metodika litsenziyasi/release gate yaroqli. Faollashtirishga tayyor.
3. **Active** — ishtirokchi va javob qo‘shish, validatsiya va hisoblash mumkin.
4. **Paused** — yangi kiritish/import va hisoblash vaqtincha yopiq; mavjud ma’lumotni ruxsat doirasida ko‘rish mumkin.
5. **Closed** — ma’lumot yig‘ish tugagan; mavjud tasdiqlangan ma’lumot va natijalar read-only. Qayta ochish faqat admin vakolati va sabab bilan audit qilinadi.
6. **Archived** — kundalik ro‘yxatlardan chiqariladi, read-only va retention nazoratida qoladi.
7. **Deletion/Anonymization pending** — retention muddati yoki qonuniy so‘rov sabab o‘chirish/anonimlashtirish navbatida; legal hold bo‘lsa bajarilmaydi.

Holat o‘tishlari audit qilinadi. Metodika versiyasi tadqiqot `Active` bo‘lgach almashtirilmaydi; boshqa versiya kerak bo‘lsa yangi tadqiqot yaratiladi.

### 4.2. Ishtirokchi va javob lifecycle

1. **Participant registered** — tizim ichki ID yaratadi; tashqi kod bo‘lsa, u tashkilot/tadqiqot doirasida yagona bo‘lishi kerak.
2. **Consent recorded** — rozilik holati, versiya/reference, olingan sana-vaqt va qayd etuvchi xodim ko‘rsatiladi. Rad etilgan yoki qaytarib olingan rozilikda yangi ishlov bloklanadi.
3. **Response draft** — qo‘lda kiritilgan yoki import qilingan javob hali yakunlanmagan.
4. **Validation failed / Validated** — xatolar ro‘yxati qaytariladi yoki javob hisoblashga tayyor deb belgilanadi.
5. **Scored** — validatsiyadan o‘tgan javob uchun natija, metodika versiyasi va hisoblangan vaqt bog‘lanadi.
6. **Corrected and rescored** — manba javobi o‘zgarsa avvalgi natija ustiga yozilmaydi; yangi revision va yangi natija hosil bo‘ladi, sabab auditda qoladi.
7. **Withdrawn / anonymized / deleted** — rozilik qaytarib olinishi yoki retention jarayoni sabab keyingi ishlov to‘xtatiladi va siyosatga ko‘ra PII ajratiladi yoki ma’lumot o‘chiriladi. Oldindan anonimlashtirilgan agregat natijani olib tashlash talabi yurisdiksiya siyosatiga bog‘liq.

## 5. Asosiy user flowlar

### 5.1. Metodika tanlash

1. Tadqiqotchi katalogni nomi, til, maqsadli guruh va status bo‘yicha ko‘radi/qidiradi.
2. Metodika kartasida versiya, til, mo‘ljallangan populyatsiya, taxminiy to‘ldirish vaqti, litsenziya statusi, foydalanish cheklovi va ogohlantirishlar ko‘rinadi.
3. Faqat `verified` va amal qilish muddati tugamagan versiyani tanlash mumkin.
4. Noma’lum, muddati tugagan, bekor qilingan yoki foydalanish doirasiga mos bo‘lmagan litsenziya tanlovni bloklaydi va sababini ko‘rsatadi.

### 5.2. Tadqiqot yaratish

1. Tadqiqotchi nom, qisqa maqsad, mas’ul shaxs, metodika versiyasi va taxminiy muddatni kiritadi.
2. PII rejimini (`anonymous` yoki `pseudonymous/identified`), majburiy demografik maydonlarni, consent reference/version va retention qoidasini tanlaydi.
3. Tizim majburiy metadata hamda metodika release gate’ni tekshiradi.
4. Talablar bajarilganda tadqiqot `Ready`, so‘ng vakolatli foydalanuvchi tasdig‘i bilan `Active` bo‘ladi.

### 5.3. Javobni qo‘lda kiritish

1. Operator mavjud participant ID’ni tanlaydi yoki yangisini yaratadi.
2. Consent holati tekshiriladi; yaroqsiz holatda kiritish davom etmaydi.
3. Operator metodika maydonlariga javoblarni kiritadi va draft saqlashi mumkin.
4. Yakunlashda validatsiya ishlaydi; xatolar maydon kesimida tushunarli ko‘rsatiladi.
5. Xatosiz javob `Validated` holatiga o‘tadi.

### 5.4. Javoblarni yuklash

1. Operator aynan tanlangan metodika versiyasiga tegishli shablonni oladi.
2. CSV/XLSX faylni yuklaydi; fayl turi/hajmi, ustunlar va encoding tekshiriladi.
3. Tizim preview va qatorlar kesimidagi xatolarni ko‘rsatadi; PII ustunlari ruxsatga muvofiq qabul qilinadi.
4. Import “hammasi yoki hech narsa” emas: xatoli qatorlar rad etilib, yaroqli qatorlar faqat foydalanuvchining yakuniy tasdig‘idan keyin saqlanishi mumkin.
5. Import xulosasida jami, qabul qilingan, rad etilgan va duplikat qatorlar soni hamda tuzatish uchun xato fayli beriladi.

### 5.5. Validatsiya va hisoblash

1. Tizim participant/consent holati, majburiy javoblar, ruxsat etilgan qiymatlar, metodika versiyasi va duplikatni tekshiradi.
2. Xato mavjud bo‘lsa hisoblash bloklanadi va amaliy tuzatish xabari beriladi.
3. Vakolatli tadqiqotchi validatsiyadan o‘tgan bitta yoki bir nechta javob uchun hisoblashni boshlaydi.
4. Natija metodika versiyasi, response revision, vaqt va tashabbuskor bilan bog‘lanadi.
5. Bir xil o‘zgarmagan response revision uchun takroriy so‘rov yangi turlicha natija yaratmasligi kerak; foydalanuvchi mavjud natijaga yo‘naltiriladi.

### 5.6. Natija va izohni ko‘rish

1. Tadqiqotchi ishtirokchini tanlab, umumiy natija va mavjud subshkalalarni ko‘radi.
2. Har bir natijada birlik/diapazon, metodika versiyasi, hisoblangan vaqt va talqin chegaralari ko‘rsatiladi.
3. “Qanday hisoblandi?” bo‘limida ishlatilgan javoblar/revision, qoida bosqichlari va oraliq qiymatlar inson tushunadigan ko‘rinishda beriladi; maxfiy metodika kontenti litsenziya ruxsatidan oshib ketmaydi.
4. Yetarli ma’lumot bo‘lmasa talqin berilmaydi va sabab ko‘rsatiladi.
5. Tibbiy tashxis emasligi haqidagi ogohlantirish doim ko‘rinadi.
6. Natija yoki PII eksporti foydalanuvchi huquqi, tadqiqot holati va audit talabiga ko‘ra bajariladi.

## 6. Consent, PII, maxfiylik, audit va retention talablari

### 6.1. Consent

- Platformaga javob kiritishdan oldin rozilik olinganligi qayd qilinishi shart.
- Minimal consent record: status (`granted`, `withdrawn`, `declined`, `not_required_with_basis`), hujjat/reference va versiyasi, olingan sana-vaqt, qayd etuvchi hamda asos/izoh.
- `not_required_with_basis` faqat tashkilot admini tasdiqlagan huquqiy/etik asos bilan ishlatiladi.
- Rozilikning matni yoki tashqi hujjatga havola saqlanishi kerak; aynan qaysi versiyaga rozilik berilgani o‘zgarmas bo‘ladi.
- Rozilik qaytarib olinsa yangi kiritish, hisoblash va eksport bloklanadi; keyingi o‘chirish/anonimlashtirish tashkilot siyosati va qonuniy majburiyatga ko‘ra audit bilan bajariladi.
- Voyaga yetmaganlar va vakil orqali rozilik MVPda qo‘llab-quvvatlanmaydi; bunday tadqiqotni faollashtirish bloklanadi.

### 6.2. PII va anonimlik

- Yangi tadqiqot uchun default rejim `pseudonymous`; bevosita identifikator faqat asoslangan ehtiyoj va alohida huquq bilan qo‘shiladi.
- `anonymous` tadqiqotda ism, telefon, email, manzil, davlat identifikatori kabi bevosita PII yig‘ilmaydi; qayta identifikatsiya kaliti platformada saqlanmaydi.
- Pseudonim participant ID javoblar bilan ishlashdagi asosiy identifikator bo‘ladi.
- PII mantiqan javob va natijalardan ajratiladi; PII’ga kirish alohida ruxsat va auditga ega.
- Erkin matn MVPda default o‘chiq, chunki u kutilmagan PII olib kirishi mumkin.
- Eksportlar default holatda pseudonimlashtiriladi; PII bilan eksport alohida ruxsat, sabab va audit talab qiladi.
- Import preview va xato loglari zarur bo‘lmagan PII’ni ochib bermasligi kerak.

### 6.3. Maxfiylik va xavfsizlikka oid product talablari

- Tenantlararo ma’lumot izolyatsiyasi majburiy va buzilmas invariantdir.
- Ma’lumot uzatishda va saqlashda shifrlanishi kerak.
- Sessiya, parol va autentifikatsiya tafsiloti texnik bosqichda aniqlanadi, ammo admin va PII vakolatli rollar uchun kuchli autentifikatsiya talab qilinadi.
- Maxfiy ma’lumot ilova loglari, monitoring xabarlari yoki oddiy xato matnlariga tushmasligi kerak.
- Backup ma’lumotlari ham bir xil maxfiylik va retention talablariga bo‘ysunadi.
- Support xodimining tashkilot ma’lumotiga favqulodda kirishi vaqt bilan cheklangan, sababli va to‘liq audit qilinadigan bo‘lishi kerak.
- Tashkilot tadqiqot ma’lumotini kim ko‘rganini va kim eksport qilganini tekshira olishi kerak.

### 6.4. Audit

Quyidagi hodisalar kamida audit qilinadi:

- login va muvaffaqiyatsiz loginlar (zarur xavfsiz metadata bilan);
- a’zolik, rol va PII ruxsatining berilishi/bekor qilinishi;
- tadqiqot yaratish, holat va siyosat o‘zgarishi;
- participant yaratish, birlashtirishga urinish, anonimlashtirish va o‘chirish;
- consent yaratish va status o‘zgarishi;
- qo‘lda kiritish/import, validatsiya natijasi va tuzatish;
- hisoblashni boshlash va natija versiyasi;
- PII ko‘rish, natija/PII eksporti;
- metodika litsenziya metadata va release gate o‘zgarishi;
- retention, legal hold va deletion amallari.

Har bir audit yozuvi kim, qachon, qaysi tashkilot/tadqiqot/obyekt, nima qilgani, natija va sababni (talab qilingan amallarda) saqlaydi. Audit yozuvini odatiy foydalanuvchi tahrirlay yoki o‘chira olmaydi; auditning o‘zi PII’ni ortiqcha nusxalamasligi kerak.

### 6.5. Data retention

- Har bir tadqiqot faollashishidan oldin retention muddati yoki tashkilotning tasdiqlangan siyosatiga reference olishi shart.
- Aniq default muddat yurisdiksiya va tashkilot siyosati tasdiqlanmaguncha belgilanmaydi; MVP konfiguratsiya orqali muddatni majburiy tanlatadi.
- Retention muddati tugashidan oldin vakolatli admin ogohlantiriladi.
- Muddati tugagan ma’lumot o‘chirish yoki qayta tiklab bo‘lmaydigan anonimlashtirish navbatiga o‘tadi.
- `legal hold` retention o‘chirishini vaqtincha to‘xtatadi; uni faqat admin sabab bilan qo‘yadi/oladi va bu audit qilinadi.
- Backupdan yo‘qolish vaqti alohida hujjatlashtiriladi; UI’dagi o‘chirish “darhol barcha backupdan yo‘qoldi” deb noto‘g‘ri da’vo qilmaydi.

### 6.6. Metodika litsenziyasi va copyright release gate

Har bir metodika **va har bir versiya** quyidagi majburiy metadata’ga ega bo‘ladi:

- nomi, versiyasi, tili va manba/reference;
- muallif yoki huquq egasi;
- copyright holati;
- litsenziya statusi: `verified`, `restricted`, `expired`, `revoked` yoki `unknown`;
- ruxsat berilgan foydalanish turi (research/education/clinical va boshqalar), tashkilot turi va hudud;
- ruxsat etilgan kontent ko‘rsatish/eksport chegaralari;
- litsenziya dalili yoki uning himoyalangan reference’i;
- amal boshlanish/tugash sanasi, tekshirgan shaxs va tekshirish sanasi;
- zarur disclaimer va foydalanish cheklovlari.

Release gate qoidasi: status `verified` bo‘lmasa, muddati tugagan bo‘lsa yoki tadqiqot konteksti ruxsat doirasiga mos kelmasa, metodika yangi tadqiqot uchun tanlanmaydi, tadqiqot faollashtirilmaydi va yangi hisoblash bajarilmaydi. Avvalgi natijalar audit/retention sabab read-only ko‘rinishi mumkin, lekin yangi foydalanish bloklanadi. Faqat platform administrator huquqiy tasdiq asosida statusni o‘zgartiradi; barcha o‘zgarishlar audit qilinadi.

## 7. Ustuvor user storylar va acceptance criteria

### US-01 — Tashkilot izolatsiyasi (P0)

**Story:** Tashkilot admini sifatida faqat o‘z tashkilotim ma’lumotlari ko‘rinishini istayman.

**Acceptance criteria:**

- Given A va B tashkilotida tadqiqotlar bor, when A a’zosi ro‘yxat/qidiruv/eksportdan foydalansa, then B ma’lumoti natijaga kirmaydi.
- Given foydalanuvchida A a’zoligi bekor qilingan, when u yangi so‘rov qilsa, then kirish darhol rad etiladi.
- Tenantlararo ruxsatsiz kirish urinishi xavfsiz metadata bilan audit qilinadi.

### US-02 — Metodika tanlash va litsenziya gate’i (P0)

**Story:** Tadqiqotchi sifatida faqat qonuniy foydalanishga yaroqli metodika versiyasini tanlamoqchiman.

**Acceptance criteria:**

- `verified`, muddati yaroqli va kontekstga mos versiya tanlanadi.
- `unknown`, `expired`, `revoked` yoki kontekstga mos bo‘lmagan versiyada tanlash/faollashtirish/hisoblash bloklanadi va aniq sabab ko‘rsatiladi.
- Majburiy litsenziya metadata’sidan bittasi yo‘q bo‘lsa release gate muvaffaqiyatsiz tugaydi.
- Status o‘zgarishi kim/qachon/sabab bilan auditda qoladi.

### US-03 — Tadqiqotni faollashtirish (P0)

**Story:** Tadqiqotchi sifatida barcha etik va product sozlamalari to‘liq bo‘lgandagina tadqiqotni boshlamoqchiman.

**Acceptance criteria:**

- Nomi, mas’ul, metodika versiyasi, PII rejimi, consent reference/asosi va retention qoidasi bo‘lmasa `Active` holatiga o‘tmaydi.
- Metodika versiyasi `Active` holatidan keyin tahrirlanmaydi.
- Har bir holat o‘zgarishi tashabbuskor va vaqt bilan audit qilinadi.

### US-04 — Consent nazorati (P0)

**Story:** Operator sifatida rozilik holati yaroqli bo‘lmagan ishtirokchi javobiga ishlov berib yubormaslikni istayman.

**Acceptance criteria:**

- `granted` yoki tasdiqlangan `not_required_with_basis` bo‘lmasa response yakunlash va hisoblash bloklanadi.
- Consent record versiya/reference, sana-vaqt va qayd etuvchisiz yaroqli hisoblanmaydi.
- `withdrawn` qilingach yangi kiritish, hisoblash va eksport darhol bloklanadi.

### US-05 — Qo‘lda javob kiritish (P0)

**Story:** Operator sifatida bitta ishtirokchi javobini xatosiz kiritmoqchiman.

**Acceptance criteria:**

- Draft to‘liq bo‘lmagan holatda saqlanishi mumkin, lekin hisoblanmaydi.
- Majburiy javob, format yoki diapazon xatosi maydon kesimida ko‘rsatiladi.
- Xatolar tuzatilgach response `Validated` bo‘ladi va kim/qachon kiritgani saqlanadi.

### US-06 — Ommaviy import (P0)

**Story:** Operator sifatida ko‘p javobni shablon orqali yuklab, xatolarni qator kesimida tuzatmoqchiman.

**Acceptance criteria:**

- Noto‘g‘ri fayl turi, versiyaga mos kelmaydigan ustun yoki ortiqcha PII ustuni importni bloklaydi.
- Preview jami/yaroqli/xatoli/duplikat qatorlar sonini ko‘rsatadi.
- Foydalanuvchi tasdiqlamaguncha yaroqli qatorlar ham doimiy saqlanmaydi.
- Xato hisobotida qator, maydon, xato kodi va tuzatish tavsifi bor; ruxsatsiz foydalanuvchiga PII ochilmaydi.

### US-07 — Ishonchli hisoblash va revision (P0)

**Story:** Tadqiqotchi sifatida natija aynan qaysi javob revisionidan olinganini bilmoqchiman.

**Acceptance criteria:**

- Faqat `Validated` response va yaroqli consent/litsenziya holatida hisoblash boshlanadi.
- Natijada metodika versiyasi, response revision, hisoblangan vaqt va tashabbuskor mavjud.
- Javob tahrirlanganda eski natija o‘zgarmaydi; yangi revision qayta hisoblashni talab qiladi.
- O‘zgarmagan revisionni takror hisoblash mavjud natijani qaytaradi yoki unga yo‘naltiradi.

### US-08 — Tushunarli natija (P0)

**Story:** Psixolog sifatida natijani va u qanday hosil bo‘lganini tekshirmoqchiman.

**Acceptance criteria:**

- Natija umumiy ball va metodikada mavjud subshkalalarni birlik/diapazon bilan ko‘rsatadi.
- Izoh foydalanilgan response revision, hisoblash bosqichlari va oraliq qiymatlarni ko‘rsatadi, lekin litsenziya cheklovini buzmaydi.
- Yetarli ma’lumot bo‘lmasa talqin o‘rniga aniq sabab chiqadi.
- Har bir natija va eksportda “tibbiy tashxis emas” ogohlantirishi bor.

### US-09 — PII nazoratli eksport (P0)

**Story:** Tashkilot admini sifatida eksportda maxfiy ma’lumot nazoratsiz tarqalmasligini istayman.

**Acceptance criteria:**

- Oddiy eksport pseudonim ID bilan, bevosita PII’siz yaratiladi.
- PII eksporti faqat alohida huquqli foydalanuvchidan sabab kiritishni talab qiladi.
- Eksport kim, qachon, qaysi tadqiqot va PII mavjud/yo‘qligi bilan audit qilinadi.

### US-10 — Yopish va retention (P1)

**Story:** Tashkilot admini sifatida tadqiqot tugagach ma’lumotni belgilangan muddatdan ortiq saqlamaslikni istayman.

**Acceptance criteria:**

- `Closed` tadqiqotda yangi javob/import bloklanadi; qayta ochish admin sababi va auditni talab qiladi.
- Retention muddati yaqinlashganda admin ogohlantiriladi.
- Muddati tugaganda ma’lumot deletion/anonymization pending holatiga o‘tadi.
- Faol legal hold bo‘lsa avtomatik o‘chirish bajarilmaydi va sabab ko‘rsatiladi.

## 8. Edge-case va xatolik holatlari

| Holat | Kutiladigan product xulqi |
| --- | --- |
| Bir participant tashqi kodi bir faylda yoki tadqiqotda takrorlangan | Duplikat bloklanadi yoki foydalanuvchidan aniq merge/skip qarori so‘raladi; avtomatik birlashtirilmaydi |
| Import shabloni boshqa metodika/versiyaga tegishli | Import bloklanadi, kutilgan va topilgan versiya ko‘rsatiladi |
| Fayl juda katta, buzilgan yoki encoding noma’lum | Hech qanday qator saqlanmaydi; xavfsiz va amaliy xabar beriladi |
| Importning ayrim qatorlari xato | Preview’da ajratiladi; faqat tasdiqlangan yaroqli qatorlar saqlanadi |
| Majburiy javob yo‘q yoki qiymat diapazondan tashqarida | `Validated` bo‘lmaydi; metodika qoidasiga mos xato chiqadi |
| Bir ishtirokchi uchun bir nechta to‘ldirish | Tadqiqot sozlamasi ruxsat bermasa duplikat bloklanadi; ruxsat bersa har biri alohida vaqt/revision bilan saqlanadi |
| Hisoblash paytida litsenziya muddati tugadi/bekor qilindi | Yangi hisoblash bloklanadi; oldingi natija read-only va ogohlantirish bilan qoladi |
| Consent hisoblashdan keyin qaytarib olindi | Yangi ishlov/eksport bloklanadi; deletion/anonymization workflow boshlanadi, eski audit saqlanadi |
| Javob natijadan keyin tuzatildi | Eski response/result o‘zgarmaydi; yangi revision va qayta hisoblash talab qilinadi |
| Ikki operator bir draftni bir vaqtda tahrirladi | Jim overwrite qilinmaydi; konflikt ko‘rsatiladi va qayta yuklash/solishtirish talab qilinadi |
| Hisoblash so‘rovi takror yuborildi | O‘zgarmagan revision uchun duplikat natija yaratilmaydi |
| Natija diapazondan tashqari yoki qoida bajarilmadi | Natija “hisoblab bo‘lmadi” holatida, ichki diagnostika reference’i bilan qaytadi; uydirma talqin berilmaydi |
| Foydalanuvchi hisoblash vaqtida huquqini yo‘qotdi | Natijaga keyingi kirish rad etiladi; yakunlangan amal audit qilinadi |
| Tadqiqot `Closed`/`Paused` paytida import | Bloklanadi; holat va zarur keyingi amal ko‘rsatiladi |
| Anonymous tadqiqotga PII ustuni yuklandi | Import bloklanadi va PII’ni olib tashlash talabi beriladi |
| Participant ID yo‘qolgan yoki noto‘g‘ri moslangan | PII orqali taxminiy auto-match qilinmaydi; operator tekshiruvi talab qilinadi |
| Retention muddati tugadi, lekin legal hold mavjud | O‘chirish to‘xtaydi; hold sababi va egasi ko‘rinadi |
| Metodika kontentini ko‘rsatish litsenziyada cheklangan | Natija izohi faqat ruxsat etilgan abstraksiya darajasida beriladi |

## 9. 3-subagent uchun topshiruv

### 9.1. Qabul qilingan product qarorlari

Quyidagilar keyingi domen/ma’lumot modelida invariant sifatida aks etishi kerak:

1. Platforma multi-tenant; barcha biznes obyektlari tashkilot kontekstiga tegishli va tenantlararo kirish taqiqlangan.
2. Metodika versiyalanadi; `Active` tadqiqot aniq bitta metodika versiyasiga mahkamlanadi.
3. Metodika litsenziya/copyright metadata’si majburiy va release gate hisoblanadi.
4. Tadqiqot holatlari: `Draft → Ready → Active ↔ Paused → Closed → Archived → Deletion/Anonymization pending`; qayta ochish vakolat va audit talab qiladi.
5. Ishtirokchi platforma user’i emas; asosiy identifikator pseudonim participant ID.
6. Consent alohida kuzatiladigan record; uning statusi response yakunlash, hisoblash va eksportga ta’sir qiladi.
7. Response draft va revisionlarga ega; tuzatish tarixni ustiga yozmaydi.
8. Natija aniq response revision va metodika versiyasiga bog‘lanadi; takroriy hisoblash idempotent bo‘lishi kerak.
9. PII javob/natijadan mantiqan ajratiladi va alohida ruxsat bilan boshqariladi.
10. Audit odatiy foydalanuvchi tomonidan o‘zgartirib bo‘lmaydigan hodisalar izi sifatida saqlanadi.
11. Har bir tadqiqotda consent, PII rejimi va retention qoidasi faollashtirishdan oldin mavjud bo‘ladi.
12. MVP tibbiy tashxis bermaydi; natija va eksportlarda disclaimer majburiy.
13. Voyaga yetmaganlar, participant self-service va metodika konstruktori MVPdan tashqarida.

### 9.2. Keyingi bosqich javob berishi kerak bo‘lgan ochiq savollar

Bu savollar bo‘yicha hozir product taxmini ishlatiladi; yakuniy yuridik/product qarori keyin olinadi:

1. Dastlabki bozor/yurisdiksiya qaysi va qaysi privacy qonunlari ustuvor?
2. Retention uchun ruxsat etilgan minimum/maksimum va tashkilot default muddati qancha?
3. `anonymous` ma’lumotni amalda qayta identifikatsiya qilib bo‘lmasligi uchun qaysi demografik kombinatsiyalar cheklanadi?
4. Bir tadqiqotda bitta ishtirokchining takroriy o‘lchovlari MVPda kerakmi yoki faqat bitta response’mi?
5. Importning maksimal fayl hajmi/qator soni va qo‘llab-quvvatlanadigan CSV encoding’lari qanday?
6. Natija eksportining MVP formatlari: CSV, XLSX va/yoki PDF’dan qaysilari majburiy?
7. Tashkilot admini metodika litsenziya dalilini yuklay oladimi yoki bu faqat platforma operatori orqali bajariladimi?
8. Litsenziya bekor qilinganda oldingi natijalarni ko‘rsatishning huquqiy chegarasi qanday?
9. PII support access (break-glass) MVPda kerakmi yoki butunlay bloklanadimi?
10. Tashkilot ichida tadqiqotga alohida a’zolar biriktirish P0’mi yoki barcha tadqiqotchilar barcha tadqiqotni ko‘radimi?
11. Rozilik matnining platformada to‘liq nusxasi saqlanadimi yoki himoyalangan tashqi reference yetarlimi?
12. Data subject access/deletion so‘rovlari uchun tashkilotning tekshirish va tasdiqlash SLA’i qanday?

### 9.3. MVP uchun ishchi taxminlar

- Birinchi release kattalar ishtirokidagi, tashkilot oldindan rozilik oladigan tadqiqotlarga mo‘ljallangan.
- Ishtirokchi javobni platformada o‘zi to‘ldirmaydi; vakolatli xodim qo‘lda kiritadi yoki fayldan yuklaydi.
- Dastlabki metodikalar platforma operatori tomonidan oldindan tayyorlangan va huquqiy holati tekshirilgan bo‘ladi.
- Pseudonimlashtirish default, bevosita PII esa ixtiyoriy va cheklangan.
- Erkin matnli javoblar default o‘chiq.
- Bitta tadqiqot bitta metodika versiyasidan foydalanadi; bir nechta metodika kerak bo‘lsa alohida tadqiqotlar yaratiladi.
- Guruh statistikasi va klinik tavsiya MVPdan tashqarida; MVP individual response natijasi va uning izohiga qaratiladi.
- Product darajasidagi holatlar va invariantlar keyingi bosqichda texnik modelga aylantiriladi, ammo bu hujjat API, database schema yoki scoring formulalarini belgilamaydi.

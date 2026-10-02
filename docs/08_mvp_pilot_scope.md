# Psychogram: kichik va to‘liq ishlaydigan MVP

Sana: 2026-10-02. Asos: foydalanuvchi taqdim etgan `ARCHITECTURE(4).md`.

## 1. Tahlil chegarasi va asosiy qaror

Hozir faqat arxitektura hujjati taqdim etilgan. Undagi kod, testlar soni va imkoniyatlar hujjat tavsifi sifatida qabul qilindi; dastur ishga tushirilmadi va implementatsiya tekshirilmadi. Quyidagi matn — mavjud loyihani qisqartirish uchun taklif etilgan texnik topshiriq. Kodga o‘zgarish kiritilgani yoki tizim tayyorligi haqidagi hisobot emas.

MVP mahsuloti: **psixolog yoki tadqiqotchi tayyor metodika bo‘yicha yig‘ilgan javoblarni kiritadi, tekshirilgan ballarni oladi va tadqiqot natijalarini CSV jadvalga chiqaradi.**

Boshlang‘ich chegaralar:

- Bitta pilot tashkilot; backenddagi tashkilotlararo izolyatsiya saqlanadi.
- Platforma administratori va tadqiqotchi — ikkita faol foydalanish turi. Mavjud owner/admin rollari texnik sozlash uchun saqlanadi, yangi rollar yaratilmaydi.
- Dastlab bitta to‘liq tekshirilgan metodika. Ikkinchi va uchinchi metodika birinchi oqim qabul sinovidan o‘tgach qo‘shiladi.
- Bitta tadqiqotda bitta metodika versiyasi.
- Faqat tadqiqot maqsadi; klinik foydalanish interfeysga kiritilmaydi.
- Respondentning ismi, telefoni, manzili kiritilmaydi; P001 kabi tadqiqot ichidagi kod ishlatiladi. Kodning shaxsga mos ro‘yxati tashqarida mavjud bo‘lsa, bu psevdonimlashtirilgan ma’lumot hisoblanadi.
- Interfeys o‘zbek lotin yozuvida. Mavjud tarjima tuzilmasi saqlanadi.
- Birinchi relizda mutaxassis javoblarni qo‘lda kiritadi. Respondent uchun ochiq havola va CSV import keyingi alohida bosqichlar.

Bu tanlov mavjud hujjatdagi oqimga eng yaqin. Agar mahsulotning asosiy maqsadi respondentning masofadan mustaqil test to‘ldirishi bo‘lsa, ushbu qaror o‘zgaradi: respondent oqimi birinchi relizga olinadi, import esa baribir keyinga qoladi.

## 2. Mavjud arxitektura bo‘yicha xulosalar

| Kuzatuv | Mahsulotga ta’siri | Qaror |
|---|---|---|
| Snapshot, versiya, javob revisioni va deterministik hisoblash tasvirlangan | Ballni qayta tekshirish uchun foydali asos | Saqlash; qayta yozmaslik |
| Litsenziya, rozilik va tenant tekshiruvlari mavjud deb ko‘rsatilgan | Natijadan foydalanish va ma’lumot ajratilishi nazorat qilinadi | Tekshiruvlarni saqlash, sozlashni administrator zimmasiga olish |
| Ko‘p rol, registr, retention, audit, PII va alohida validate/calculate ekranlari bor | Tadqiqotchi asosiy ishni bajarishdan oldin ko‘p texnik bosqichdan o‘tadi | Menyu va foydalanuvchi amallarini kamaytirish |
| CSV import avvaldan yaratilgan participant va rozilikni talab qiladi | Birinchi marta ommaviy yuklash mustaqil ishlamaydi | Birinchi relizdan chiqarish; keyin alohida yakunlangan oqim sifatida kiritish |
| Import confirm faqat javoblarni yaratish/tekshirish bilan tavsiflangan | Importdan keyin hisoblash hali alohida qoladi | Import qo‘shilganda hisoblash va qayta urinishni ham loyihalash |
| Eksport alohida natija uchun ko‘rsatilgan | Tadqiqotchi butun guruhni bir jadvalda ololmasligi mumkin | Tadqiqot bo‘yicha umumiy CSV eksport qo‘shish |
| Frontend auditorga export beradi, backend rad etadi | Tugma ko‘rinadi, ammo 403 qaytadi | Frontend capability’ni backendga moslash |
| Research uchun yopish holati ko‘rsatilmagan | Yig‘ish tugagach yangi yozuvni to‘xtatish amali yo‘q | `closed` holatini qo‘shish |
| Idempotency bo‘yicha mavjud natijani qaytarish gate’lardan oldin tasvirlangan | Rozilik/litsenziya o‘zgargach eski natijaga kirish siyosati chetlab o‘tilishi ehtimoli bor | Kodda tekshirish; cache javobidan oldin ham joriy ruxsat siyosatini qo‘llash |
| Har metodikada bitta `total` shkala majburiy | Umumiy balli bo‘lmagan metodikaga mos kelmasligi mumkin | Birinchi metodika kontraktga haqiqatan mos bo‘lsin; sun’iy umumiy ball yaratilmasin |

Oxirgi ikki band — koddan tasdiqlanishi kerak bo‘lgan tekshiruv nuqtalari. Ular aniqlangan ekspluatatsiya yoki barcha metodikalarga tegishli xato sifatida talqin qilinmaydi.

## 3. Birinchi relizdagi olti funksiya

| № | Funksiya | Foydalanuvchi amali | Tayyor deb hisoblash sharti |
|---|---|---|---|
| 1 | Tizimga kirish | Administrator tayyorlagan hisob bilan kiradi | Faqat o‘z tashkiloti ma’lumotini ko‘radi; chiqish ishlaydi |
| 2 | Tadqiqot yaratish | Nom, maqsad va tayyor metodikani tanlaydi | Versiya biriktiriladi; yaroqsiz metodika bilan ish boshlanmaydi |
| 3 | Respondent va javob kiritish | Kod va amaldagi rozilik qaydi bilan javoblarni kiritadi | Kod takrorlanmaydi; formani qoralama sifatida saqlash mumkin |
| 4 | Tekshirish va hisoblash | «Natijani hisoblash»ni bosadi | Xato savol yonida ko‘rinadi yoki natija ochiladi; takror bosish nusxa yaratmaydi |
| 5 | Natijani ko‘rish va tuzatish | Shkala ballarini ko‘radi; kerak bo‘lsa sabab bilan javobni tuzatadi | Oldingi natija saqlanadi, joriy natija aniq belgilanadi |
| 6 | Umumiy CSV eksport va yakunlash | Tadqiqot jadvalini yuklaydi; yig‘ishni yopadi | Joriy natijalar bitta faylda; yopilgach yangi javob va tahrir bloklanadi |

Rozilik belgisi avtomatik «berilgan» bo‘lib turmaydi. Mutaxassis hujjatlashtirilgan rozilik asosini qayd qiladi. Huquqiy istisno uchun mavjud `not_required_with_basis` holati oddiy formaga avtomatik qo‘llanmaydi.

## 4. Foydalanuvchi oqimi va ekranlar

Asosiy menyu: **Tadqiqotlar** va **Metodikalar**. Natijalar har bir tadqiqot ichida. Alohida statistik dashboard qurilmaydi.

1. **Kirish.** Login/parol, tushunarli xato, sessiya tugaganda qayta kirish. Pilotda ochiq ro‘yxatdan o‘tish yopiladi; hisobni administrator yaratadi.
2. **Tadqiqotlar.** Nom, metodika, holat, respondentlar soni va hisoblangan natijalar soni. «Yangi tadqiqot» tugmasi.
3. **Tadqiqot yaratish.** Nom, maqsad, metodika, rozilik matni/asosi va saqlash muddati bo‘yicha tashkilot tasdiqlagan standart. Texnik hash, norm ID va litsenziya JSON’i ko‘rsatilmaydi. «Yaratish va boshlash» mavjud create/activate xizmatlarini ketma-ket bajaradi; yaratilgan `ready` tadqiqot aktivlashmasa, shu obyekt bilan davom etadi.
4. **Tadqiqot ish oynasi.** Respondent kodi, javob holati, natija holati, sana. «Javob kiritish», «CSV yuklash», «Tadqiqotni yakunlash». CSV yuklash bu yerda eksportni anglatadi; import tugmasi birinchi relizda bo‘lmaydi.
5. **Javob formasi.** Kod, rozilik qaydi, metodika yo‘riqnomasi va savollar. «Qoralamani saqlash» va «Natijani hisoblash». Server tasdiqlamaguncha «Saqlandi» yozilmaydi. Qayta ochishda serverdagi qoralama tiklanadi.
6. **Natija.** Respondent kodi, metodika va versiya, shkala nomi, ball, mavjud bo‘lsa asoslangan talqin, hisoblash vaqti. «Bu natija tibbiy tashxis emas» izohi. Tafsilotda revision va hisoblash izchilligi; odatiy ekranda uzun trace yo‘q.

Metodikalar katalogi faqat ko‘rish uchun: nom, maqsad, qo‘llanish doirasi, savollar soni, versiya. Yangi metodika yaratish konstruktori tadqiqotchi interfeysiga kirmaydi.

Javob va natija holati alohida ko‘rsatiladi. Javob tahrirlanganidan keyin yangi revision hisoblanmaguncha «Qayta hisoblash kerak» yoziladi; oldingi natija joriydek ko‘rsatilmaydi.

## 5. Hisoblash va metodika talablari

- Birinchi metodika uchun savollar, javob kodlari, to‘g‘ri/teskari kalitlar, shkala tarkibi, ball diapazoni va hisoblash misollari tekshiriladi.
- Foydalanish asosi va matnni ko‘rsatish ruxsati tasdiqlanadi. Bu tekshiruv administrator tayyorlaydigan metodika paketiga kiradi.
- Texnik test uchun sun’iy fixture mumkin, ammo u haqiqiy psixologik metodika sifatida katalogda e’lon qilinmaydi.
- Lokal normativ tasdiqlanmagan bo‘lsa, tizim «past/o‘rta/yuqori» chegaralarini o‘zi yasamaydi. Xom ball va «Ushbu guruh uchun normativ talqin mavjud emas» holati ko‘rsatiladi.
- Yo‘q javoblarni nolga aylantirish, o‘rtacha bilan to‘ldirish yoki proratsiya qilish faqat metodika qoidasi ruxsat etsa ishlaydi.
- Dastlab single-choice va mavjud agregatsiya qoidalariga mos metodika tanlanadi. Yangi universal formula konstruktori yaratilmaydi.
- Mavjud Decimal hisoblash, versiya/hash, validatsiya, reverse scoring, immutable revision va natija tarixi saqlanadi.
- Bir respondent uchun bir tadqiqotda bitta faol javob urinishidan foydalaniladi. Tuzatish yangi attempt emas, yangi revision yaratadi. Qayta testlash alohida tadqiqotda amalga oshiriladi.

Metodika nomi ushbu hujjatda ataylab qat’iy belgilanmagan: taqdim etilgan arxitektura real tayyor metodikalar ro‘yxatini bermaydi. Kod ko‘rilganda mavjud fixture va seed’lar orasidan birinchi pilot metodikasi tanlanadi.

## 6. Backendni o‘zgartirish chegarasi

FastAPI, React, SQLAlchemy va mavjud scoring xizmatlari saqlanadi. Mikroservislar, yangi ma’lumotlar bazasi turi yoki navbat infratuzilmasi bu qisqartirishning sharti emas. Production uchun hujjatda ko‘rsatilgan PostgreSQL yo‘li ishlatiladi; SQLite lokal tekshiruv uchun qoladi.

### Bir tugma — ketma-ket boshqariladigan amallar

Yangi «hammasini bajaruvchi» endpoint majburiy emas. Frontend mavjud API orqali participant/consent, draft response, validate va calculate amallarini boshqaradi. Har request alohida tranzaksiya ekani hisobga olinadi:

- Participant va response ID’lari qayta urinishda qayta ishlatiladi.
- Response yaratishda barqaror attempt kaliti; calculate’da joriy revisionga bog‘langan barqaror idempotency kaliti ishlatiladi.
- Validatsiya xatosi hisoblashga o‘tmaydi, ammo saqlangan qoralama yo‘qolmaydi.
- Hisoblash xatosi javoblarni qayta kiritishni talab qilmaydi.
- Tarmoq javobi yo‘qolsa, mavjud response/result holati olinadi; ko‘r-ko‘rona yangi obyekt yaratilmaydi.
- Rozilik yoki litsenziya qaytarib olingach hisoblash, qayta natija olish va eksport uchun joriy siyosat tekshiriladi. Pilotning odatiy foydalanuvchi oqimida kirish yopiladi; saqlangan tarixni ko‘rish masalasi alohida administrator siyosatiga tegishli.

### Qo‘shiladigan kichik API imkoniyatlari

Quyidagi endpointlar — yangi taklif, mavjud deb da’vo qilinmaydi.

| Endpoint | Vazifa | Ruxsat va qoida |
|---|---|---|
| `POST /api/v1/researches/{id}/close` | `active → closed` | O/A/R; takror chaqirish xavfsiz; yangi yozuvlar va tahrirni bloklaydi |
| `GET /api/v1/researches/{id}/export?format=csv` | Tadqiqotning joriy natijalari | O/A/R; tenant, joriy rozilik va litsenziya tekshiriladi |

Yopish hisoblanmagan joriy revision bo‘lsa avval ularning sonini ko‘rsatadi va ularni hisoblash/tuzatishga qaytaradi. Yopilgan tadqiqot o‘qish va ruxsatli eksport uchun qoladi. Rozilikni qaytarib olish kabi nazorat amallari yopilgandan keyin ham mumkin. Birinchi relizda qayta ochish tugmasi qo‘shilmaydi.

Eksport: har respondent uchun bitta qator; `participant_code`, `methodology_code`, `version_code`, `response_revision`, `result_id`, `calculated_at`, har shkalaning `score` va `validity_status` ustunlari. Normativ mavjud bo‘lsa norm/talqin kodi ham qo‘shiladi. Ball ustunlari tahlil dasturiga mos bo‘ladi; erkin matn ustunlarida formula injection himoyasi saqlanadi. UTF-8 va Excel orqali o‘qilishi tekshiriladi.

Eksportda faqat joriy revision natijasi olinadi. Hisoblanmagan respondentlar va siyosat sabab chiqarilmagan qatorlar soni foydalanuvchiga alohida bildiriladi. Litsenziya butun metodika eksportini bloklasa, fayl umuman berilmaydi. Sahifalash sabab dastlabki 50/100 natijagina tushib qolmasligi server darajasida tekshiriladi.

### Jadvallar va eski imkoniyatlar

Mavjud ma’lumotlar bor-yo‘qligi aniqlanmaguncha jadval va migrationlar o‘chirilmaydi. PII, LegalHold, ImportJob va murakkab registr obyektlari sxemada qolishi mumkin; MVP ularni faol ishlatmaydi. Funksiyani menyudan yashirish serverdagi ruxsatni almashtirmaydi. Ochiq registratsiya va MVPda o‘chiq yozish yo‘llari backend konfiguratsiyasi/ruxsatlari bilan ham cheklanadi.

## 7. Keyingi relizga qoldiriladigan ishlar

| Imkoniyat | Nega hozir olinmaydi | Qaytish sharti |
|---|---|---|
| Respondent uchun test havolasi | Token, rozilik, qoralama, yuborish va takror topshirish alohida oqim | Masofadan yig‘ish pilotning asosiy talabi bo‘lsa ustuvor bo‘ladi |
| CSV import | Participant va consent tayyorlash hamda batch hisoblash hal etilishi kerak | Qo‘lda kiritish pilot uchun asosiy to‘siq bo‘lsa |
| PDF/XLSX hisobot | Birinchi ilmiy tahlil uchun umumiy CSV yetarli deb qabul qilindi | Pilot foydalanuvchilarning aniq talabi |
| Vizual metodika konstruktori | Kontrakt va tekshiruv murakkabligini oshiradi | Bir nechta real metodikani qo‘shish takroriy muammoga aylansa |
| Bir tadqiqotda metodikalar batareyasi | Sessiya va birlashtirilgan hisobot talab qiladi | Bir metodikali oqim ishlashi tasdiqlansa |
| Statistika: faktor tahlili, SEM, korrelatsiya | Mahsulot vazifasini keskin kengaytiradi | Natijalar eksportidan keyingi alohida yo‘nalish |
| AI talqin va tavsiyalar | Deterministik metodika talqinidan tashqari yangi tekshiruv talab qiladi | Alohida mahsulot va baholash rejasi bo‘lsa |
| Ism/telefon/pasport saqlash | Kod bilan pilotni bajarish mumkin | Shaxsni identifikatsiya qilishga amaliy zarurat bo‘lsa |
| To‘lov, obuna, tashkilotni o‘zi ro‘yxatdan o‘tkazish | Pilotni ishga tushirish uchun shart emas | Xizmat modeli tasdiqlansa |
| Fon navbati va katta batchlar | Birinchi oqim sinxron hisoblash bilan tekshiriladi | O‘lchangan yuklama talab qilsa |

## 8. Ishga tushirish uchun zarur sifat chegarasi

Hujjatdagi HTTPS, rate limiting va backup kabi ekspluatatsion masalalarni ommaviy tarmoqqa chiqarishdan oldin bajarish kerak. Ular foydalanuvchiga yangi funksiya qo‘shmaydi, lekin ishlovchi pilotning asosidir.

- HTTPS, cheklangan CORS, barqaror production secret, yopilgan bootstrap va pilotga mos kirish cheklovi.
- Login so‘rovlariga cheklov va server/proxy darajasida so‘rov hajmi chegarasi.
- Tenant scope barcha obyekt operatsiyalarida, eksportda va qayta urinishda tekshiriladi.
- Xom javoblar hamda maxfiy ma’lumotlar logga yozilmaydi.
- PostgreSQL backup va uni qayta tiklash sinovi; ishga tushirish, migration, rollback bo‘yicha qisqa README.
- Saqlash muddati va o‘chirish amali uchun mas’ul belgilanadi. Retention worker bo‘lmasa, bajarilganligi qayd etiladigan qo‘lda jarayon bo‘ladi; saqlash siyosati faqat DB yozuvi bo‘lib qolmaydi.
- Mavjud immutability ORM darajasida ekani inobatga olinadi: bu DBga to‘g‘ridan-to‘g‘ri yozishni to‘liq himoya qiladi degani emas. Ilova uchun DB huquqlari cheklanadi.

## 9. Bajarish ketma-ketligi

| Bosqich | Ish | Tugash dalili |
|---|---|---|
| A | Kodni ochish, README va AGENTS ko‘rsatmalarini o‘qish, konfiguratsiya/migration/testlarni tekshirish | Hujjat va real kod orasidagi farqlar ro‘yxati; lokal ishga tushirish |
| B | Bitta haqiqiy metodikani tayyorlash va etalon misollarini tekshirish | Kalit, ball, norm va foydalanish asosi tasdiqlangan paket |
| C | Menyuni qisqartirish, login va tadqiqot yaratish oqimini yakunlash | Tadqiqotchi texnik sozlamalarsiz ish boshlaydi |
| D | Respondent, rozilik, qoralama va «Natijani hisoblash» oqimi | Bitta respondent bo‘yicha boshidan oxirigacha ishlaydigan demo |
| E | Revision, joriy natija, umumiy CSV, yopish va ruxsat nomuvofiqligini tuzatish | Tuzatish tarixi va eksport qabul sinovidan o‘tadi |
| F | PostgreSQL pilot, backup/restore va real foydalanuvchi sinovi | Sinov dalillari va ishlatish yo‘riqnomasi |

Kod ko‘rilmaguncha kun hisobida muddat va bajarilganlik foizi belgilanmaydi. D bosqichi tugamasdan qo‘shimcha metodika yoki yangi integratsiya boshlanmaydi.

## 10. MVP qabul sinovlari

1. Tadqiqotchi kiradi, tayyor metodikani tanlaydi va tadqiqotni boshlaydi.
2. Rozilik qaydisiz hisoblash ishlamaydi; qayd foydalanuvchi tomonidan aniq kiritiladi.
3. 20 ta sinov respondentini kiritish, qoralamani saqlash va qayta ochish ishlaydi.
4. Kamida uchta oldindan mustaqil hisoblangan etalon natija tizim bilan mos tushadi; ular minimum/maksimum yoki talqin chegarasi, odatiy javob va teskari bandni qamrab oladi.
5. Majburiy javob yo‘q, noto‘g‘ri variant va chegaradan tashqari qiymat bo‘yicha xatolar to‘g‘ri savol yonida ko‘rinadi.
6. Hisoblashni takror bosish va tarmoq uzilishidan keyin qayta urinish bitta revision uchun nusxa natija yaratmaydi.
7. Javob tuzatilsa eski revision/natija saqlanadi; yangi hisoblashgacha «Qayta hisoblash kerak» chiqadi; eksport eski natijani joriy deb bermaydi.
8. Boshqa tashkilot foydalanuvchisi ID almashtirish orqali response, result va eksportga kira olmaydi.
9. Rozilik/litsenziya bekor qilingach qayta hisoblash, cached natija olish va eksport joriy siyosatga muvofiq bloklanadi.
10. Umumiy CSVdagi qatorlar va shkala qiymatlari ekrandagi joriy natijalarga mos; sahifalashdan katta sintetik to‘plamda ham qator yo‘qolmaydi.
11. Yopilgan tadqiqotga yangi respondent/javob kiritish va tahrir rad etiladi; ruxsatli natijalar ko‘rinadi va eksport ishlaydi.
12. Server qayta ishga tushgach ma’lumotlar qoladi; backupdan tiklangan pilot ma’lumotlari ochiladi.

Ushbu sinovlar bajarilganda birinchi MVPni ishlovchi deb hisoblash mumkin. Keyingi funksiyalar pilotdagi kuzatilgan ehtiyojga qarab tanlanadi.

## 11. Kod bilan davom etish uchun kerakli material

Repository havolasi yoki loyiha ZIP’i: `src/`, `frontend/`, `tests/`, `alembic/`, `docs/`, dependency fayllari va `README.md`. Maxfiy kalitlar o‘rniga `.env.example` yetarli. Shundan keyin ushbu topshiriq real kod o‘zgarishlari va tekshirilgan ishga tushirishga aylantiriladi.

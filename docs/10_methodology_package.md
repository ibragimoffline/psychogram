# B bosqichi: pilot metodika paketi talablari

Sana: 2026-10-02. Asos: [08_mvp_pilot_scope.md](08_mvp_pilot_scope.md) (5-bo'lim, B bosqichi)
va [02_methodology_contract.md](02_methodology_contract.md).

Bu hujjat — birinchi pilot metodikasini tizimga kiritish uchun metodika egasi yoki mas'ul
psixolog tayyorlab berishi kerak bo'lgan materiallar ro'yxati. Paket to'liq va tasdiqlangan
bo'lmaguncha metodika katalogda e'lon qilinmaydi. Sintetik `synth_balance_demo` faqat test
uchun; u haqiqiy metodika o'rnida ishlatilmaydi.

## 1. Tanlash mezonlari

Birinchi metodika quyidagilarga mos bo'lishi kerak, aks holda tizim uni hozir qabul qilmaydi:

| Mezon | Sabab |
|---|---|
| Savollar `single_choice` (yoki `integer`/`decimal`/`boolean`) | Boshqa savol turlari MVP whitelist'ida yo'q |
| Natija haqiqiy umumiy ball (`total`) yoki bir nechta omil (`factor`) shkalasi ko'rinishida | Sun'iy umumiy ball yaratilmaydi; ko'p omilli metodikada umumiy ball bo'lmasligi mumkin |
| Ball `sum`, `mean`, `sum_prorated` yoki `weighted_sum` bilan hisoblanadi | Boshqa agregatsiya hozir qo'llab-quvvatlanmaydi |
| Tadqiqot maqsadida foydalanishga yozma ruxsat bor | Litsenziya `research` foydalanish turini qamrashi kerak |
| Respondentni identifikatsiya qilish shart emas | Pilot faqat P001 kabi kod bilan ishlaydi |

## 2. Paket tarkibi

### 2.1. Pasport

- Rasmiy nomi va qisqa kodi (masalan, `xyz_scale`; kichik harf, raqam, `_`).
- Muallif(lar), manba (nashr, yil, DOI yoki havola).
- Maqsadi va qo'llanish doirasi (yosh, populyatsiya), o'rtacha to'ldirish vaqti (daqiqa).
- O'zbek lotin tilidagi tarjima manbasi va uni kim tasdiqlagani.

### 2.2. Savollar

Har bir savol uchun:

| Maydon | Misol |
|---|---|
| Savol kodi | `q01` |
| Savol matni (o'zbek lotin) | — |
| Majburiymi | ha / yo'q |
| Javob variantlari: kod, matn, ball | `a` · "Hech qachon" · `0` |
| Teskari (reverse) savolmi | ha → qaysi diapazonda (`min`, `max`) yoki aniq jadval |

### 2.3. Shkalalar

Har bir shkala (shu jumladan umumiy) uchun:

- Kodi, nomi, qaysi savollar kiradi (va og'irliklari, agar bo'lsa).
- Hisoblash usuli: yig'indi, o'rtacha, proratsiyalangan yig'indi yoki og'irlikli yig'indi.
- Nazariy minimum va maksimum ball.
- Yetishmayotgan javoblar qoidasi: kamida nechta javob kerak, ko'pi bilan nechtasi yo'q bo'lishi mumkin.
  Metodika ruxsat bermasa, yo'q javob nolga aylantirilmaydi va to'ldirilmaydi.
- Ko'rsatiladigan kasr xonalari soni.

### 2.4. Norma va talqin (ixtiyoriy)

Faqat **tasdiqlangan** normativ bo'lsa:

- Normativ manbasi va qaysi populyatsiya uchun ekani.
- Chegaralar: har bir oraliq uchun pastki/yuqori chegara va chegaraning o'zi kirishi.
  Oraliqlar bir-birini qoplamasligi kerak.
- Har bir oraliq uchun talqin matni (o'zbek lotin).

Normativ bo'lmasa, tizim faqat xom ballni ko'rsatadi va "Ushbu guruh uchun normativ talqin
mavjud emas" deb yozadi. "Past/o'rta/yuqori" chegaralari o'ylab topilmaydi.

### 2.5. Foydalanish huquqi (litsenziya)

- Huquq egasi va mualliflik maqomi (ommaviy mulk / ruxsat berilgan / mualliflik huquqi bilan).
- Ruxsatni tasdiqlovchi hujjat (xat, shartnoma, nashrdagi litsenziya) — havola yoki nusxa.
- Ruxsat etilgan foydalanish: tadqiqot; tashkilot turi; hudud.
- Amal qilish muddati (boshlanishi va, bo'lsa, tugashi).
- Savol matnlarini ekranda ko'rsatish va eksport qilish mumkinmi.
- Natija bilan birga ko'rsatilishi shart bo'lgan izoh (disclaimer) va cheklovlar matni.

### 2.6. Etalon misollar

Kamida **3 ta** mustaqil (qo'lda yoki rasmiy kalit bo'yicha) hisoblangan misol. Ular birgalikda
quyidagilarni qamrashi kerak:

1. Minimal yoki maksimal ball.
2. Talqin chegarasiga to'g'ri keladigan ball (normativ bo'lsa).
3. Odatiy aralash javoblar, kamida bitta teskari savol bilan.

Har bir misol uchun: barcha savollarga javob kodlari, kutilgan shkala ballari (yaxlitlanmagan va
ko'rsatiladigan) va kutilgan talqin. Agar yo'q javoblar qoidasi bo'lsa, bitta misol yetishmayotgan
javob bilan bo'lishi tavsiya etiladi.

## 3. Qabul qilish jarayoni

| Qadam | Kim | Natija |
|---|---|---|
| 1. Paketni topshirish | Metodika egasi / psixolog | 2-bo'limdagi materiallar |
| 2. Snapshot JSON tayyorlash | Dasturchi | `docs/02` kontraktiga mos snapshot |
| 3. Etalon misollarni avtomatik test qilish | Dasturchi | Har bir misol uchun pytest testi, ballar mos tushadi |
| 4. Mazmunni tekshirish | Psixolog | Savollar, kalitlar va talqin tizimdagisi bilan bir xilligi tasdiqlanadi |
| 5. Litsenziya va publish | Platform administrator | Licence revision `verified`, versiya `published` |

Qadam 3 va 4 o'tmaguncha versiya publish qilinmaydi. Etalon testlari `tests/` ichida saqlanadi
va har bir o'zgarishda qayta ishga tushadi (pilot qabul sinovi 4).

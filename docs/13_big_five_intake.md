# B bosqichi: "Katta beshlik" metodikasini qabul qilish

Sana: 2026-10-02. Manba: `КАТТА БЕШЛИК МЕТОДИКА.rtf` (o'zbek kirill, 13 bet). Talablar —
[10_methodology_package.md](10_methodology_package.md).

Bu hujjat metodika egasi va mas'ul psixolog uchun: paketdan nima olindi, tizimda qanday
ifodalandi, nima tekshirildi va publish qilishdan oldin nimalarni tasdiqlash kerak.

## 1. Holat

| Qadam ([10](10_methodology_package.md), 3-bo'lim) | Holat |
|---|---|
| 1. Paket topshirildi | Qisman: savollar, kalit, darajalar va talqinlar bor; litsenziya hujjati va etalon misollar yo'q |
| 2. Snapshot tayyorlandi | Bajarildi: [methodologies/big_five.py](../methodologies/big_five.py) |
| 3. Etalon misollar avtomatik testda | Qisman: [tests/test_big_five.py](../tests/test_big_five.py) (3-bo'lim) |
| 4. Psixolog mazmunni tasdiqlaydi | **Kutilmoqda** (5-bo'lim) |
| 5. Litsenziya va publish | **Kutilmoqda**: huquqiy asos yo'q |

Metodika tizimga kiritishga tayyor, lekin 5-bo'limdagi savollar yopilmaguncha **publish qilinmaydi**.

## 2. Tizimdagi ifodasi

- **75 ta savol** (`q01`…`q75`), har biri ikki qutbli juft mulohaza. Javob kodi `-2`, `-1`, `0`,
  `1`, `2`; manbadagi jadval bo'yicha ball 5, 4, 3, 2, 1. Teskari savol yo'q: har bir juftda chap
  mulohaza shkala nomidagi birinchi qutb.
- **Tuzilma** manbadagi javoblar varag'idan olingan: `n`-savol `((n−1) mod 5)+1`-omilga va
  `((n−1) div 15)+1`-birlamchi omilga tegishli. Masalan, 1, 6, 11 → 1.1 (faollik); 64, 69, 74 → 4.5.
  Har bir savolning mazmuni o'z shkalasiga mos kelishini bittalab tekshirdim; nomuvofiqlik topilmadi
  (istisno — 50-savol, 4-bo'lim).
- **30 ta shkala**: 5 ta omil (`factor`, 15 savol, 15–75 ball) va 25 ta birlamchi omil (`subscale`,
  3 savol, 3–15 ball). Umumiy ball yo'q, shuning uchun kontrakt o'zgartirildi (`0b1421e`).
- **Darajalar** manbadan: omil 15–35 past, 36–54 o'rtacha, 55–75 yuqori; birlamchi omil 3–6 past,
  7–11 o'rtacha, 12–15 yuqori.
- **Yetishmayotgan javob**: manbada qoida yo'q, shuning uchun 75 ta savolning hammasi majburiy.
- **Talqin**: omillar uchun yuqori va past daraja matnlari. O'rtacha daraja va birlamchi omillar
  uchun manbada matn yo'q; ular natijada "talqinsiz" ko'rsatiladi.
- **Til**: asl matn `uz-Cyrl`; `uz-Latn` avtomatik transliteratsiya qilingan, uni tekshirish kerak.
- **Mualliflik matnlari repository'da yo'q.** Repository ochiq, shuning uchun mulohaza va talqin
  matnlari faqat mahalliy `methodologies/private/` papkasida (git'ga kirmaydi).
  `scripts/extract_big_five_texts.py` ularni RTF'dan ajratadi va versiya body'sini yig'adi.

## 3. Tekshiruvlar

| Tekshiruv | Natija |
|---|---|
| RTF'dan 75 ta juft mulohaza va 5 ta talqin ajratildi | 75/75, 5/5 |
| Har bir savol bitta birlamchi omilga va uning omiliga tegishli | Test |
| Hamma javob `-2` → omil 75, birlamchi 15 (yuqori); `0` → 45, 9 (o'rtacha); `2` → 15, 3 (past) | Test |
| Manbadagi namuna (A=8 … Y=7): omillar 27, 60, 50, 64, 48 va darajalari | Test |
| Daraja chegaralari: omil 35/36, 54/55; birlamchi 6/7, 11/12 | Test |
| API orqali: versiya → litsenziya → publish → tadqiqot → javob → natija → CSV | Test |
| Manbadagi namunaning foizlari `(ball − min) / (max − min)` formulasiga mos | Qo'lda tekshirildi |

**Muhim cheklov.** Manbadagi namuna faqat birlamchi omil yig'indilarini beradi, savol javoblarini
bermaydi. Javoblar shu yig'indilardan qayta tiklangan. Shu sababli test yig'ish va darajalarni
tekshiradi, lekin [10](10_methodology_package.md) talab qilgan **savol javoblari bilan mustaqil
hisoblangan ≥3 misol** hali yo'q.

## 4. Topilgan nomuvofiqliklar

| № | Joy | Nima | Tizimda nima qilindi |
|---|---|---|---|
| 1 | Sarlavha | "Мак Крае ва П.Коста" deyilgan. Lekin tuzilma (75 ta ikki qutbli juft, −2…+2, 5×5 birlamchi omil) A.B. Xromovning "Пятифакторный опросник личности" (5PFQ, 2000) bilan mos keladi, u esa Tsuji va boshq. FFPQ'siga asoslangan. McCrae & Costa NEO-PI tuzilishi boshqacha | Manba sifatida hech biri yozilmadi |
| 2 | IV omil nomi | Ro'yxatda "барқарорлик – беқарорлик", talqin bo'limida "беқарорлик – барқарорлик". Chap mulohazalar beqarorlikni bildiradi, demak **yuqori ball = emotsional beqarorlik** | "Беқарорлик – барқарорлик", kod `f4_emotional_instability` |
| 3 | Omil nomlari | II: "Меҳрибонлик – алоҳидалик" va "Яқинлик – холислик"; III: "…ғайри ихтиёрий" va "…импульсивлик"; V: "Таъсирчанлик – ишчанлик" va "Экспрессивлик – практиклик" | Ro'yxatdagi nomlar olindi |
| 4 | 3.2 nomi | "Қатъиятлик – қатъиятлилик" (ikki qutb bir xil) | "Қатъиятлилик – қатъиятсизлик" |
| 5 | 5.2 nomi | "Билимга қизиқувчанлик – реалист", lekin 20, 25, 30-savollar xayolparastlik haqida (5PFQ'da "мечтательность – реалистичность") | Nom saqlandi, kod `s5_2_imagination` |
| 6 | 4.2 nomi | "Кескинлик – кучсизлик" (qarama-qarshi qutb noaniq) | "Кескинлик – бўшашганлик" |
| 7 | 1.5 nomi | "Намоён қилиш – айбдорлик ҳиссидан қочиш" (5PFQ'da "привлечение внимания – избегание внимания") | Saqlandi |
| 8 | 50-savol | O'ng mulohaza ("Бошқа одамлар менга қараганда ҳис-туйғуси камроқдек туюлади") ham sezgirlik qutbini bildiradi; juft ikki qutbli emas, tarjima xatosi bo'lishi mumkin | O'zgartirilmadi |
| 9 | V omil, yuqori talqin | "Кўпроқ моддий таъминланганликка эътибор қаратадилар" — past daraja matnidagi "моддий қадриятлар" bilan zid | O'zgartirilmadi |
| 10 | Javoblar varag'i | 49 o'rniga "99", 57 o'rniga "77" | Tuzilmaga ta'siri yo'q |
| 11 | Imlo | 16 "бўйруқ", 27 "рақботлашиш", 39 "камдан ҳолларда", 46 "мусобоқа", 58 "наоса", 72 o'ng mulohaza grammatikasi, 75 "эатман" | Matn o'zgartirilmadi |
| 12 | Talqin matnlari | III past: "асоциал хатти-ҳаракатларга мойил", "нопоклик ва ёлғондан қайтмайди" — tadqiqot natijasida ko'rsatish uchun keskin | O'zgartirilmadi |
| 13 | Darajalar | 15–35/36–54/55–75 va 3–6/7–11/12–15 xom ball oralig'ini bo'lish ko'rinishida; normativ namuna, yosh va jins ko'rsatilmagan | "Daraja" sifatida kiritildi, normativ talqin deb nomlanmadi |

## 5. Publish qilishdan oldin kerak

1. **Huquqiy asos.** Kimning metodikasi (4.1), o'zbekcha tarjima muallifi va tadqiqotda foydalanishga
   ruxsat hujjati. Ularsiz litsenziya `verified` qilinmaydi.
2. **Psixolog tasdig'i**: 4-bo'limdagi 2–9 va 12-bandlar bo'yicha qaror; omil va birlamchi omil nomlari.
3. **Darajalar manbasi** (4.13): agar ular normativ bo'lmasa, natijada "past/o'rtacha/yuqori"
   ko'rsatilsinmi yoki faqat xom ball?
4. **Kamida 3 ta mustaqil etalon misol**: 75 ta javob va qo'lda hisoblangan 30 ta ball bilan.
   Ular `tests/test_big_five.py`ga qo'shiladi.
5. **Lotin yozuvi**: transliteratsiyani o'qib chiqish yoki rasmiy lotin matnini berish.
6. **To'ldirish vaqti**: hozir 20 daqiqa deb taxmin qilingan.

## 6. Mahalliy tekshirish

```sh
python scripts/extract_big_five_texts.py "КАТТА БЕШЛИК МЕТОДИКА.rtf" --payload methodologies/private/big_five_version.json
pytest tests/test_big_five.py
```

`methodologies/private/big_five_version.json` — `POST /api/v1/methodologies/{id}/versions` uchun
tayyor body. Uni faqat lokal yoki staging bazaga yuklash mumkin; litsenziya tasdiqlanmaguncha
pilot bazasida publish qilinmaydi.

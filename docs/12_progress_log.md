# Bajarilgan ishlar jurnali

Bu fayl pilot MVP bo'yicha qilingan ishlarni bir joyda jamlaydi: har bosqichda nima qilindi,
qaysi commit'lar bilan, qanday tekshirildi va nima ochiq qoldi. Reja —
[08_mvp_pilot_scope.md](08_mvp_pilot_scope.md), kodning joriy holati —
[ARCHITECTURE.md](../ARCHITECTURE.md). Har bir commit'ning to'liq sababi `git log`da yozilgan.

Yangi ish qo'shilganda shu faylning oxiriga yangi bo'lim yoziladi.

## Umumiy holat (2026-10-02)

| Bosqich | Holat | Branch | `main`da |
|---|---|---|---|
| Arxitektura xaritasi | Bajarildi | — | ha |
| A — kod va hujjat solishtiruvi | Bajarildi | `fix/stage-a-gates` | ha |
| B — haqiqiy metodika | **Kutilmoqda**: paket foydalanuvchidan keladi | — | — |
| C — kirish, menyu, tadqiqot yaratish | Bajarildi | `feat/stage-c-onboarding` | ha |
| D — javob formasi | Bajarildi | `feat/stage-d-response-flow` | ha |
| E — yopish, umumiy CSV | Bajarildi | `feat/stage-e-close-export` | ha |
| F — PostgreSQL, backup, qo'llanma | Lokal qismi bajarildi | `feat/stage-f-pilot-ops` | ha |
| Qo'shimcha mustahkamlash | Bajarildi | `feat/pilot-hardening` | ha |
| Excel CSV tuzatishi | Bajarildi | `fix/excel-csv-dialect` | **yo'q** (PR kutmoqda) |

Oxirgi tekshiruv: backend 77 test, frontend 55 test o'tdi; black, flake8, mypy, ESLint,
TypeScript va build toza.

## 0. Arxitektura xaritasi va pilot topshirig'i

- [ARCHITECTURE.md](../ARCHITECTURE.md) yozildi: qatlamlar, 30 ta model, barcha servis
  funksiyalari, API, frontend, testlar, xato kodlari.
- Foydalanuvchi bergan pilot topshirig'i [08_mvp_pilot_scope.md](08_mvp_pilot_scope.md) sifatida saqlandi.

## A bosqichi — kod va hujjat solishtiruvi

**Natija:** [09_stage_a_findings.md](09_stage_a_findings.md), 16 ta topilma (F-01…F-16).

**Qanday tekshirildi:** backend testlari, migratsiyalar (upgrade/downgrade), frontend
typecheck/lint/test/build, ishlab turgan serverda pilot oqimi bo'yicha 32 ta HTTP tekshiruv.

**Muhim topilmalar:** rozilik qaytarib olingach eski natija hali ham olinardi; takroriy respondent
kodi 500 xatoga olib kelardi; validatsiya xatolari API'da qaytmasdi; auditorga eksport tugmasi
ko'rinib, server rad etardi; loyiha git'da emas edi.

**Tuzatishlar:**

| Commit | Nima |
|---|---|
| `712826f` | Loyiha git'ga olindi, GitHub'ga ulandi (F-15) |
| `ad77bcb` | Rozilik/litsenziya tekshiruvi keshdan oldin va natijani o'qishda ham (F-01, F-02) |
| `d74f81a` | Takroriy respondent va retention kodi → 409 (F-03, F-04) |
| `9861703` | Auditordan eksport tugmasi olindi (F-07) |
| `8ccd3b2` | Beqaror frontend testi tuzatildi (F-08) |
| `8490da5` | Validatsiya xatolari savol bo'yicha qaytariladi (F-05) |
| `e727ca2`, `7b398dd`, `c2d2c93` | Hujjat va formatlash |

## B bosqichi — haqiqiy metodika

- [10_methodology_package.md](10_methodology_package.md) — metodika egasi tayyorlashi kerak
  bo'lgan paket talablari (savollar, kalit, shkalalar, norma, litsenziya, ≥3 etalon misol).
- **Ochiq:** paket hali kelmagan. Hozir faqat sintetik test metodikasi bor.

## C bosqichi — kirish, menyu, tadqiqot yaratish

| Commit | Nima |
|---|---|
| `568b045` | Ochiq registratsiya default o'chiq; tashkilotni platform admin yaratadi (F-09) |
| `85eeccd` | CSV import default o'chiq (birinchi relizda yo'q) |
| `37314fa` | Metodika ro'yxatlarida metodika nomi |
| `7764fd6` | Menyu: faqat Tadqiqotlar va Metodikalar; registratsiya va import yashirildi |
| `0542e2f` | "Yaratish va boshlash"; avval UI'da yaratilgan tadqiqotni boshlab bo'lmasdi (F-12) |
| `d49c7a6` | Sessiya tugaganda login sahifasiga qaytish |
| `5db5617` | B paketi talablari va hujjatlar |

**Tekshiruv:** server pilot default sozlamalari bilan: registratsiya 404, admin tashkilot yaratadi,
import 404, owner tashkilot yarata olmaydi.

## D bosqichi — javob formasi

| Commit | Nima |
|---|---|
| `fda6e3a` | Tuzatish sababi faqat tasdiqlangan javobni o'zgartirganda shart |
| `10d0902` | Javoblar ro'yxatida natija holati ("Qayta hisoblash kerak") |
| `493e037` | Yagona forma: respondent kodi, rozilik, savollar, qoralama, hisoblash; qayta urinishda dublikat yo'q |
| `13c22d9` | Hujjatlar |

**Tekshiruv:** formaning so'rovlar ketma-ketligi haqiqiy backend'da qayta ijro etildi, 17/17.
Yo'l-yo'lakay topilgan xato: URL o'zgarganda forma qayta mount bo'lib, xatolarni yo'qotardi — tuzatildi.

## E bosqichi — yopish va umumiy CSV

| Commit | Nima |
|---|---|
| `e4c3123` | `closed` holati va `POST /researches/{id}/close` (F-10) |
| `e22ca2f` | Tadqiqot bo'yicha umumiy CSV, sahifalashsiz (F-11) |
| `d343507` | Natija joriy yoki eskirganini belgilash |
| `7c0d90b` | Frontend: yakunlash, CSV yuklash, eskirgan natija ogohlantirishi |
| `b9d27a8` | Hujjatlar |

**Tekshiruv:** 105 respondent bilan eksport (sahifa chegarasidan ko'p); haqiqiy serverda 9/9.

**Spec'dan ongli farq:** hisoblanmagan javoblar bo'lsa yopish ularning sonini ko'rsatadi, lekin
"Baribir yakunlash" yo'li ham bor — aks holda bitta tugallanmagan qoralama tadqiqotni abadiy ochiq qoldirardi.

## F bosqichi — PostgreSQL, backup, qo'llanma

| Commit | Nima |
|---|---|
| `ade3455` | Test to'plamini PostgreSQL'da ishga tushirish (`PSYCHOGRAM_TEST_DATABASE_URL`) |
| `697cf63` | Cheklangan `psychogram_app` roli va `scripts/pilot_smoke.py` |
| `25096b2` | `scripts/compare_databases.py` — tiklangan bazani solishtirish |
| `d1b594b` | [11_pilot_operations.md](11_pilot_operations.md) va nginx namunasi |

**Tekshiruv** (bir martalik PostgreSQL 18 klasteri; foydalanuvchi xizmatiga tegilmagan): migratsiyalar,
74 test PostgreSQL'da, smoke 16/16, ilova roli bilan tarixni o'zgartirish rad etildi, backup →
tiklash → 34/34 jadval mos, tiklangan bazada eksport bayt-ma-bayt bir xil.

## Qo'shimcha mustahkamlash

| Commit | Nima |
|---|---|
| `e60eee9` | Tadqiqotlar ro'yxatida metodika va "hisoblangan / respondentlar" |
| `b9c8eb2` | `0003` migratsiyasi: tasdiqlangan revision va nashr qilingan versiyani baza trigger'i himoya qiladi |

## Excel CSV tuzatishi

| Commit | Nima |
|---|---|
| `dd84166` | Eksportga `dialect=excel` (`;` va kasr `,`); ikki tugma: "Excel uchun CSV", "CSV (SPSS, R)" |

**Topilma:** Excel 16 va Windows `ru-RU` sozlamasida oddiy CSV bitta ustunga tushadi, `;` + nuqta
varianti esa `3.33`ni jimgina sanaga aylantiradi. Tuzatilgan fayl o'sha Excel'da to'g'ri ochildi.

## Ochiq masalalar

1. **B:** haqiqiy metodika paketi va etalon misollar.
2. **Haqiqiy server:** TLS, proxy (namuna sinalmagan), tiklash mashqini o'sha muhitda takrorlash.
3. **Saqlash muddati:** mas'ul shaxs va o'chirish tartibi; MVP'da natijani o'chiradigan vosita yo'q.
4. **MFA / login rate limit:** proxy yoki IdP darajasida.
5. **Real foydalanuvchi sinovi:** 1–2 tadqiqotchi, kamida 20 respondent ([11](11_pilot_operations.md), 9-bo'lim).
6. **Brauzerda ko'rib chiqish:** ekranlar avtomatik testlangan, lekin vizual tekshirilmagan.
7. **en-US Excel:** Excel varianti mos emas; "Data → From Text/CSV" orqali ochiladi.

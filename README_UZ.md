# Nova West LC — Telegram placement test bot

## Imkoniyatlar
- `/start` orqali Beginner va Intermediate test tanlovi
- Har bir savol uchun 60 soniyalik vaqt
- A/B/C/D javob variantlari
- Oldingisi, Keyingisi va Yakunlash tugmalari
- Javoblar bo‘yicha 100 ballik natija
- A1–C1 daraja tavsifi
- Natijalarni SQLite bazasida saqlash (`/result`)
- Testni bekor qilish (`/cancel`)

## Muhim: savollar banki
`data/questions.json` ichida hozircha namuna (demo) savollar bor. Avvalgi suhbatda yuborilgan Nova West LC uchun aniq 20 ta Beginner va 20 ta Intermediate savolning to‘liq matni ushbu ish muhitida qayta olinmadi. Shu sababli namuna savollarni aniq siz yuborgan savollar deb ko‘rsatmadim. Bot ishga tushadi, lekin rasmiy foydalanishdan oldin JSON ichidagi demo savollarni sizning asl savollaringiz bilan almashtiring.

Har bir savol quyidagi shaklda bo‘lishi kerak:
```json
{
  "id": 1,
  "question": "Choose the correct answer.",
  "options": {"A": "Option 1", "B": "Option 2", "C": "Option 3", "D": "Option 4"},
  "correct_answer": "B",
  "points": 2,
  "active": true
}
```
Beginner va Intermediate savollari alohida ro‘yxatlarda turadi. Har bir testning xom ballari avtomatik ravishda 100 ballik tizimga normallashtiriladi.

## PyCharm orqali ishga tushirish (Windows)
1. ZIP faylni oching.
2. PyCharm’da `nova_west_lc_bot` papkasini oching.
3. PyCharm terminalida quyidagilarni bajaring:
   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```
4. `.env.example` faylidan nusxa olib, nusxasini `.env` deb nomlang.
5. Telegram’da `@BotFather` orqali bot yarating va tokenni `.env` ichiga kiriting:
   `BOT_TOKEN=123456:ABC...`
6. Ishga tushiring:
   ```powershell
   python bot.py
   ```

## Eslatma
- Bot ishlashi uchun kompyuter yoki serverda Python jarayoni ish holatida turishi kerak.
- Tokenni hech kimga yubormang va GitHub’ga `.env` faylini yuklamang.
- Savol va javoblar foydalanuvchiga Telegram tugmalari orqali ko‘rsatiladi.

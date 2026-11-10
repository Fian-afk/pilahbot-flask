# Pilahbot

Chatbot rule-based untuk membantu mengenali dan memilah sampah rumah tangga. Basis
pengetahuan di `knowledge_base.json` disusun dari sheet **Kategori**, **Intents**,
**Pertanyaan_Respons**, dan **Rules_IF_THEN** pada `PilahBot_Knowledge_Mapping.xlsx`.
Urutan serta prioritas IF-THEN pada workbook digunakan untuk menentukan respons;
chatbot tidak menggunakan LLM. Pertanyaan spesifik tentang sampah anorganik tetap
ditangani oleh intent-nya meskipun juga memuat kata "daur ulang".

## Menjalankan aplikasi

```powershell
cd pilahbot-chatbot-flask
python -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
python app.py
```

Buka <http://127.0.0.1:5000>.

## API

`POST /api/chat`

```json
{"message": "Baterai bekas dibuang ke mana?"}
```

Respons mencakup jawaban, intent, kategori, dan ID rule yang cocok. Pesan kosong
atau lebih dari 500 karakter ditolak dengan status `400`.

## Pengujian

```powershell
python -m pytest
```

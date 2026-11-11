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

## Menjalankan versi CLI

PilahBot juga dapat dijalankan langsung di terminal melalui `cli.py`:

```powershell
# Mode interaktif (sesi obrolan langsung)
python cli.py

# Mode sekali tanya (single-query)
python cli.py "Botol plastik termasuk sampah apa?"

# Mode dengan detail kecocokan (rule, intent, skor)
python cli.py "Baterai bekas dibuang ke mana?" -v

# Melihat ringkasan statistik database
python cli.py --stats
```

Perintah khusus dalam mode interaktif:
- `/bantuan` atau `/help`: melihat daftar perintah
- `/statistik` atau `/stats`: melihat ringkasan statistik
- `/debug` atau `/verbose`: toggle tampilan informasi pencocokan
- `/clear` atau `/cls`: bersihkan layar terminal
- `keluar`, `exit`, atau `quit`: mengakhiri sesi chat

## Statistik

Buka <http://127.0.0.1:5000/statistik> atau pilih **Statistik** dari halaman chat.
Halaman ini menampilkan total pertanyaan, persentase dikenali, jumlah pertanyaan
tidak dikenali, jumlah sesi pengunjung, distribusi pertanyaan per intent, dan
daftar pertanyaan yang belum dikenali beserta skor serta waktu pencatatan.
Pertanyaan dan ID sesi disimpan lokal di `instance/pilahbot.sqlite3`, sehingga
data statistik tetap ada setelah server dimulai ulang.
Skor kemiripan berada pada rentang `0.00`–`1.00`; pertanyaan dikenali jika
mencapai ambang `0.45`. Nilainya dapat diubah melalui environment variable
`THRESHOLD`.

## Knowledge base

`knowledge_base.json` menyimpan konfigurasi bot, kategori, intent, jawaban, dan
aturan pencocokan. Setiap intent memiliki daftar `answers` dan `rules`; aturan
merujuk jawaban menggunakan `answer_ids`, sehingga satu jawaban dapat digunakan
oleh lebih dari satu aturan tanpa diduplikasi. ID dan nama intent pada jawaban
mewarisi intent induknya. Kondisi aturan disimpan pada `when`, sedangkan `priority`
menentukan urutan pemeriksaan. Respons cadangan disimpan terpisah pada `fallback`.

Jumlah Q&A dan daftar aturan terkait tidak disimpan sebagai angka atau daftar
terpisah karena dapat diturunkan dari `answers` dan `rules`. ID kategori, intent,
aturan, dan jawaban tetap disediakan sebagai pengenal stabil untuk hubungan antar
data dan informasi hasil pencocokan. Jika struktur JSON diubah, mesin chatbot
serta pengujian juga perlu disesuaikan.

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

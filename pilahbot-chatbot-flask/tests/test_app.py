import pytest

from app import create_app
from chatbot.database import get_statistics, record_question


@pytest.fixture
def client(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "pilahbot.sqlite3"),
    })
    return app.test_client()


@pytest.mark.parametrize(
    ("message", "rule_id", "intent", "answer_part"),
    [
        ("Halo Pilahbot", "R01", "INT01", "Selamat datang"),
        ("Botol plastik termasuk sampah apa?", "R02", "INT02", "anorganik"),
        ("Kulit pisang termasuk sampah apa?", "R03", "INT02", "organik"),
        ("Baterai bekas dibuang ke mana?", "R17", "INT05", "limbah B3"),
        ("Botol plastik dibuang ke mana?", "R18", "INT07", "bank sampah"),
        ("Kertas berminyak termasuk apa?", "R23", "INT02", "residu"),
        ("Kertas termasuk sampah apa?", "R24", "INT02", "Kertas bersih"),
        ("Bisakah sampah anorganik didaur ulang?", "R13", "INT04", "Pisahkan berdasarkan jenisnya"),
        ("Tisu bekas bisa didaur ulang?", "R25", "INT06", "residu"),
        ("Bagaimana cara membuat kompos?", "R06", "INT09", "wadah kompos"),
        ("Sampah apa saja yang bisa didaur ulang?", "R07", "INT08", "Plastik bersih"),
        ("Bagaimana cara mendaur ulang sampah plastik?", "R07", "INT08", "jenis plastik"),
        ("Apa manfaat memilah sampah?", "R08", "INT11", "pengolahan"),
        ("Sampai jumpa", "R22", "INT12", "Sampai jumpa"),
    ],
)
def test_chat_mematuhi_aturan_prioritas(client, message, rule_id, intent, answer_part):
    response = client.post("/api/chat", json={"message": message})

    assert response.status_code == 200
    data = response.get_json()
    assert data["rule_id"] == rule_id
    assert data["intent"] == intent
    assert 0.45 <= data["score"] <= 1
    assert answer_part.lower() in data["reply"].lower()


def test_chat_tidak_dikenali_menggunakan_fallback(client):
    response = client.post("/api/chat", json={"message": "Bagaimana cuaca hari ini?"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["rule_id"] == "R10"
    assert data["intent"] == "FB01"
    assert 0 <= data["score"] < 0.45
    assert "belum mengerti" in data["reply"]


@pytest.mark.parametrize(
    "message",
    [
        "kabel charger rusak termasuk sampah apa",
        "kondom termasuk apa",
    ],
)
def test_pertanyaan_tidak_dikenali_menyimpan_skor_kemiripan(client, message):
    response = client.post("/api/chat", json={"message": message})

    assert response.status_code == 200
    data = response.get_json()
    assert data["intent"] == "FB01"
    assert 0 < data["score"] < 0.45

    statistics = get_statistics(client.application.config["DATABASE"])
    assert statistics["unknown_questions"][0]["question"] == message
    assert statistics["unknown_questions"][0]["score"] == data["score"]


@pytest.mark.parametrize(
    "payload",
    [None, {}, {"message": ""}, {"message": "   "}, {"message": 42}],
)
def test_chat_menolak_pesan_kosong_atau_payload_tidak_valid(client, payload):
    response = client.post("/api/chat", json=payload)

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_chat_menolak_pesan_terlalu_panjang(client):
    response = client.post("/api/chat", json={"message": "a" * 501})

    assert response.status_code == 400


def test_beranda_memuat_tampilan_chat(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Pilahbot" in response.get_data(as_text=True)
    assert "Tulis pertanyaanmu" in response.get_data(as_text=True)
    assert "/statistik" in response.get_data(as_text=True)


def test_halaman_statistik_menampilkan_ringkasan_dan_pertanyaan_tidak_dikenali(client):
    client.post("/api/chat", json={"message": "Baterai bekas dibuang ke mana?"})
    client.post("/api/chat", json={"message": "Apakah alien bisa memilah sampah?"})

    response = client.get("/statistik")
    html = response.get_data(as_text=True)
    statistics = get_statistics(client.application.config["DATABASE"])

    assert response.status_code == 200
    assert statistics["total"] == 2
    assert statistics["recognition_rate"] == 50
    assert statistics["unrecognized"] == 1
    assert statistics["visitors"] == 1
    assert sum(item["count"] for item in statistics["intents"]) == 2
    assert sum(item["proportion"] for item in statistics["intents"]) == 100
    assert statistics["unknown_questions"][0]["question"] == "Apakah alien bisa memilah sampah?"
    assert 0 < statistics["unknown_questions"][0]["score"] < 0.45
    assert statistics["unknown_questions"][0]["created_at"]
    assert "Total pertanyaan" in html
    assert "Persentase dikenali" in html
    assert "Jumlah tidak dikenali" in html
    assert "Jumlah pengunjung (sesi)" in html
    assert "Ambang pengenalan saat ini: 0.45" in html
    assert "Waste_Disposal" in html
    assert "Apakah alien bisa memilah sampah?" in html
    assert f'{statistics["unknown_questions"][0]["score"]:.2f}' in html


def test_statistik_menghitung_sesi_pengunjung_berbeda(client):
    client.post("/api/chat", json={"message": "Halo"})
    second_visitor = client.application.test_client()
    second_visitor.post("/api/chat", json={"message": "Halo"})

    client.get("/statistik")
    statistics = get_statistics(client.application.config["DATABASE"])

    assert statistics["total"] == 2
    assert statistics["visitors"] == 2


def test_skor_pertanyaan_lama_diperbarui_saat_aplikasi_dibuka(tmp_path):
    database = str(tmp_path / "pilahbot.sqlite3")
    app = create_app({"TESTING": True, "DATABASE": database})
    record_question(
        database,
        "visitor",
        "kabel charger rusak termasuk sampah apa",
        {
            "intent": "FB01",
            "intent_name": "Fallback",
            "score": 0.0,
        },
        "2026-11-11 00:30:50",
    )

    refreshed_app = create_app({"TESTING": True, "DATABASE": database})
    statistics = get_statistics(database)

    assert statistics["unknown_questions"][0]["score"] == pytest.approx(0.3292)
    assert refreshed_app.test_client().get("/statistik").status_code == 200

import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app({"TESTING": True})
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
    assert answer_part.lower() in data["reply"].lower()


def test_chat_tidak_dikenali_menggunakan_fallback(client):
    response = client.post("/api/chat", json={"message": "Bagaimana cuaca hari ini?"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["rule_id"] == "R10"
    assert data["intent"] == "FB01"
    assert "belum mengerti" in data["reply"]


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

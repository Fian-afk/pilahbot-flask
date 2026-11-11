import subprocess
import sys
from pathlib import Path
import pytest

from chatbot.database import get_statistics, initialize_database


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "cli_test.sqlite3"
    initialize_database(str(db_file))
    return db_file


def run_cli(*args, input_text=None):
    cmd = [sys.executable, "cli.py", *args]
    return subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_single_query():
    result = run_cli("Botol plastik termasuk sampah apa?", "--no-record")
    assert result.returncode == 0
    assert "PilahBot:" in result.stdout
    assert "anorganik" in result.stdout.lower()


def test_cli_single_query_flag():
    result = run_cli("-q", "Baterai bekas dibuang ke mana?", "--no-record")
    assert result.returncode == 0
    assert "PilahBot:" in result.stdout
    assert "b3" in result.stdout.lower()


def test_cli_verbose():
    result = run_cli("Botol plastik termasuk sampah apa?", "--no-record", "-v")
    assert result.returncode == 0
    assert "[Detail] Rule: R02" in result.stdout
    assert "INT02" in result.stdout
    assert "Skor:" in result.stdout


def test_cli_records_to_database(temp_db):
    result = run_cli("Kulit pisang termasuk sampah apa?", "-d", str(temp_db))
    assert result.returncode == 0

    stats = get_statistics(str(temp_db))
    assert stats["total"] == 1
    assert stats["recognized"] == 1


def test_cli_stats_flag(temp_db):
    # Kirim satu pertanyaan dulu
    run_cli("Kulit pisang termasuk sampah apa?", "-d", str(temp_db))

    # Cek output flag --stats
    result = run_cli("--stats", "-d", str(temp_db))
    assert result.returncode == 0
    assert "STATISTIK PILAHBOT" in result.stdout
    assert "Total pertanyaan       : 1" in result.stdout


def test_cli_interactive_flow(temp_db):
    interactive_input = "/bantuan\n/debug\nBotol plastik termasuk apa?\n/stats\nkeluar\n"
    result = run_cli("-d", str(temp_db), input_text=interactive_input)

    assert result.returncode == 0
    assert "PILAHBOT - CLI Version" in result.stdout
    assert "Perintah Tersedia:" in result.stdout
    assert "[Mode Debug/Verbose]: aktif" in result.stdout
    assert "PilahBot: Botol plastik termasuk sampah anorganik" in result.stdout
    assert "STATISTIK PILAHBOT" in result.stdout
    assert "Sampai jumpa" in result.stdout


def test_cli_invalid_knowledge_base(tmp_path):
    invalid_kb = tmp_path / "non_existent.json"
    result = run_cli("-k", str(invalid_kb), "Halo")
    assert result.returncode == 1
    assert "Error: Knowledge base file tidak ditemukan" in result.stderr

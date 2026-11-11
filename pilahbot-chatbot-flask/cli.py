#!/usr/bin/env python3
"""Antarmuka Baris Perintah (CLI) untuk Chatbot PilahBot."""

import argparse
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from chatbot.database import (
    get_statistics,
    initialize_database,
    record_question,
)
from chatbot.engine import DEFAULT_THRESHOLD, ChatbotEngine

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_KB_PATH = BASE_DIR / "knowledge_base.json"
DEFAULT_DB_PATH = BASE_DIR / "instance" / "pilahbot.sqlite3"


def print_banner(bot_name: str, description: str, threshold: float) -> None:
    """Menampilkan banner selamat datang pada mode interaktif CLI."""
    border = "=" * 60
    print(border)
    print(f" {bot_name.upper()} - CLI Version")
    print(f" {description}")
    print(f" Ambang kemiripan (threshold): {threshold:.2f}")
    print(border)
    print("Petunjuk:")
    print(" - Ketik pertanyaanmu dan tekan Enter.")
    print(" - Ketik '/bantuan' untuk daftar perintah khusus.")
    print(" - Ketik 'keluar', 'exit', atau 'quit' untuk mengakhiri sesi.")
    print(border)
    print()


def display_stats(db_path: Path, threshold: float) -> None:
    """Menampilkan ringkasan statistik interaksi dari basis data."""
    if not db_path.exists():
        print(f"\n[Info] Database belum ditemukan di {db_path}.")
        return

    stats = get_statistics(str(db_path))
    total = stats["total"]
    print("\n" + "=" * 50)
    print(" STATISTIK PILAHBOT")
    print("=" * 50)
    print(f"Total pertanyaan       : {total}")
    print(f"Pertanyaan dikenali    : {stats['recognized']} ({stats['recognition_rate']}%)")
    print(f"Pertanyaan tdk dikenali: {stats['unrecognized']}")
    print(f"Jumlah pengunjung (sesi): {stats['visitors']}")
    print(f"Ambang batas (threshold): {threshold:.2f}")

    if stats["intents"]:
        print("\nDistribusi Intent:")
        for item in stats["intents"]:
            bar = "#" * int(item["proportion"] / 5)
            print(f" - {item['intent']:<22}: {item['count']:>3} ({item['proportion']:>5.1f}%) {bar}")

    if stats["unknown_questions"]:
        print("\nPertanyaan Belum Dikenali Terbaru (maksimal 5):")
        for uq in stats["unknown_questions"][:5]:
            print(f" - \"{uq['question']}\" (skor: {uq['score']:.2f}, waktu: {uq['created_at']})")
    print("=" * 50 + "\n")


def print_help() -> None:
    """Menampilkan daftar perintah khusus pada mode interaktif."""
    print("\nPerintah Tersedia:")
    print("  /bantuan, /help     : Menampilkan bantuan ini")
    print("  /statistik, /stats  : Menampilkan statistik pertanyaan dari database")
    print("  /debug, /verbose    : Mengaktifkan/menonaktifkan detail pencocokan")
    print("  /clear, /cls        : Membersihkan layar terminal")
    print("  keluar, exit, quit  : Mengakhiri obrolan CLI\n")


def ask_and_respond(
    engine: ChatbotEngine,
    message: str,
    db_path: Path | None = None,
    session_id: str | None = None,
    verbose: bool = False,
) -> dict:
    """Memproses pesan dengan engine, mencatat ke database (bila ada), dan mencetak balasan."""
    result = engine.reply(message)

    if db_path is not None and session_id is not None:
        try:
            record_question(
                str(db_path),
                session_id,
                message,
                result,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        except Exception as err:
            if verbose:
                print(f"[Peringatan] Gagal menyimpan ke database: {err}", file=sys.stderr)

    print(f"\nPilahBot: {result['reply']}")

    if verbose:
        print(f"  [Detail] Rule: {result.get('rule_id')} | Intent: {result.get('intent')} "
              f"({result.get('intent_name')}) | Kategori: {result.get('category')} | Skor: {result.get('score'):.4f}")
        if result.get("matched_question"):
            print(f"  [Cocok] \"{result['matched_question']}\"")
    print()

    return result


def run_interactive(
    engine: ChatbotEngine,
    db_path: Path | None,
    session_id: str,
    threshold: float,
    verbose: bool = False,
) -> None:
    """Menjalankan loop percakapan interaktif di terminal."""
    bot_name = engine.knowledge.get("name", "PilahBot")
    description = engine.knowledge.get("description", "Asisten Pemilahan Sampah")
    print_banner(bot_name, description, threshold)

    current_verbose = verbose

    while True:
        try:
            user_input = input("Anda: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nSampai jumpa! Terima kasih telah menggunakan PilahBot.")
            break

        if not user_input:
            continue

        lower_input = user_input.lower()

        if lower_input in {"keluar", "exit", "quit", "q", ":q"}:
            print("\nSampai jumpa! Jaga kebersihan dan pilah sampahmu ya!")
            break

        if lower_input in {"/bantuan", "/help"}:
            print_help()
            continue

        if lower_input in {"/statistik", "/stats"}:
            if db_path:
                display_stats(db_path, threshold)
            else:
                print("\n[Info] Fitur database dinonaktifkan (--no-record).\n")
            continue

        if lower_input in {"/debug", "/verbose"}:
            current_verbose = not current_verbose
            status = "aktif" if current_verbose else "nonaktif"
            print(f"\n[Mode Debug/Verbose]: {status}\n")
            continue

        if lower_input in {"/clear", "/cls"}:
            os.system("cls" if os.name == "nt" else "clear")
            print_banner(bot_name, description, threshold)
            continue

        ask_and_respond(
            engine=engine,
            message=user_input,
            db_path=db_path,
            session_id=session_id,
            verbose=current_verbose,
        )


def build_parser() -> argparse.ArgumentParser:
    """Membangun argument parser untuk CLI."""
    parser = argparse.ArgumentParser(
        prog="python cli.py",
        description="PilahBot CLI - Chatbot panduan pemilahan sampah rumah tangga berbasis aturan.",
    )
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="Pertanyaan satu kali langsung (single-query mode). Jika dikosongkan, masuk ke mode interaktif.",
    )
    parser.add_argument(
        "-q",
        "--question",
        dest="flag_query",
        default=None,
        help="Opsi alternatif untuk mengirim pertanyaan langsung.",
    )
    parser.add_argument(
        "-k",
        "--knowledge-base",
        dest="kb_path",
        type=Path,
        default=DEFAULT_KB_PATH,
        help=f"Path ke file knowledge_base.json (default: {DEFAULT_KB_PATH.name})",
    )
    parser.add_argument(
        "-d",
        "--database",
        dest="db_path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path ke file database sqlite (default: instance/{DEFAULT_DB_PATH.name})",
    )
    parser.add_argument(
        "--no-record",
        action="store_true",
        help="Jangan rekam pertanyaan dan respons ke database SQLite.",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=float,
        default=float(os.environ.get("THRESHOLD", str(DEFAULT_THRESHOLD))),
        help=f"Ambang kemiripan pencocokan (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Tampilkan rincian aturan, intent, dan skor kemiripan pada balasan.",
    )
    parser.add_argument(
        "-s",
        "--stats",
        action="store_true",
        help="Tampilkan ringkasan statistik dari database lalu keluar.",
    )
    return parser


def main() -> int:
    """Fungsi utama eksekusi CLI."""
    parser = build_parser()
    args = parser.parse_args()

    # Periksa keberadaan knowledge base
    if not args.kb_path.exists():
        print(f"Error: Knowledge base file tidak ditemukan di '{args.kb_path}'", file=sys.stderr)
        return 1

    # Tampilkan statistik jika diminta
    if args.stats:
        display_stats(args.db_path, args.threshold)
        return 0

    # Inisialisasi engine
    try:
        engine = ChatbotEngine.from_file(str(args.kb_path), threshold=args.threshold)
    except Exception as err:
        print(f"Error saat memuat knowledge base: {err}", file=sys.stderr)
        return 1

    # Inisialisasi database jika pencatatan aktif
    db_target = None
    if not args.no_record:
        try:
            initialize_database(str(args.db_path))
            db_target = args.db_path
        except Exception as err:
            print(f"[Peringatan] Inisialisasi database gagal: {err}", file=sys.stderr)

    session_id = f"cli-{uuid.uuid4().hex[:8]}"

    # Prioritaskan query yang diberikan melalui argumen
    single_query = args.flag_query or args.query
    if single_query:
        single_query = single_query.strip()
        if not single_query:
            print("Error: Pertanyaan tidak boleh kosong.", file=sys.stderr)
            return 1
        ask_and_respond(
            engine=engine,
            message=single_query,
            db_path=db_target,
            session_id=session_id,
            verbose=args.verbose,
        )
        return 0

    # Masuk ke mode interaktif
    run_interactive(
        engine=engine,
        db_path=db_target,
        session_id=session_id,
        threshold=args.threshold,
        verbose=args.verbose,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

# db_mysql.py

import mysql.connector
from datetime import date, timedelta

# --------------------- KONEKSI DATABASE --------------------- #

conn = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="",  # Sesuaikan dengan konfigurasi Anda
    database="fp_sbd_library"
)
cursor = conn.cursor(dictionary=True)

# --------------------- USER MANAGEMENT --------------------- #

def generate_user_id(role):
    prefix = "STF" if role == "staff" else "MBR"
    cursor.execute(
        f"SELECT user_id FROM users WHERE user_id LIKE '{prefix}%' ORDER BY user_id DESC LIMIT 1"
    )
    result = cursor.fetchone()
    if result:
        last_id = int(result["user_id"][3:])
        return f"{prefix}{last_id + 1:03d}"
    return f"{prefix}001"

def registrasi_user(name, email, password, role="member"):
    user_id = generate_user_id(role)
    try:
        cursor.execute("""
            INSERT INTO users (user_id, name, email, password, role)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, name, email, password, role))
        conn.commit()
        return True, user_id
    except mysql.connector.IntegrityError:
        return False, None

def login_user(user_id, password):
    cursor.execute("""
        SELECT * FROM users
        WHERE user_id = %s AND password = %s AND is_active = TRUE
    """, (user_id, password))
    return cursor.fetchone()

# --------------------- BUKU MANAGEMENT --------------------- #

def tambah_buku(buku_id, title, author, publisher, year, stock, genre):
    cursor.execute("""
        INSERT INTO buku (buku_id, title, author, publisher, year, stock, total_copies, genre)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (buku_id, title, author, publisher, year, stock, stock, genre))
    conn.commit()

def lihat_buku_dengan_status():
    cursor.execute("""
        SELECT buku_id, title, author, publisher, year, stock, total_copies,
        CASE WHEN stock > 0 THEN '✅ Available' ELSE '❌ Not Available' END AS status
        FROM buku
        ORDER BY title
    """)
    return cursor.fetchall()

def cari_buku(keyword):
    like = f"%{keyword}%"
    cursor.execute("""
        SELECT * FROM buku
        WHERE title LIKE %s OR author LIKE %s OR publisher LIKE %s
    """, (like, like, like))
    return cursor.fetchall()

# --------------------- PEMINJAMAN --------------------- #

def pinjam_buku(user_id, buku_id):
    cursor.execute("SELECT stock FROM buku WHERE buku_id = %s", (buku_id,))
    buku = cursor.fetchone()

    if not buku or buku['stock'] <= 0:
        return False, "Buku tidak tersedia atau tidak ditemukan."

    today = date.today()
    due = today + timedelta(days=7)

    cursor.execute("""
        INSERT INTO peminjaman (user_id, buku_id, pinjam_date, due_date)
        VALUES (%s, %s, %s, %s)
    """, (user_id, buku_id, today, due))

    cursor.execute("UPDATE buku SET stock = stock - 1 WHERE buku_id = %s", (buku_id,))
    conn.commit()
    return True, f"Buku berhasil dipinjam hingga {due}"

def kembalikan_buku(user_id, buku_id):
    cursor.execute("""
        SELECT * FROM peminjaman
        WHERE user_id = %s AND buku_id = %s AND return_date IS NULL
    """, (user_id, buku_id))
    peminjaman = cursor.fetchone()

    if not peminjaman:
        return False, "Tidak ditemukan peminjaman aktif untuk buku ini."

    today = date.today()
    denda = 0
    if today > peminjaman['due_date']:
        hari_telat = (today - peminjaman['due_date']).days
        denda = hari_telat * 20000

    cursor.execute("""
        UPDATE peminjaman
        SET return_date = %s, fine_amount = %s
        WHERE pinjam_id = %s
    """, (today, denda, peminjaman['pinjam_id']))

    cursor.execute("UPDATE buku SET stock = stock + 1 WHERE buku_id = %s", (buku_id,))
    conn.commit()
    return True, f"Buku berhasil dikembalikan. Denda: Rp{denda}"

def perpanjang_peminjaman(user_id, buku_id):
    cursor.execute("""
        SELECT * FROM peminjaman
        WHERE user_id = %s AND buku_id = %s AND return_date IS NULL
    """, (user_id, buku_id))
    pinjam = cursor.fetchone()

    if not pinjam:
        return False, "❌ Tidak ada peminjaman aktif untuk buku ini."
    if pinjam["extended"]:
        return False, "⛔ Buku ini sudah pernah diperpanjang."
    if date.today() > pinjam["due_date"]:
        return False, "⚠️ Sudah melewati batas waktu pengembalian."

    new_due = pinjam["due_date"] + timedelta(days=3)
    cursor.execute("""
        UPDATE peminjaman
        SET due_date = %s, extended = TRUE
        WHERE pinjam_id = %s
    """, (new_due, pinjam["pinjam_id"]))
    conn.commit()
    return True, f"✅ Peminjaman diperpanjang hingga {new_due}"

def riwayat_peminjaman_user(user_id):
    cursor.execute("""
        SELECT p.buku_id, b.title, p.pinjam_date, p.due_date, p.return_date, p.fine_amount,
        CASE WHEN p.return_date IS NOT NULL THEN '✅ Sudah Kembali' ELSE '❌ Belum Kembali' END AS status
        FROM peminjaman p
        JOIN buku b ON p.buku_id = b.buku_id
        WHERE p.user_id = %s
        ORDER BY p.pinjam_date DESC
    """, (user_id,))
    return cursor.fetchall()

def cek_peminjaman_mendekati_jatuh_tempo(user_id):
    cursor.execute("""
        SELECT b.title, p.due_date
        FROM peminjaman p
        JOIN buku b ON p.buku_id = b.buku_id
        WHERE p.user_id = %s
          AND p.return_date IS NULL
          AND DATEDIFF(p.due_date, CURDATE()) BETWEEN 0 AND 3
    """, (user_id,))
    return cursor.fetchall()

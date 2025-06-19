# FP_SBD.py

from tabulate import tabulate
from db_mysql import (
    tambah_buku, registrasi_user, login_user,
    lihat_buku_dengan_status, pinjam_buku, kembalikan_buku,
    cari_buku, riwayat_peminjaman_user, perpanjang_peminjaman,
    cursor, conn, cek_peminjaman_mendekati_jatuh_tempo
)
from db_mongo import (
    simpan_aktivitas, simpan_pencarian, simpan_review,
    tambah_wishlist, proses_notifikasi_tersedia,
    lihat_wishlist_user, hapus_dari_wishlist,
    lihat_rekomendasi, notifikasi_wishlist_user,
    generate_rekomendasi
)

# --------------------- MENU UTAMA --------------------- #

def main():
    while True:
        print("\n=== 📖 SISTEM PERPUSTAKAAN ===")
        print("1. Registrasi")
        print("2. Login")
        print("0. Keluar")
        pilihan = input("Pilih menu: ")
        if pilihan == "1":
            menu_registrasi()
        elif pilihan == "2":
            user = menu_login()
            if user:
                if user['role'] == 'member':
                    peringatan = cek_peminjaman_mendekati_jatuh_tempo(user['user_id'])
                    if peringatan:
                        print("\n🕒 Peringatan: Buku berikut mendekati batas pengembalian:")
                        for item in peringatan:
                            print(f"- {item['title']} (paling lambat: {item['due_date']})")

                    notif = notifikasi_wishlist_user(user['user_id'])
                    if notif:
                        print("\n📢 Notifikasi Wishlist: Buku berikut kini tersedia!")
                        for judul in notif:
                            print(f"  - {judul}")

                    menu_member(user)
                else:
                    menu_staff(user)
        elif pilihan == "0":
            print("👋 Keluar dari sistem. Sampai jumpa!")
            break
        else:
            print("⚠️ Pilihan tidak valid.")

# --------------------- REGISTRASI & LOGIN --------------------- #

def menu_registrasi():
    print("\n=== 📝 REGISTRASI ===")
    name = input("Nama lengkap: ").strip()
    email = input("Email: ").strip()
    password = input("Password: ").strip()
    role = input("Role (member/staff) [default: member]: ").lower().strip() or "member"
    if role not in ['member', 'staff']:
        role = 'member'

    success, user_id = registrasi_user(name, email, password, role)
    if success:
        print(f"✅ Registrasi berhasil! User ID Anda: {user_id}")
        simpan_aktivitas(user_id, "register", {"role": role})
    else:
        print("❌ Gagal registrasi. Email mungkin sudah digunakan.")

def menu_login():
    print("\n=== 🔐 LOGIN ===")
    user_id = input("User ID: ").strip()
    password = input("Password: ").strip()
    user = login_user(user_id, password)
    if user:
        print(f"✅ Login berhasil! Selamat datang, {user['name']} ({user['role']}) | ID: {user['user_id']}")
        simpan_aktivitas(user['user_id'], "login", {"via": "terminal"})
        return user
    else:
        print("❌ Login gagal. User ID atau password salah.")
        return None

# --------------------- MENU MEMBER --------------------- #

def menu_member(user):
    while True:
        print(f"\n=== 📚 MENU MEMBER | {user['name']} ===")
        print("1. Lihat Daftar Buku")
        print("2. Peminjaman / Pengembalian Buku")
        print("3. Wishlist Buku")
        print("4. Cari Buku")
        print("5. Simpan Review Buku")
        print("6. Lihat Rekomendasi Buku")
        print("0. Logout")
        pilihan = input("Pilih: ")

        if pilihan == "1":
            daftar = lihat_buku_dengan_status()
            print(tabulate(daftar, headers="keys", tablefmt="grid") if daftar else "📭 Belum ada data buku.")

        elif pilihan == "2":
            submenu_peminjaman(user)

        elif pilihan == "3":
            submenu_wishlist(user)

        elif pilihan == "4":
            keyword = input("🔍 Cari buku (judul/penulis/penerbit): ").strip()
            hasil = cari_buku(keyword)
            print(tabulate(hasil, headers="keys", tablefmt="grid") if hasil else "📭 Tidak ditemukan.")
            simpan_pencarian(user['user_id'], keyword)

        elif pilihan == "5":
            buku_id = input("ID buku: ")
            rating = float(input("Rating (0-5): "))
            review = input("Review singkat: ")
            simpan_review(user['user_id'], buku_id, rating, review)
            print("✅ Review berhasil disimpan.")

        elif pilihan == "6":
            if input("🔄 Generate rekomendasi baru? (y/n): ").lower() == "y":
                data = generate_rekomendasi(user['user_id'])
            else:
                data = lihat_rekomendasi(user['user_id'])
            print(tabulate(data, headers="keys", tablefmt="grid") if data else "📭 Belum ada rekomendasi.")

        elif pilihan == "0":
            print("👋 Logout berhasil.")
            break
        else:
            print("⚠️ Pilihan tidak valid.")

# --------------------- SUBMENU MEMBER --------------------- #

def submenu_peminjaman(user):
    print("\n📚 Menu Peminjaman / Pengembalian Buku")
    print("1. Pinjam Buku")
    print("2. Kembalikan Buku")
    print("3. Riwayat Peminjaman")
    print("4. Perpanjang Peminjaman")
    sub = input("Pilih opsi: ")
    uid = user['user_id']

    if sub == "1":
        buku_id = input("ID buku yang ingin dipinjam: ")
        success, pesan = pinjam_buku(uid, buku_id)
        print("✅" if success else "❌", pesan)
    elif sub == "2":
        buku_id = input("ID buku yang ingin dikembalikan: ")
        success, pesan = kembalikan_buku(uid, buku_id)
        print("✅" if success else "❌", pesan)
    elif sub == "3":
        riwayat = riwayat_peminjaman_user(uid)
        print(tabulate(riwayat, headers="keys", tablefmt="grid") if riwayat else "📭 Belum ada riwayat.")
    elif sub == "4":
        buku_id = input("Masukkan ID Buku yang ingin diperpanjang: ").strip()
        success, pesan = perpanjang_peminjaman(uid, buku_id)
        print(pesan)
    else:
        print("⚠️ Pilihan tidak valid.")

def submenu_wishlist(user):
    notif = notifikasi_wishlist_user(user['user_id'])
    if notif:
        print("\n📢 Notifikasi Wishlist: Buku berikut kini tersedia!")
        for judul in notif:
            print(f"  - {judul}")

    print("\n🧡 Wishlist Buku")
    print("1. Tambah ke Wishlist")
    print("2. Lihat Wishlist Saya")
    print("3. Hapus Buku dari Wishlist")
    sub = input("Pilih opsi: ")

    if sub == "1":
        buku_id = input("ID buku: ")
        cursor.execute("SELECT title, stock FROM buku WHERE buku_id = %s", (buku_id,))
        data = cursor.fetchone()
        if data:
            success, pesan = tambah_wishlist(user['user_id'], buku_id, data['title'])
            print("✅" if success else "❌", pesan)
            if success and data['stock'] > 0:
                proses_notifikasi_tersedia(buku_id, data['stock'])
        else:
            print("❌ Buku tidak ditemukan.")
    elif sub == "2":
        wishlist = lihat_wishlist_user(user['user_id'])
        print(tabulate(wishlist, headers="keys", tablefmt="grid") if wishlist else "📭 Wishlist kosong.")
    elif sub == "3":
        buku_id = input("ID buku: ")
        success, pesan = hapus_dari_wishlist(user['user_id'], buku_id)
        print("✅" if success else "❌", pesan)
    else:
        print("⚠️ Pilihan tidak valid.")

# --------------------- MENU STAFF --------------------- #

def menu_staff(user):
    while True:
        print(f"\n=== 🛠️ MENU STAFF | {user['name']} ===")
        print("1. Manajemen Buku")
        print("2. Manajemen User")
        print("3. Lihat Daftar Buku")
        print("0. Logout")
        pilihan = input("Pilih: ")

        if pilihan == "1":
            submenu_manajemen_buku()
        elif pilihan == "2":
            submenu_manajemen_user()
        elif pilihan == "3":
            daftar = lihat_buku_dengan_status()
            print(tabulate(daftar, headers="keys", tablefmt="grid") if daftar else "📭 Belum ada data buku.")
        elif pilihan == "0":
            print("👋 Logout berhasil.")
            break
        else:
            print("⚠️ Pilihan tidak valid.")

def submenu_manajemen_buku():
    while True:
        print("\n--- 📚 MANAJEMEN BUKU ---")
        print("1. Tambah Buku")
        print("2. Edit Buku")
        print("3. Hapus Buku")
        print("0. Kembali")
        sub = input("Pilih opsi: ")

        if sub == "1":
            buku_id = input("ID Buku: ")
            title = input("Judul: ")
            author = input("Penulis: ")
            publisher = input("Penerbit: ")
            year = int(input("Tahun: "))
            stock = int(input("Stok: "))
            genre = input("Genre: ")
            tambah_buku(buku_id, title, author, publisher, year, stock, genre)
            print("✅ Buku berhasil ditambahkan.")

        elif sub == "2":
            buku_id = input("ID Buku yang ingin diedit: ")
            cursor.execute("SELECT * FROM buku WHERE buku_id = %s", (buku_id,))
            data = cursor.fetchone()
            if not data:
                print("❌ Buku tidak ditemukan.")
                continue

            new_title = input(f"Judul baru [{data['title']}]: ") or data['title']
            new_author = input(f"Penulis baru [{data['author']}]: ") or data['author']
            new_publisher = input(f"Penerbit baru [{data['publisher']}]: ") or data['publisher']
            new_year = int(input(f"Tahun baru [{data['year']}]: ") or data['year'])
            new_stock = int(input(f"Stok baru [{data['stock']}]: ") or data['stock'])
            new_genre = input(f"Genre baru [{data['genre']}]: ") or data['genre']

            cursor.execute("""
                UPDATE buku SET title=%s, author=%s, publisher=%s, year=%s, stock=%s, genre=%s
                WHERE buku_id = %s
            """, (new_title, new_author, new_publisher, new_year, new_stock, new_genre, buku_id))
            conn.commit()
            print("✅ Data buku berhasil diperbarui.")

        elif sub == "3":
            buku_id = input("ID Buku yang ingin dihapus: ")
            cursor.execute("SELECT * FROM buku WHERE buku_id = %s", (buku_id,))
            if not cursor.fetchone():
                print("❌ Buku tidak ditemukan.")
                continue
            if input("Yakin ingin menghapus buku ini? (y/n): ").lower() == "y":
                cursor.execute("DELETE FROM buku WHERE buku_id = %s", (buku_id,))
                conn.commit()
                print("🗑️ Buku berhasil dihapus.")
            else:
                print("❌ Dibatalkan.")

        elif sub == "0":
            break
        else:
            print("⚠️ Pilihan tidak valid.")

def submenu_manajemen_user():
    while True:
        print("\n--- 👥 MANAJEMEN USER ---")
        print("1. Lihat Daftar Member")
        print("2. Nonaktifkan User")
        print("0. Kembali")
        sub = input("Pilih opsi: ")

        if sub == "1":
            cursor.execute("""
                SELECT user_id, name, email, role, registered_at, is_active
                FROM users WHERE role = 'member'
                ORDER BY registered_at DESC
            """)
            data = cursor.fetchall()
            for d in data:
                d['status'] = "✅ Aktif" if d['is_active'] else "❌ Nonaktif"
            print(tabulate(data, headers="keys", tablefmt="grid") if data else "📭 Tidak ada member.")

        elif sub == "2":
            user_id = input("User ID yang ingin dinonaktifkan: ").strip()
            cursor.execute("SELECT * FROM users WHERE user_id = %s AND role = 'member'", (user_id,))
            user = cursor.fetchone()
            if not user:
                print("❌ User tidak ditemukan atau bukan member.")
                continue
            if input(f"Nonaktifkan {user['name']}? (y/n): ").lower() == "y":
                cursor.execute("UPDATE users SET is_active = FALSE WHERE user_id = %s", (user_id,))
                conn.commit()
                print("✅ User berhasil dinonaktifkan.")
            else:
                print("⏹️ Dibatalkan.")

        elif sub == "0":
            break
        else:
            print("⚠️ Pilihan tidak valid.")

# --------------------- RUN APP --------------------- #

if __name__ == "__main__":
    main()

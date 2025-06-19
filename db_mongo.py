# db_mongo.py

from pymongo import MongoClient
from datetime import datetime
from db_mysql import cursor

# --------------------- KONEKSI MONGODB --------------------- #

client = MongoClient("mongodb://localhost:27017/")
mongo_db = client["FP_SBD_Library"]

# --------------------- LOG AKTIVITAS & PENCARIAN --------------------- #

def simpan_aktivitas(user_id, action, detail):
    mongo_db.activity_log.insert_one({
        "user_id": user_id,
        "action": action,
        "timestamp": datetime.utcnow(),
        "details": detail
    })

def simpan_pencarian(user_id, keyword):
    mongo_db.search_history.insert_one({
        "user_id": user_id,
        "search_keyword": keyword,
        "timestamp": datetime.utcnow()
    })

# --------------------- REVIEW BUKU --------------------- #

def simpan_review(user_id, book_id, rating, review):
    mongo_db.reviews.insert_one({
        "user_id": user_id,
        "book_id": book_id,
        "rating": rating,
        "review": review,
        "timestamp": datetime.utcnow()
    })

# --------------------- WISHLIST & NOTIFIKASI --------------------- #

def tambah_wishlist(user_id, book_id, book_title):
    if mongo_db.wishlist_notifications.find_one({"user_id": user_id, "book_id": book_id}):
        return False, "Buku sudah ada di wishlist Anda."

    mongo_db.wishlist_notifications.insert_one({
        "user_id": user_id,
        "book_id": book_id,
        "book_title": book_title,
        "notified_at": None
    })
    return True, "Buku ditambahkan ke wishlist."

def hapus_dari_wishlist(user_id, book_id):
    result = mongo_db.wishlist_notifications.delete_one({
        "user_id": user_id,
        "book_id": book_id
    })
    if result.deleted_count > 0:
        return True, "Buku berhasil dihapus dari wishlist."
    return False, "Buku tidak ditemukan dalam wishlist Anda."

def lihat_wishlist_user(user_id):
    data = mongo_db.wishlist_notifications.find({"user_id": user_id})
    wishlist = []

    for item in data:
        cursor.execute("SELECT stock FROM buku WHERE buku_id = %s", (item["book_id"],))
        result = cursor.fetchone()
        status = "✅" if result and result["stock"] > 0 else "❌"
        wishlist.append({
            "Book ID": item["book_id"],
            "Title": item["book_title"],
            "Stok Available": status
        })
    return wishlist

def notifikasi_wishlist_user(user_id):
    tersedia = []
    data = mongo_db.wishlist_notifications.find({
        "user_id": user_id,
        "notified_at": None
    })
    for item in data:
        cursor.execute("SELECT stock FROM buku WHERE buku_id = %s", (item["book_id"],))
        result = cursor.fetchone()
        if result and result["stock"] > 0:
            tersedia.append(item["book_title"])
            mongo_db.wishlist_notifications.update_one(
                {"_id": item["_id"]},
                {"$set": {"notified_at": datetime.utcnow()}}
            )
    return tersedia

def proses_notifikasi_tersedia(book_id, stock):
    if stock <= 0:
        return
    wishers = mongo_db.wishlist_notifications.find({
        "book_id": book_id,
        "notified_at": None
    })
    for w in wishers:
        mongo_db.wishlist_notifications.update_one(
            {"_id": w["_id"]},
            {"$set": {"notified_at": datetime.utcnow()}}
        )
        print(f"🔔 Notifikasi: {w['user_id']} diberi tahu bahwa buku '{w['book_title']}' sekarang tersedia.")

# --------------------- REKOMENDASI --------------------- #

def lihat_rekomendasi(user_id):
    data = mongo_db.book_recommendations.find_one(
        {"user_id": user_id},
        sort=[("generated_at", -1)]
    )
    return data["recommended_books"] if data else []

def generate_rekomendasi(user_id):
    from db_mysql import cursor
    from collections import defaultdict

    genres = set()
    rekomendasi_ids = set()
    hasil_akhir = []

    # Ambil genre dari wishlist user (MongoDB → SQL)
    wishlist = mongo_db.wishlist_notifications.find({"user_id": user_id})
    for item in wishlist:
        cursor.execute("SELECT genre FROM buku WHERE buku_id = %s", (item["book_id"],))
        result = cursor.fetchone()
        if result:
            genres.add(result["genre"])

    # Ambil review dari user lain dengan rating > 4
    reviews = mongo_db.reviews.find({
        "user_id": { "$ne": user_id },
        "rating": { "$gt": 4 }
    })

    # Hitung jumlah review positif per buku
    rating_count = defaultdict(int)
    for r in reviews:
        rating_count[r["book_id"]] += 1

    # Ambil top 3 buku yang paling sering direview bagus
    top_books = sorted(rating_count.items(), key=lambda x: -x[1])[:5]

    for book_id, _ in top_books:
        cursor.execute("SELECT buku_id, title, genre FROM buku WHERE buku_id = %s", (book_id,))
        data = cursor.fetchone()
        if data and data["buku_id"] not in rekomendasi_ids:
            # Jika genre cocok dengan wishlist user
            if not genres or data["genre"] in genres:
                hasil_akhir.append({"buku_id": data["buku_id"], "title": data["title"]})
                rekomendasi_ids.add(data["buku_id"])

    # Simpan hasil ke MongoDB
    if hasil_akhir:
        mongo_db.book_recommendations.insert_one({
            "user_id": user_id,
            "generated_at": datetime.utcnow(),
            "recommended_books": hasil_akhir
        })

    return hasil_akhir

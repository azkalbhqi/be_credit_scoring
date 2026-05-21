from typing import Dict, Tuple


def check_hard_rules(data: Dict) -> Tuple[bool, str]:
    """
    Langkah 2:
    Hard Rules / Pre-screening Layer

    Return:
    (is_passed, reason)
    """

    print("=== MENJALANKAN HARD RULES ===")


    bi_check = data.get("kolektibilitas_bi", 1)

    if bi_check in [3, 4, 5]:
        return (
            False,
            "REJECT - Bank Teknis (Kolektibilitas BI buruk)"
        )


    produk = data.get("produk", "KUR").upper()

    dsr = float(data.get("dsr", 0))


    if produk == "KUR":

        lama_usaha = int(data.get("lama_usaha_bulan", 0))

        if lama_usaha < 6:
            return (
                False,
                "REJECT - Lama usaha kurang dari 6 bulan"
            )

        if dsr > 60:
            return (
                False,
                "REJECT - DSR melebihi 60%"
            )


    elif produk == "KTA":

        gaji = float(data.get("gaji", 0))

        if gaji < 3000000:
            return (
                False,
                "REJECT - Gaji kurang dari Rp3.000.000"
            )

        if dsr > 35:
            return (
                False,
                "REJECT - DSR melebihi 35%"
            )

    elif produk == "KOMERSIAL":

        # 1. BI Checking: Wajib Kolektibilitas 1 (Lancar). Kol 2 atau lebih buruk otomatis ditolak.
        if bi_check >= 2:
            return (
                False,
                "REJECT - Kolektibilitas BI tidak lancar (Minimal Kol 1 untuk Kredit Komersial)"
            )

        # 2. Lama Usaha: Minimal 24 bulan
        lama_usaha = int(data.get("lama_usaha_bulan", 0))
        if lama_usaha < 24:
            return (
                False,
                "REJECT - Lama usaha kurang dari 24 bulan (Minimal 2 tahun untuk Kredit Komersial)"
            )

        # 3. DSR: Maksimum DSR 50%
        if dsr > 50:
            return (
                False,
                "REJECT - DSR melebihi 50% untuk Kredit Komersial"
            )

        # 4. Omzet Bulanan (Gaji): Minimal Rp10.000.000
        gaji = float(data.get("gaji", 0))
        if gaji < 10000000:
            return (
                False,
                "REJECT - Omzet bulanan kurang dari Rp10.000.000"
            )

        # 5. Saldo Rata-rata Koran (Balance): Minimal Rp15.000.000
        balance = float(data.get("balance", 0))
        if balance < 15000000:
            return (
                False,
                "REJECT - Saldo rata-rata rekening koran kurang dari Rp15.000.000"
            )

    else:
        return (
            False,
            f"REJECT - Produk tidak dikenali: {produk}"
        )


    return (
        True,
        "PASS - Lolos Hard Rules"
    )
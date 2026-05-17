from typing import Dict, Tuple


def check_hard_rules(data: Dict) -> Tuple[bool, str]:
    """
    Langkah 2:
    Hard Rules / Pre-screening Layer

    Return:
    (is_passed, reason)
    """

    print("=== MENJALANKAN HARD RULES ===")

    # =====================================================
    # 1. BI CHECKING
    # =====================================================

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



    else:
        return (
            False,
            f"REJECT - Produk tidak dikenali: {produk}"
        )


    return (
        True,
        "PASS - Lolos Hard Rules"
    )
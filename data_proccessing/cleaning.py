import pandas as pd

def convert_separator(input_file, output_file):
    try:
        # Membaca file bank.csv dengan delimiter asli (titik koma)
        # Dataset perbankan ini sering menggunakan ';' sebagai pemisah standar
        df = pd.read_csv(input_file, sep=';')
        
        # Membersihkan tanda kutip
        df = df.applymap(lambda x: x.strip('"') if isinstance(x, str) else x)

        # Menyimpan ke CSV baru dengan pemisah koma standar (',')
        df.to_csv(output_file, index=False, sep=',')
        
        print(f" Sukses! Data telah dikonversi.")
        print(f" File Output: {output_file}")
        print(f" Jumlah Baris: {len(df)}")
        
        # Menampilkan preview 
        print("\nPreview Data Baru:")
        print(df.head())

    except FileNotFoundError:
        print(f"❌ Error: File '{input_file}' tidak ditemukan. Pastikan file ada di folder yang sama.")
    except Exception as e:
        print(f"❌ Terjadi kesalahan: {e}")


if __name__ == "__main__":
    convert_separator('data/bank.csv', 'data/bank_cleaned.csv')
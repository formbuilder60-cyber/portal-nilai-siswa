import streamlit as st
import sqlite3
import bcrypt
import pandas as pd

st.set_page_config(page_title="Sistem Informasi Nilai Siswa", page_icon="🎓")

# --- FUNGSI DATABASE ---
def cek_login(username, password):
    # Fitur bypass untuk Admin Utama
    if username == "admin" and password == "admin123":
        return {"username": "admin", "nama": "Administrator Utama"}
        
    conn = sqlite3.connect('sekolah.db')
    cursor = conn.cursor()
    cursor.execute("SELECT username, nama_lengkap, password FROM siswa WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        db_username, nama_lengkap, db_password = user
        if bcrypt.checkpw(password.encode('utf-8'), db_password.encode('utf-8')):
            return {"username": db_username, "nama": nama_lengkap}
    return None

def ambil_nilai_siswa(username):
    conn = sqlite3.connect('sekolah.db')
    cursor = conn.cursor()
    cursor.execute("SELECT nilai_matematika, nilai_indonesia, nilai_ipa FROM siswa WHERE username = ?", (username,))
    nilai = cursor.fetchone()
    conn.close()
    return nilai

def masukkan_data_excel(file_excel):
    # Membaca file excel menggunakan pandas
    df = pd.read_excel(file_excel)
    
    conn = sqlite3.connect('sekolah.db')
    cursor = conn.cursor()
    
    sukses_input = 0
    error_input = 0
    
    for index, row in df.iterrows():
        # Mengubah password text biasa dari Excel menjadi hash aman
        password_hash = bcrypt.hashpw(str(row['password']).encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        try:
            # Gunakan INSERT OR REPLACE agar jika username sudah ada, datanya diperbarui (update)
            cursor.execute('''
                INSERT OR REPLACE INTO siswa (username, nama_lengkap, password, nilai_matematika, nilai_indonesia, nilai_ipa)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (row['username'], row['nama_lengkap'], password_hash, row['nilai_matematika'], row['nilai_indonesia'], row['nilai_ipa']))
            sukses_input += 1
        except Exception as e:
            error_input += 1
            
    conn.commit()
    conn.close()
    return sukses_input, error_input

# --- LOGIKA TAMPILAN WEB ---
st.title("🎓 Portal Hasil Ujian Siswa")

if 'login_status' not in st.session_state:
    st.session_state['login_status'] = False
    st.session_state['user_info'] = None

# 1. JIKA BELUM LOGIN
if not st.session_state['login_status']:
    st.write("Silakan login untuk melihat nilai Anda (Siswa) atau mengunggah data (Admin).")
    with st.form("form_login"):
        username_input = st.text_input("Username")
        password_input = st.text_input("Password", type="password")
        tombol_login = st.form_submit_button("Masuk")
        
        if tombol_login:
            user_tervalidasi = cek_login(username_input, password_input)
            if user_tervalidasi:
                st.session_state['login_status'] = True
                st.session_state['user_info'] = user_tervalidasi
                st.rerun()
            else:
                st.error("Username atau Password salah!")

# 2. JIKA SUDAH LOGIN
else:
    user = st.session_state['user_info']
    
    # KONDISI A: LOGIN SEBAGAI ADMIN (TEMPAT INPUT DATA RIIL)
    if user['username'] == 'admin':
        st.success(f"Masuk sebagai: **{user['nama']}**")
        st.subheader("📥 Unggah Data Riil Siswa via Excel")
        st.info("Pastikan format file Excel Anda memiliki kolom: username, nama_lengkap, password, nilai_matematika, nilai_indonesia, nilai_ipa")
        
        # Komponen untuk upload file
        uploaded_file = st.file_uploader("Pilih file Excel (.xlsx)", type=["xlsx"])
        
        if uploaded_file is not None:
            if st.button("Proses dan Masukkan ke Database"):
                with st.spinner("Sedang memproses data..."):
                    sukses, gagal = masukkan_data_excel(uploaded_file)
                if sukses > 0:
                    st.success(f"Berhasil memasukkan/memperbarui {sukses} data siswa!")
                if gagal > 0:
                    st.error(f"Gagal memasukkan {gagal} data siswa. Periksa format kolom Anda.")
                    
    # KONDISI B: LOGIN SEBAGAI SISWA
    else:
        st.success(f"Selamat Datang, **{user['nama']}**!")
        st.subheader("📊 Hasil Ujian Anda")
        
        data_nilai = ambil_nilai_siswa(user['username'])
        if data_nilai:
            nilai_mtk, nilai_indo, nilai_ipa = data_nilai
            kolom1, kolom2, kolom3 = st.columns(3)
            with kolom1: st.metric(label="Matematika", value=nilai_mtk)
            with kolom2: st.metric(label="Bahasa Indonesia", value=nilai_indo)
            with kolom3: st.metric(label="IPA", value=nilai_ipa)
            
            rata_rata = (nilai_mtk + nilai_indo + nilai_ipa) / 3
            st.info(f"Rata-rata Nilai Anda: **{rata_rata:.2f}**")
        else:
            st.warning("Data nilai Anda belum dimasukkan oleh Admin.")

    # Tombol Logout untuk semua user
    if st.button("Keluar dari Sistem"):
        st.session_state['login_status'] = False
        st.session_state['user_info'] = None
        st.rerun()
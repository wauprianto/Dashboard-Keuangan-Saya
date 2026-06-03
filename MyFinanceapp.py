import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import random
from statsmodels.tsa.arima.model import ARIMA
from sklearn.ensemble import IsolationForest
import google.generativeai as genai
import warnings

warnings.filterwarnings('ignore')

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Smart Finance", page_icon="💰", layout="wide", initial_sidebar_state="expanded")

# --- FITUR KEAMANAN (LOGIN) ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<br><br><h2 style='text-align: center; color: #00ffcc;'>🔒 Akses Dasbor Keuangan</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            password_input = st.text_input("Masukkan PIN / Password:", type="password")
            if st.button("Masuk", use_container_width=True):
                try:
                    kunci_rahasia = st.secrets["APP_PASSWORD"]
                    if password_input == str(kunci_rahasia): 
                        st.session_state['logged_in'] = True
                        st.rerun()
                    else:
                        st.error("❌ Password salah!")
                except KeyError:
                    st.error("⚠️ Sistem terkunci: 'APP_PASSWORD' belum diatur di Streamlit Secrets!")
    st.stop() 

if st.sidebar.button("🚪 Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

# -- CUSTOM CSS & FLOATING CHAT BUBBLE CSS DI KANAN ATAS ---
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, #1e1e2e, #2b2b40);
        border-left: 5px solid #00ffcc;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0, 255, 204, 0.2);
    }
    div[data-testid="stForm"] {
        background-color: rgba(30, 30, 46, 0.5);
        border: 1px solid #45475a;
        border-radius: 15px;
        padding: 25px;
    }
    h1, h2, h3 {
        font-family: 'Trebuchet MS', sans-serif;
        color: #89b4fa !important;
    }
    .block-container {
        padding-top: 2rem;
    }
    /* CSS UNTUK TOMBOL BOLA MELAYANG (AI CHAT) DI POJOK KANAN ATAS */
    div[data-testid="stPopover"]:last-of-type > button {
        position: fixed !important;
        top: 70px !important; /* Posisi di atas */
        right: 25px !important;
        width: 65px !important;
        height: 65px !important;
        border-radius: 50% !important;
        background: linear-gradient(135deg, #89b4fa, #00ffcc) !important;
        color: white !important;
        font-size: 30px !important;
        z-index: 99999 !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.6) !important;
        padding: 0 !important;
        border: none !important;
        transition: transform 0.3s !important;
    }
    div[data-testid="stPopover"]:last-of-type > button:hover {
        transform: scale(1.1) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- INISIALISASI DATA ---
DATA_FILE = 'data_keuangan.csv'

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        return df
    else:
        return pd.DataFrame(columns=['Tanggal', 'Tipe', 'Kategori', 'Jumlah', 'Keterangan'])

def save_data(df):
    df.to_csv(DATA_FILE, index=False)

df = load_data()

# --- FITUR 1: SMART CATEGORIZATION (NLP) ---
def tebak_kategori(keterangan, tipe):
    teks = keterangan.lower()
    if tipe == "Pengeluaran":
        if any(kata in teks for kata in ['makan', 'minum', 'nasi', 'kopi', 'warteg', 'snack', 'roti', 'kue', 'gojek food', 'grab food']):
            return "Makan/Minum"
        if any(kata in teks for kata in ['kereta', 'krl', 'gojek', 'grab', 'bensin', 'parkir', 'tol', 'tiket']):
            return "Transportasi"
        if any(kata in teks for kata in ['listrik', 'pln', 'air', 'pdam', 'wifi', 'internet', 'kuota', 'pulsa', 'bpjs']):
            return "Tagihan"
        if any(kata in teks for kata in ['game', 'anime', 'bioskop', 'netflix', 'spotify', 'nonton', 'steam']):
            return "Hiburan"
        if any(kata in teks for kata in ['baju', 'sepatu', 'shopee', 'tokopedia', 'minimarket', 'indomaret', 'alfamart', 'belanja']):
            return "Belanja"
    else:
        if any(kata in teks for kata in ['gaji', 'upah', 'salary']):
            return "Gaji"
        if any(kata in teks for kata in ['bonus', 'thr', 'hadiah']):
            return "Bonus"
        if any(kata in teks for kata in ['saham', 'kripto', 'reksa dana', 'bunga']):
            return "Investasi"
    return "Lain-lain"

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown("<h2 style='text-align: center; color: #00ffcc !important;'>💠 Smart Finance</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Navigasi Dashboard:",
    ["🏠 Dashboard", "📈 Analyze", "🔮 AI Predict"]
)
st.sidebar.markdown("---")
st.sidebar.caption("© 2026 | Financial Dashboard & Analytics")
st.sidebar.caption("Prianto Sanema Wau")

# ==========================================
# MENU 1: BERANDA & INPUT
# ==========================================
if menu == "🏠 Dashboard":
    st.title("Ringkasan Hari Ini & Input Transaksi")
    
    # KOMPUTASI METRIK (FILTER HARIAN)
    waktu_sekarang = pd.Timestamp.now().normalize()
    df['Tanggal_Clean'] = pd.to_datetime(df['Tanggal']).dt.normalize()
    df_harian = df[df['Tanggal_Clean'] == waktu_sekarang]
    
    pemasukan_harian = df_harian[df_harian['Tipe'] == 'Pemasukan']['Jumlah'].sum()
    pengeluaran_harian = df_harian[df_harian['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
    saldo_akhir = df[df['Tipe'] == 'Pemasukan']['Jumlah'].sum() - df[df['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
    
    # FITUR 2: AI ANOMALY DETECTION (ISOLATION FOREST)
    df_pengeluaran_all = df[df['Tipe'] == 'Pengeluaran']
    if len(df_pengeluaran_all) > 10 and pengeluaran_harian > 0: 
        pengeluaran_hist = df_pengeluaran_all.groupby(df_pengeluaran_all['Tanggal_Clean'].dt.date)['Jumlah'].sum().reset_index()
        X = pengeluaran_hist[['Jumlah']].values
        
        model_iso = IsolationForest(contamination=0.05, random_state=42)
        model_iso.fit(X)
        prediksi_anomali = model_iso.predict([[pengeluaran_harian]])
        
        if prediksi_anomali[0] == -1: 
            st.error(f"🚨 **AI Alert (Isolation Forest):** Mendeteksi lonjakan pengeluaran **TIDAK WAJAR** hari ini (Rp {pengeluaran_harian:,.0f}). Pola ini menyimpang dari kebiasaan Anda!")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Pemasukan Hari Ini", f"Rp {pemasukan_harian:,.0f}")
    col2.metric("🔴 Pengeluaran Hari Ini", f"Rp {pengeluaran_harian:,.0f}")
    col3.metric("💎 Saldo Akhir (Aktual)", f"Rp {saldo_akhir:,.0f}")
    st.markdown("---")
    
    # POP-UP KALKULATOR
    with st.popover("🧮 Buka Kalkulator Finansial", use_container_width=True):
        st.markdown("<h3 style='text-align: center;'>Simulasi Anggaran & Tabungan</h3>", unsafe_allow_html=True)
        col_target, col_budget = st.columns(2)
        with col_target:
            st.subheader("🎯 Kalkulator Target")
            with st.form("form_kalkulator_target", border=True):
                nama_target = st.text_input("Nama Target", "Laptop Baru / Liburan")
                nominal_target = st.number_input("Nominal Target (Rp)", min_value=0, value=10000000, step=500000)
                jangka_waktu = st.number_input("Berapa Bulan?", min_value=1, value=6)
                if st.form_submit_button("Hitung Target", use_container_width=True):
                    if nominal_target > 0:
                        st.success(f"Anda perlu menyisihkan **Rp {nominal_target/jangka_waktu:,.0f} / bulan**.")
                        persentase = min(saldo_akhir / nominal_target, 1.0)
                        if saldo_akhir >= nominal_target:
                            st.info(f"🎉 Selamat! Saldo saat ini sudah cukup untuk **{nama_target}**!")
                        else:
                            st.progress(max(0.0, persentase))
                            st.caption(f"Terkumpul saat ini: **Rp {saldo_akhir:,.0f}** dari Rp {nominal_target:,.0f}")
        with col_budget:
            st.subheader("📊 Anggaran 50/30/20")
            with st.form("form_kalkulator_anggaran", border=True):
                gaji = st.number_input("Estimasi Pendapatan Bulan Ini (Rp)", min_value=0, value=5000000, step=100000)
                if st.form_submit_button("Hitung Anggaran", use_container_width=True):
                    if gaji > 0:
                        st.success("✅ Rincian alokasi ideal Anda:")
                        st.markdown(f"**Pokok (50%):** Rp {gaji*0.5:,.0f} | **Hobi (30%):** Rp {gaji*0.3:,.0f} | **Tabungan (20%):** Rp {gaji*0.2:,.0f}")

    st.markdown("<br>", unsafe_allow_html=True)
    col_form, col_tabel = st.columns([1, 1.2])

    # INPUT TRANSAKSI (DENGAN SMART CATEGORIZATION)
    with col_form:
        st.subheader("📝 Catat Transaksi")
        if 'form_key' not in st.session_state:
            st.session_state.form_key = 0
            
        tanggal = st.date_input("Tanggal Transaksi", datetime.today())
        tipe = st.radio("Jenis", ["Pemasukan", "Pengeluaran"], horizontal=True)
        
        keterangan = st.text_input("Keterangan", placeholder="Cth: Beli Kopi Kenangan", key=f"ket_{st.session_state.form_key}")
        prediksi_kat = tebak_kategori(keterangan, tipe) if keterangan else "Lain-lain"
        
        if tipe == "Pemasukan":
            list_kat = ["Gaji", "Bonus", "Investasi", "Lain-lain"]
            idx = list_kat.index(prediksi_kat) if prediksi_kat in list_kat else 3
            kategori = st.selectbox("Kategori", list_kat, index=idx)
        else:
            list_kat = ["Makan/Minum", "Transportasi", "Tagihan", "Belanja", "Hiburan", "Lain-lain"]
            idx = list_kat.index(prediksi_kat) if prediksi_kat in list_kat else 5
            kategori = st.selectbox("Kategori", list_kat, index=idx)
            
        if keterangan and prediksi_kat != "Lain-lain":
            st.caption(f"✨ *AI Auto-Select: Kategori terdeteksi sebagai {prediksi_kat}*")
            
        jumlah = st.number_input("Jumlah (Rp)", min_value=0, step=5000, key=f"jumlah_{st.session_state.form_key}")
        
        if st.button("💾 Simpan Data", use_container_width=True):
            if jumlah > 0:
                data_baru = pd.DataFrame({'Tanggal': [pd.to_datetime(tanggal)],'Tipe': [tipe],'Kategori': [kategori],'Jumlah': [jumlah],'Keterangan': [keterangan]})
                df = pd.concat([df, data_baru], ignore_index=True)
                save_data(df)
                st.session_state.form_key += 1
                st.success("✅ Tersimpan!")
                st.rerun() 
            else:
                st.error("⚠️ Jumlah tidak boleh nol.")

    # TABEL DENGAN FILTER DINAMIS
    with col_tabel:
        st.subheader("📋 Riwayat Transaksi")
        if not df.empty:
            pilihan_tipe = st.multiselect("Filter Jenis:", options=["Pemasukan", "Pengeluaran"], default=["Pemasukan", "Pengeluaran"])
            df_tampil = df[df['Tipe'].isin(pilihan_tipe)].sort_values(by='Tanggal', ascending=False)
            def color_jumlah(row):
                return ['color: #00ffcc'] * len(row) if row['Tipe'] == 'Pemasukan' else ['color: #ff4d4d'] * len(row)
            st.dataframe(
                df_tampil[['Tanggal', 'Tipe', 'Kategori', 'Jumlah', 'Keterangan']].style.apply(color_jumlah, axis=1).format({"Tanggal": lambda x: x.strftime("%Y-%m-%d"), "Jumlah": "Rp {:,.0f}"}), 
                use_container_width=True, height=295, hide_index=True
            )
        else:
            st.markdown("<div style='text-align: center; color: gray;'>Belum ada riwayat transaksi.</div>", unsafe_allow_html=True)

# ==========================================
# MENU 2: ANALISIS BULANAN 
# ==========================================
elif menu == "📈 Analyze":
    st.title("Visualisasi & Analisis Bulanan")
    if df.empty:
        st.warning("Belum ada data untuk dianalisis.")
    else:
        df['Bulan_Tahun'] = df['Tanggal'].dt.to_period('M')
        list_bulan_str = [str(b) for b in sorted(df['Bulan_Tahun'].unique(), reverse=True)]
        
        col_opt1, col_opt2 = st.columns([1, 3])
        with col_opt1:
            bulan_pilihan = st.selectbox("Pilih Periode", list_bulan_str)
        df_bulanan = df[df['Bulan_Tahun'] == bulan_pilihan]
        
        with col_opt2:
            st.markdown("<br>", unsafe_allow_html=True)
            csv = df_bulanan.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Laporan (CSV)", data=csv, file_name=f"Laporan_{bulan_pilihan}.csv", mime="text/csv")
            
        st.markdown("---")
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.subheader("Arus Kas Harian")
            df_tren = df_bulanan.groupby(['Tanggal', 'Tipe'])['Jumlah'].sum().reset_index()
            df_tren['Tanggal'] = df_tren['Tanggal'].dt.strftime('%Y-%m-%d')
            fig_bar = px.bar(df_tren, x='Tanggal', y='Jumlah', color='Tipe', barmode='group', color_discrete_map={"Pemasukan": "#00ffcc", "Pengeluaran": "#ff4d4d"}, template="plotly_dark")
            fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_c2:
            st.subheader("Distribusi Pengeluaran")
            df_pengeluaran = df_bulanan[df_bulanan['Tipe'] == 'Pengeluaran']
            if not df_pengeluaran.empty:
                fig_pie = px.pie(df_pengeluaran, values='Jumlah', names='Kategori', hole=0.5, template="plotly_dark", color_discrete_sequence=px.colors.sequential.Tealgrn)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# MENU 3: AI PREDIKSI (ARIMA ADVANCED)
# ==========================================
elif menu == "🔮 AI Predict":
    st.title("Proyeksi Pengeluaran (ARIMA with Confidence Interval)")
    df_pengeluaran_all = df[df['Tipe'] == 'Pengeluaran'].copy()
    
    if len(df_pengeluaran_all['Tanggal'].unique()) < 7:
        st.warning("⚠️ Masukkan data pengeluaran minimal 7 hari (beda tanggal) agar AI dapat membaca pola.")
    else:
        df_ts = df_pengeluaran_all.groupby('Tanggal')['Jumlah'].sum().reset_index()
        df_ts = df_ts.set_index('Tanggal').asfreq('D', fill_value=0)
        
        try:
            model = ARIMA(df_ts['Jumlah'], order=(1, 1, 1))
            model_fit = model.fit()
            langkah_prediksi = st.slider("Horizon Prediksi (Hari ke depan):", 3, 30, 7)
            
            prediksi_obj = model_fit.get_forecast(steps=langkah_prediksi)
            forecast_mean = prediksi_obj.predicted_mean.apply(lambda x: max(0, x))
            conf_int = prediksi_obj.conf_int()
            lower_bound = conf_int.iloc[:, 0].apply(lambda x: max(0, x))
            upper_bound = conf_int.iloc[:, 1].apply(lambda x: max(0, x))
            
            tanggal_forecast = pd.date_range(start=df_ts.index[-1] + pd.Timedelta(days=1), periods=langkah_prediksi)
            
            fig_forecast = go.Figure()
            hist_plot = df_ts.tail(21)
            
            fig_forecast.add_trace(go.Scatter(x=hist_plot.index, y=hist_plot['Jumlah'], mode='lines+markers', name='Data Aktual', line=dict(color='#89b4fa', width=3)))
            fig_forecast.add_trace(go.Scatter(x=tanggal_forecast, y=upper_bound, mode='lines', line=dict(width=0), showlegend=False))
            fig_forecast.add_trace(go.Scatter(x=tanggal_forecast, y=lower_bound, mode='lines', fill='tonexty', fillcolor='rgba(243, 139, 168, 0.2)', line=dict(width=0), name='95% Confidence Interval'))
            fig_forecast.add_trace(go.Scatter(x=tanggal_forecast, y=forecast_mean, mode='lines+markers', name='Proyeksi Rata-rata', line=dict(color='#f38ba8', dash='dot', width=3)))
            
            fig_forecast.update_layout(template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", hovermode="x unified")
            st.plotly_chart(fig_forecast, use_container_width=True)
            
        except Exception as e:
            st.error(f"Gagal melakukan kalkulasi AI: {e}")

# ==========================================
# FITUR 3: AI ADVISOR (FLOATING CHAT INTERAKTIF DI ATAS)
# ==========================================
with st.popover("💬", use_container_width=False):
    st.markdown("<h4 style='text-align: center;'>AI Financial Advisor</h4>", unsafe_allow_html=True)
    st.caption("Tanya soal keuangan, coding, atau sapa saja!")

    # 1. Inisialisasi memori riwayat chat
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [
            {"role": "assistant", "content": "Halo Prianto! Saya AI Advisor kamu. Mau ngobrolin apa hari ini? Kalau mau cek dompet juga boleh."}
        ]

    # 2. Area khusus bergulir (scrolling) untuk menampilkan chat
    chat_container = st.container(height=300)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # 3. Form input pesan di bagian bawah
    with st.form("chat_form", clear_on_submit=True):
        cols = st.columns([4, 1])
        with cols[0]:
            user_msg = st.text_input("Pesan:", label_visibility="collapsed", placeholder="Tanya sesuatu...")
        with cols[1]:
            submit_chat = st.form_submit_button("Kirim")

    # 4. Logika saat tombol Kirim ditekan
    if submit_chat and user_msg:
        # Simpan pesan pengguna ke dalam memori layar
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        
        try:
            # Setup koneksi AI
            api_key = st.secrets["Gemini_API_Key"]
            genai.configure(api_key=api_key)
            model_ai = genai.GenerativeModel('gemini-3.1-flash-lite')
            
            # Hitung data riil bulan ini untuk disuapkan ke otak AI
            bulan_ini = pd.Timestamp.now().to_period('M')
            df['Bulan_Tahun'] = df['Tanggal'].dt.to_period('M')
            df_bulan_ini = df[df['Bulan_Tahun'] == bulan_ini]
            
            in_bln = df_bulan_ini[df_bulan_ini['Tipe'] == 'Pemasukan']['Jumlah'].sum()
            out_bln = df_bulan_ini[df_bulan_ini['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
            sisa_bln = in_bln - out_bln
            
            # Format history percakapan sebelumnya agar AI ingat konteks obrolan
            formatted_history = []
            for chat in st.session_state.chat_history[:-1]: # Abaikan pesan terakhir
                role = "model" if chat["role"] == "assistant" else "user"
                formatted_history.append({"role": role, "parts": [chat["content"]]})
                
            # Mulai sesi obrolan terstruktur dengan API
            chat_session = model_ai.start_chat(history=formatted_history)
            
            # --- INSTRUKSI KEPRIBADIAN AI ---
            instruksi_sistem = f"""[INSTRUKSI SISTEM: Kamu adalah asisten AI finansial dan teman ngobrol yang asik. Pengguna aplikasi ini bernama Prian (mahasiswa Statistika, suka Python/SQL/R, hobi lari, main game, nonton anime, dan sering naik kereta untuk bekerja di warehouse).
            Aturan ketat untuk merespons:
            1. Jika Prian hanya menyapa (misal: "Halo", "Test", "Pagi"), balas santai dan hangat. JANGAN tampilkan data keuangan!
            2. Kamu bisa diajak ngobrol topik apa saja (coding, statistik, anime, game, rutinitas kereta, dll).
            3. HANYA JIKA ditanya spesifik tentang keuangannya (misal: "Sisa uangku?", "Analisis dompetku", "Bulan ini boros ga?"), barulah gunakan data ini untuk menganalisis:
               - Pemasukan Bulan Ini: Rp {in_bln:,.0f}
               - Pengeluaran Bulan Ini: Rp {out_bln:,.0f}
               - Sisa Saldo: Rp {sisa_bln:,.0f}
            ]
            
            Pesan Prian: {user_msg}"""
            
            # Kirim pertanyaan dan instruksi, lalu simpan balasan AI
            response = chat_session.send_message(instruksi_sistem)
            st.session_state.chat_history.append({"role": "assistant", "content": response.text})
            
            # Refresh otomatis agar chat terbaru langsung muncul
            st.rerun()
            
        except KeyError:
            st.error("⚠️ API Key Gemini belum diatur di Streamlit Secrets!")
        except Exception as e:
            st.error(f"Gagal memuat AI: {e}")

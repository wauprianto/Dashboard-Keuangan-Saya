import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import tempfile
import requests
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
import google.generativeai as genai
import warnings

# Coba import FPDF untuk cetak Laporan, jika belum ada, beri peringatan
try:
    from fpdf import FPDF
    PDF_READY = True
except ImportError:
    PDF_READY = False

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

# -- CUSTOM CSS (ADAPTIVE UNTUK LIGHT/DARK MODE) ---
st.markdown("""
<style>
    /* Menggunakan variabel tema Streamlit agar warna adaptif di Light/Dark mode */
    div[data-testid="metric-container"] {
        background-color: var(--secondary-background-color);
        border-left: 5px solid #00ffcc;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 12px rgba(0, 255, 204, 0.2);
    }
    div[data-testid="stForm"] {
        background-color: var(--secondary-background-color);
        border: 1px solid var(--border-color);
        border-radius: 15px;
        padding: 25px;
    }
    .block-container {
        padding-top: 2rem;
    }
    /* Bola Melayang AI */
    div[data-testid="stPopover"]:last-of-type > button {
        position: fixed !important;
        top: 70px !important;
        right: 25px !important;
        width: 65px !important;
        height: 65px !important;
        border-radius: 50% !important;
        background: linear-gradient(135deg, #89b4fa, #00ffcc) !important;
        color: white !important;
        font-size: 30px !important;
        z-index: 99999 !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4) !important;
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
menu = st.sidebar.radio("Navigasi Dashboard:", ["🏠 Dashboard", "📈 Analyze", "🔮 AI Predict & Stats"])
st.sidebar.markdown("---")

# FITUR KOREKSI: TOMBOL LIVE API (MENGGUNAKAN NATIVE STREAMLIT BUTTON AGAR PASTI BISA DIKLIK)
st.sidebar.caption("🌍 Live Global Market")
st.sidebar.link_button("📈 Buka Market Binance (BTC)", "https://www.binance.com/en/trade/BTC_USDT", use_container_width=True)

try:
    btc_res = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=3)
    if btc_res.status_code == 200:
        btc_price = float(btc_res.json()['price'])
        st.sidebar.info(f"**Harga Live:** ${btc_price:,.2f}")
except:
    st.sidebar.caption("Gagal memuat harga live saat ini.")

st.sidebar.markdown("---")
st.sidebar.caption("© 2026 | Analytics Dashboard")
st.sidebar.caption("Prianto Sanema Wau")

# ==========================================
# MENU 1: BERANDA & INPUT
# ==========================================
if menu == "🏠 Dashboard":
    st.title("Ringkasan Hari Ini & Input Transaksi")
    
    waktu_sekarang = pd.Timestamp.now().normalize()
    kemarin = waktu_sekarang - pd.Timedelta(days=1)
    df['Tanggal_Clean'] = pd.to_datetime(df['Tanggal']).dt.normalize()
    
    df_harian = df[df['Tanggal_Clean'] == waktu_sekarang]
    df_kemarin = df[df['Tanggal_Clean'] == kemarin]
    
    in_hari_ini = df_harian[df_harian['Tipe'] == 'Pemasukan']['Jumlah'].sum()
    in_kemarin = df_kemarin[df_kemarin['Tipe'] == 'Pemasukan']['Jumlah'].sum()
    out_hari_ini = df_harian[df_harian['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
    out_kemarin = df_kemarin[df_kemarin['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
    saldo_akhir = df[df['Tipe'] == 'Pemasukan']['Jumlah'].sum() - df[df['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
    
    # Delta (Selisih dengan hari sebelumnya)
    delta_in = int(in_hari_ini - in_kemarin)
    delta_out = int(out_hari_ini - out_kemarin)
    
    # Jika tidak ada transaksi kemarin, delta tidak usah ditampilkan agar tidak membingungkan
    d_in_str = f"{delta_in:,.0f} vs kemarin" if in_kemarin > 0 or in_hari_ini > 0 else None
    d_out_str = f"{delta_out:,.0f} vs kemarin" if out_kemarin > 0 or out_hari_ini > 0 else None

    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Pemasukan Hari Ini", f"Rp {in_hari_ini:,.0f}", delta=d_in_str)
    col2.metric("🔴 Pengeluaran Hari Ini", f"Rp {out_hari_ini:,.0f}", delta=d_out_str, delta_color="inverse")
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
    
    col_gauge, col_form, col_tabel = st.columns([1, 1, 1.5]) 
    
    with col_gauge:
        st.subheader("🏎️ Burn Rate")
        batas_aman = 150000 
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = out_hari_ini,
            title = {'text': "Pengeluaran Hari Ini", 'font': {'size': 14}},
            domain = {'x': [0, 1], 'y': [0, 1]},
            gauge = {
                'axis': {'range': [None, batas_aman * 2]},
                'bar': {'color': "#00ffcc"},
                'steps' : [
                    {'range': [0, batas_aman], 'color': "rgba(166, 227, 161, 0.4)"},
                    {'range': [batas_aman, batas_aman*2], 'color': "rgba(243, 139, 168, 0.4)"}],
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': batas_aman}
            }
        ))
        fig_gauge.update_layout(height=250, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig_gauge, use_container_width=True, theme="streamlit")
        st.caption(f"*Batas harian: Rp {batas_aman:,.0f}*")

    with col_form:
        st.subheader("📝 Catat Transaksi")
        if 'form_key' not in st.session_state: st.session_state.form_key = 0
            
        tanggal = st.date_input("Tanggal Transaksi", datetime.today())
        tipe = st.radio("Jenis", ["Pemasukan", "Pengeluaran"], horizontal=True)
        
        keterangan = st.text_input("Keterangan", placeholder="Cth: Beli Kopi Kenangan", key=f"ket_{st.session_state.form_key}")
        prediksi_kat = tebak_kategori(keterangan, tipe) if keterangan else "Lain-lain"
        
        list_kat = ["Gaji", "Bonus", "Investasi", "Lain-lain"] if tipe == "Pemasukan" else ["Makan/Minum", "Transportasi", "Tagihan", "Belanja", "Hiburan", "Lain-lain"]
        idx = list_kat.index(prediksi_kat) if prediksi_kat in list_kat else (len(list_kat)-1)
        kategori = st.selectbox("Kategori", list_kat, index=idx)
            
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

    # TABEL RIWAYAT TRANSAKSI 
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
        
        col_opt1, col_opt2, col_opt3 = st.columns([1, 1.5, 1.5])
        with col_opt1:
            bulan_pilihan = st.selectbox("Pilih Periode", list_bulan_str)
        df_bulanan = df[df['Bulan_Tahun'] == bulan_pilihan]
        
        # HITUNGAN UNTUK PDF DAN GRAFIK
        in_bln = df_bulanan[df_bulanan['Tipe'] == 'Pemasukan']['Jumlah'].sum()
        out_bln = df_bulanan[df_bulanan['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
        sisa_saldo = in_bln - out_bln
        
        with col_opt2:
            st.markdown("<br>", unsafe_allow_html=True)
            csv = df_bulanan.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Data (CSV)", data=csv, file_name=f"Data_{bulan_pilihan}.csv", mime="text/csv", use_container_width=True)
            
        # TOMBOL EXPORT PDF
        with col_opt3:
            st.markdown("<br>", unsafe_allow_html=True)
            if PDF_READY:
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(200, 10, txt=f"Laporan Arus Kas - {bulan_pilihan}", ln=True, align='C')
                pdf.set_font("Arial", size=12)
                pdf.ln(10)
                pdf.cell(200, 8, txt=f"Total Pemasukan: Rp {in_bln:,.0f}", ln=True)
                pdf.cell(200, 8, txt=f"Total Pengeluaran: Rp {out_bln:,.0f}", ln=True)
                pdf.cell(200, 8, txt=f"Sisa Saldo: Rp {sisa_saldo:,.0f}", ln=True)
                pdf.ln(10)
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(200, 8, txt="Rincian Pengeluaran:", ln=True)
                pdf.set_font("Arial", size=12)
                
                df_keluar_pdf = df_bulanan[df_bulanan['Tipe'] == 'Pengeluaran'].groupby('Kategori')['Jumlah'].sum().reset_index()
                for index, row in df_keluar_pdf.iterrows():
                    pdf.cell(200, 8, txt=f"- {row['Kategori']}: Rp {row['Jumlah']:,.0f}", ln=True)
                
                tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                pdf.output(tmp_file.name)
                with open(tmp_file.name, "rb") as f:
                    pdf_bytes = f.read()
                
                st.download_button("📄 Ekspor Laporan (PDF)", data=pdf_bytes, file_name=f"Laporan_{bulan_pilihan}.pdf", mime="application/pdf", use_container_width=True)
            else:
                st.error("Tambahkan `fpdf` di requirements.txt untuk cetak PDF.")

        st.markdown("---")
        
        # 1. PETA ARUS KAS (SANKEY)
        st.subheader("🌊 Peta Arus Kas (Sankey Diagram)")
        df_keluar = df_bulanan[df_bulanan['Tipe'] == 'Pengeluaran'].groupby('Kategori')['Jumlah'].sum().reset_index()
        
        label_node = ["Pemasukan Bulanan"] + df_keluar['Kategori'].tolist() + ["Sisa Saldo Tersimpan"]
        sumber = [0] * (len(df_keluar) + 1)
        tujuan = list(range(1, len(label_node)))
        nilai = df_keluar['Jumlah'].tolist() + [max(0, sisa_saldo)]
        
        if sisa_saldo < 0:
            label_node.pop(); sumber.pop(); tujuan.pop(); nilai.pop()

        if in_bln > 0 or out_bln > 0:
            fig_sankey = go.Figure(data=[go.Sankey(
                node = dict(pad = 20, thickness = 25, line = dict(color = "black", width = 0.5), label = label_node, color = ["#00ffcc"] + ["#ff4d4d"] * len(df_keluar) + ["#a6e3a1"]),
                link = dict(source = sumber, target = tujuan, value = nilai, color = "rgba(128, 128, 128, 0.2)") # Warna netral untuk light/dark mode
            )])
            fig_sankey.update_layout(font_size=13, margin=dict(t=20, b=20, l=0, r=0), height=350)
            st.plotly_chart(fig_sankey, use_container_width=True, theme="streamlit")
        else:
            st.info("Belum ada aliran kas bulan ini.")
            
        st.markdown("---")

        # 2. GRAFIK BAR & PIE
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.subheader("📊 Arus Kas Harian")
            df_tren = df_bulanan.groupby(['Tanggal', 'Tipe'])['Jumlah'].sum().reset_index()
            df_tren['Tanggal'] = df_tren['Tanggal'].dt.strftime('%Y-%m-%d')
            fig_bar = px.bar(df_tren, x='Tanggal', y='Jumlah', color='Tipe', barmode='group', color_discrete_map={"Pemasukan": "#00ffcc", "Pengeluaran": "#ff4d4d"})
            st.plotly_chart(fig_bar, use_container_width=True, theme="streamlit")
            
        with col_c2:
            st.subheader("🍕 Distribusi Pengeluaran")
            df_pengeluaran = df_bulanan[df_bulanan['Tipe'] == 'Pengeluaran']
            if not df_pengeluaran.empty:
                fig_pie = px.pie(df_pengeluaran, values='Jumlah', names='Kategori', hole=0.5, color_discrete_sequence=px.colors.sequential.Tealgrn)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_pie, use_container_width=True, theme="streamlit")

        st.markdown("---")
        
        # 3. K-MEANS CLUSTERING
        st.subheader("🤖 AI Lifestyle Segmentation (K-Means)")
        df_peng_hari = df_bulanan[df_bulanan['Tipe']=='Pengeluaran'].groupby(df_bulanan['Tanggal'].dt.date)['Jumlah'].sum().reset_index()
        if len(df_peng_hari) >= 5: 
            X = df_peng_hari[['Jumlah']].values
            kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
            df_peng_hari['Cluster'] = kmeans.fit_predict(X)
            
            pusat = kmeans.cluster_centers_.flatten()
            urutan = np.argsort(pusat)
            label_map = {urutan[0]: "Hemat", urutan[1]: "Normal", urutan[2]: "Boros/Foya-foya"}
            df_peng_hari['Gaya Hidup'] = df_peng_hari['Cluster'].map(label_map)
            
            fig_cluster = px.scatter(df_peng_hari, x='Tanggal', y='Jumlah', color='Gaya Hidup', size='Jumlah', color_discrete_map={"Hemat":"#a6e3a1", "Normal":"#89b4fa", "Boros/Foya-foya":"#f38ba8"})
            st.plotly_chart(fig_cluster, use_container_width=True, theme="streamlit")
            st.caption("AI mengelompokkan kebiasaan harian Anda. Perhatikan kapan Anda berada di zona 'Boros'.")
        else:
            st.info("Data harian belum cukup untuk menjalankan Algoritma K-Means (Minimal 5 hari transaksi).")


# ==========================================
# MENU 3: AI PREDIKSI & STATISTIKA
# ==========================================
elif menu == "🔮 AI Predict & Stats":
    st.title("Proyeksi & Diagnostik Lanjut")
    df_pengeluaran_all = df[df['Tipe'] == 'Pengeluaran'].copy()
    
    if len(df_pengeluaran_all['Tanggal'].unique()) < 7:
        st.warning("⚠️ Masukkan data pengeluaran minimal 7 hari (beda tanggal).")
    else:
        df_ts = df_pengeluaran_all.groupby('Tanggal')['Jumlah'].sum().reset_index()
        df_ts = df_ts.set_index('Tanggal').asfreq('D', fill_value=0)
        
        tab1, tab2, tab3 = st.tabs(["📈 Model ARIMA", "🎲 Simulasi Monte Carlo", "📊 Uji Diagnostik (ADF)"])
        
        with tab1:
            st.subheader("Proyeksi ARIMA")
            try:
                model = ARIMA(df_ts['Jumlah'], order=(1, 1, 1))
                model_fit = model.fit()
                langkah_prediksi = st.slider("Horizon Prediksi (Hari ke depan):", 3, 30, 7)
                prediksi_obj = model_fit.get_forecast(steps=langkah_prediksi)
                forecast_mean = prediksi_obj.predicted_mean.apply(lambda x: max(0, x))
                
                tanggal_forecast = pd.date_range(start=df_ts.index[-1] + pd.Timedelta(days=1), periods=langkah_prediksi)
                fig_forecast = go.Figure()
                fig_forecast.add_trace(go.Scatter(x=df_ts.tail(21).index, y=df_ts.tail(21)['Jumlah'], mode='lines+markers', name='Data Aktual', line=dict(color='#89b4fa', width=3)))
                fig_forecast.add_trace(go.Scatter(x=tanggal_forecast, y=forecast_mean, mode='lines+markers', name='Proyeksi Rata-rata', line=dict(color='#f38ba8', dash='dot', width=3)))
                st.plotly_chart(fig_forecast, use_container_width=True, theme="streamlit")
            except Exception as e:
                st.error(f"Gagal kalkulasi ARIMA: {e}")
                
        with tab2:
            st.subheader("🎲 Simulasi Monte Carlo (100 Skenario Masa Depan)")
            st.caption("Memproyeksikan akumulasi pengeluaran 30 hari ke depan menggunakan Random Walk probabilistik.")
            
            mean_peng = df_ts['Jumlah'].mean()
            std_peng = df_ts['Jumlah'].std()
            
            hari_ke_depan = 30
            jumlah_simulasi = 100
            
            simulasi_hasil = np.zeros((hari_ke_depan, jumlah_simulasi))
            
            for i in range(jumlah_simulasi):
                random_walk = np.random.normal(loc=mean_peng, scale=std_peng, size=hari_ke_depan)
                random_walk = np.maximum(random_walk, 0)
                simulasi_hasil[:, i] = np.cumsum(random_walk)
                
            tanggal_mc = pd.date_range(start=df_ts.index[-1] + pd.Timedelta(days=1), periods=hari_ke_depan)
            fig_mc = go.Figure()
            for i in range(jumlah_simulasi):
                # Warna garis diset netral agar terlihat baik di dark/light mode
                fig_mc.add_trace(go.Scatter(x=tanggal_mc, y=simulasi_hasil[:, i], mode='lines', line=dict(color='rgba(137, 180, 250, 0.1)'), showlegend=False))
                
            fig_mc.update_layout(title="Sebaran Probabilitas Pengeluaran Sebulan ke Depan")
            st.plotly_chart(fig_mc, use_container_width=True, theme="streamlit")
            st.info(f"💡 Interpretasi AI: Terdapat variansi ekstrem berdasarkan data historis Anda. Estimasi batas atas pengeluaran kumulatif bulan depan mencapai **Rp {np.percentile(simulasi_hasil[-1, :], 95):,.0f}**.")

        with tab3:
            st.subheader("📊 Uji Stasioneritas (Augmented Dickey-Fuller)")
            st.write("Sebagai mahasiswa Statistika, Anda tentu tahu data *Time-Series* harus stasioner sebelum dianalisis.")
            hasil_adf = adfuller(df_ts['Jumlah'].values)
            st.markdown(f"""
            - **ADF Statistic:** `{hasil_adf[0]:.4f}`
            - **p-value:** `{hasil_adf[1]:.4f}`
            - **Critical Values:** 1% (`{hasil_adf[4]['1%']:.4f}`), 5% (`{hasil_adf[4]['5%']:.4f}`)
            """)
            if hasil_adf[1] < 0.05:
                st.success("✅ p-value < 0.05: Tolak H0. Data Anda stasioner dan aman untuk pemodelan ARIMA tanpa *differencing* tingkat tinggi.")
            else:
                st.error("⚠️ p-value > 0.05: Gagal tolak H0. Data mengandung *unit root* (tidak stasioner). Model perlu nilai 'd' (differencing) yang lebih besar.")

# ==========================================
# FITUR 3: AI ADVISOR (FLOATING CHAT)
# ==========================================
with st.popover("💬", use_container_width=False):
    st.markdown("<h4 style='text-align: center;'>AI Financial Advisor</h4>", unsafe_allow_html=True)
    st.caption("Tanya soal keuangan, coding, atau sapa saja!")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [{"role": "assistant", "content": "Halo! Aku Dimas, AI Advisor kamu. Mau ngobrol apa hari ini?"}]

    chat_container = st.container(height=300)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    with st.form("chat_form", clear_on_submit=True):
        cols = st.columns([4, 1])
        with cols[0]:
            user_msg = st.text_input("Pesan:", label_visibility="collapsed", placeholder="Tanya sesuatu...")
        with cols[1]:
            submit_chat = st.form_submit_button("Kirim")

    if submit_chat and user_msg:
        st.session_state.chat_history.append({"role": "user", "content": user_msg})
        try:
            api_key = st.secrets["Gemini_API_Key"]
            genai.configure(api_key=api_key)
            model_ai = genai.GenerativeModel('gemini-3.1-flash-lite')
            
            profil_pribadi = st.secrets.get("USER_BIO", "Pengguna aplikasi ini")
            
            bulan_ini = pd.Timestamp.now().to_period('M')
            df['Bulan_Tahun'] = df['Tanggal'].dt.to_period('M')
            df_bulan_ini = df[df['Bulan_Tahun'] == bulan_ini]
            
            in_bln = df_bulan_ini[df_bulan_ini['Tipe'] == 'Pemasukan']['Jumlah'].sum()
            out_bln = df_bulan_ini[df_bulan_ini['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
            sisa_bln = in_bln - out_bln
            
            formatted_history = []
            for chat in st.session_state.chat_history[:-1]:
                role = "model" if chat["role"] == "assistant" else "user"
                formatted_history.append({"role": role, "parts": [chat["content"]]})
                
            chat_session = model_ai.start_chat(history=formatted_history)
            
            instruksi_sistem = f"""[INSTRUKSI SISTEM: Kamu adalah asisten AI finansial dan teman ngobrol yang asik. 
            Profil Pengguna Kamu: {profil_pribadi}
            
            Aturan ketat untuk merespons:
            1. Jika hanya menyapa, balas santai dan hangat. JANGAN tampilkan data keuangan!
            2. Kamu bisa diajak ngobrol topik apa saja dengan cerdas.
            3. HANYA JIKA ditanya spesifik tentang keuangannya, barulah gunakan data ini:
               - Pemasukan Bulan Ini: Rp {in_bln:,.0f}
               - Pengeluaran Bulan Ini: Rp {out_bln:,.0f}
               - Sisa Saldo: Rp {sisa_bln:,.0f}
            ]
            
            Pesan Pengguna: {user_msg}"""
            
            response = chat_session.send_message(instruksi_sistem)
            st.session_state.chat_history.append({"role": "assistant", "content": response.text})
            
            st.rerun()
            
        except KeyError:
            st.error("⚠️ API Key Gemini belum diatur di Streamlit Secrets!")
        except Exception as e:
            st.error(f"Gagal memuat AI: {e}")

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import random
from statsmodels.tsa.arima.model import ARIMA
import warnings

# Mengabaikan warning konvergensi
warnings.filterwarnings('ignore')

# --- KONFIGURASI HALAMAN ---
# Menggunakan layout wide dan sidebar terbuka dari awal
st.set_page_config(page_title="Smart Finance", page_icon="💠", layout="wide", initial_sidebar_state="expanded")

# --- CUSTOM CSS UNTUK TAMPILAN ELEGAN ---
st.markdown("""
<style>
    /* Styling untuk Metric Cards agar terlihat seperti panel elegan */
    div[data-testid="metric-container"] {
        background: linear-gradient(145deg, #1e1e2e, #2b2b40);
        border-left: 5px solid #00ffcc;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    /* Efek melayang saat kursor diarahkan (Hover) */
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0, 255, 204, 0.2);
    }
    /* Styling form input agar lebih soft */
    div[data-testid="stForm"] {
        background-color: rgba(30, 30, 46, 0.5);
        border: 1px solid #45475a;
        border-radius: 15px;
        padding: 25px;
    }
    /* Mempercantik font judul */
    h1, h2, h3 {
        font-family: 'Trebuchet MS', sans-serif;
        color: #89b4fa !important;
    }
    /* Menghilangkan padding atas bawaan Streamlit yang terlalu lebar */
    .block-container {
        padding-top: 2rem;
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

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown("<h2 style='text-align: center; color: #00ffcc !important;'>💠 Smart Finance</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")
menu = st.sidebar.radio(
    "Navigasi Dashboard:",
    ["🏠 Beranda & Input", "📈 Analisis Bulanan", "🔮 AI Prediksi", "🧮 Kalkulator Finansial"]
)
st.sidebar.markdown("---")
st.sidebar.caption("© 2026 | Financial Dashboard & Analytics")

# Kumpulan kata-kata motivasi dinamis
kumpulan_motivasi = [
    "Membangun stabilitas finansial itu seperti melatih algoritma machine learning; butuh kesabaran, input data yang konsisten, dan evaluasi berkelanjutan.",
    "Perjalanan panjang berdiri di kereta setiap hari mungkin melelahkan, tapi jadikan itu saksi bisu perjuanganmu membangun masa depan yang solid.",
    "Angka tidak pernah berbohong. Disiplin mencatat statistik hari ini adalah kunci untuk memprediksi kebebasan finansial di masa depan.",
    "Bermain game atau menonton anime favorit sesekali adalah reward terbaik setelah kamu berhasil mengatur arus kas dengan cerdas minggu ini."
]

# ==========================================
# MENU 1: BERANDA & INPUT (PENGGABUNGAN TAB 1 & 2)
# ==========================================
if menu == "🏠 Beranda & Input":
    st.title("Ringkasan Hari Ini & Input Transaksi")
    st.info(f"💡 **Quote Hari Ini:** *{random.choice(kumpulan_motivasi)}*")
    
    # Tampilan Metrik Harian di atas
    hari_ini = pd.to_datetime(datetime.today().date())
    df_harian = df[df['Tanggal'] == hari_ini]
    
    pemasukan_harian = df_harian[df_harian['Tipe'] == 'Pemasukan']['Jumlah'].sum()
    pengeluaran_harian = df_harian[df_harian['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
    saldo_harian = pemasukan_harian - pengeluaran_harian
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Pemasukan Hari Ini", f"Rp {pemasukan_harian:,.0f}")
    col2.metric("🔴 Pengeluaran Hari Ini", f"Rp {pengeluaran_harian:,.0f}")
    col3.metric("💎 Net Saldo", f"Rp {saldo_harian:,.0f}")
    
    st.markdown("---")
    
    # Form Input di Bawahnya
    col_form, col_tabel = st.columns([1, 1.2])
    
    with col_form:
        st.subheader("📝 Catat Transaksi")
        with st.form("form_transaksi", clear_on_submit=True):
            tanggal = st.date_input("Tanggal Transaksi", datetime.today())
            tipe = st.radio("Jenis", ["Pemasukan", "Pengeluaran"], horizontal=True)
            
            if tipe == "Pemasukan":
                kategori = st.selectbox("Kategori", ["Gaji", "Bonus", "Investasi", "Lain-lain"])
            else:
                kategori = st.selectbox("Kategori", ["Makan/Minum", "Transportasi", "Tagihan", "Belanja", "Hiburan", "Lain-lain"])
                
            jumlah = st.number_input("Jumlah (Rp)", min_value=0, step=5000)
            keterangan = st.text_input("Keterangan (Opsional)")
            
            submit = st.form_submit_button("💾 Simpan Data", use_container_width=True)
            
            if submit:
                if jumlah > 0:
                    data_baru = pd.DataFrame({
                        'Tanggal': [pd.to_datetime(tanggal)],
                        'Tipe': [tipe],
                        'Kategori': [kategori],
                        'Jumlah': [jumlah],
                        'Keterangan': [keterangan]
                    })
                    df = pd.concat([df, data_baru], ignore_index=True)
                    save_data(df)
                    st.success("✅ Tersimpan!")
                    st.rerun()
                else:
                    st.error("⚠️ Jumlah tidak boleh nol.")
                    
    with col_tabel:
        st.subheader("📋 Riwayat Hari Ini")
        if not df_harian.empty:
            st.dataframe(df_harian[['Tipe', 'Kategori', 'Jumlah', 'Keterangan']].style.format({"Jumlah": "Rp {:,.0f}"}), use_container_width=True, height=280)
        else:
            st.markdown("<br><br><div style='text-align: center; color: gray;'>Belum ada aktivitas terekam hari ini.</div>", unsafe_allow_html=True)

# ==========================================
# MENU 2: ANALISIS BULANAN
# ==========================================
elif menu == "📈 Analisis Bulanan":
    st.title("Visualisasi & Analisis Bulanan")
    
    if df.empty:
        st.warning("Belum ada data untuk dianalisis.")
    else:
        df['Bulan_Tahun'] = df['Tanggal'].dt.to_period('M')
        list_bulan_str = [str(b) for b in sorted(df['Bulan_Tahun'].unique(), reverse=True)]
        
        bulan_pilihan = st.selectbox("Pilih Periode", list_bulan_str)
        df_bulanan = df[df['Bulan_Tahun'] == bulan_pilihan]
        
        col_c1, col_c2 = st.columns(2)
        
        # Grafik 1: Bar Chart (Lebih modern dari line chart untuk agregasi harian)
        with col_c1:
            st.subheader("Arus Kas Harian")
            df_tren = df_bulanan.groupby(['Tanggal', 'Tipe'])['Jumlah'].sum().reset_index()
            fig_bar = px.bar(df_tren, x='Tanggal', y='Jumlah', color='Tipe', barmode='group',
                             color_discrete_map={"Pemasukan": "#00ffcc", "Pengeluaran": "#ff4d4d"},
                             template="plotly_dark")
            fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_bar, use_container_width=True)
            
        # Grafik 2: Donut Chart dengan desain sleek
        with col_c2:
            st.subheader("Distribusi Pengeluaran")
            df_pengeluaran = df_bulanan[df_bulanan['Tipe'] == 'Pengeluaran']
            if not df_pengeluaran.empty:
                fig_pie = px.pie(df_pengeluaran, values='Jumlah', names='Kategori', hole=0.5, template="plotly_dark",
                                 color_discrete_sequence=px.colors.sequential.Tealgrn)
                fig_pie.update_traces(textposition='inside', textinfo='percent')
                fig_pie.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Tidak ada pengeluaran di bulan ini.")

# ==========================================
# MENU 3: AI PREDIKSI (ARIMA)
# ==========================================
elif menu == "🔮 AI Prediksi":
    st.title("Proyeksi Tren Pengeluaran")
    st.markdown("Mesin analitik ini menggunakan algoritma **ARIMA** untuk mempelajari pola pengeluaran historis Anda.")
    
    df_pengeluaran_all = df[df['Tipe'] == 'Pengeluaran'].copy()
    
    if len(df_pengeluaran_all['Tanggal'].unique()) < 7:
        st.warning("⚠️ Masukkan data pengeluaran minimal 7 hari agar AI dapat membaca pola dengan akurat.")
    else:
        df_ts = df_pengeluaran_all.groupby('Tanggal')['Jumlah'].sum().reset_index()
        df_ts = df_ts.set_index('Tanggal').asfreq('D', fill_value=0)
        
        try:
            model = ARIMA(df_ts['Jumlah'], order=(1, 1, 1))
            model_fit = model.fit()
            
            langkah_prediksi = st.slider("Horizon Prediksi (Hari ke depan):", 3, 30, 7)
            forecast = model_fit.forecast(steps=langkah_prediksi)
            
            tanggal_forecast = pd.date_range(start=df_ts.index[-1] + pd.Timedelta(days=1), periods=langkah_prediksi)
            df_forecast = pd.DataFrame({'Tanggal': tanggal_forecast, 'Prediksi': forecast.values})
            df_forecast['Prediksi'] = df_forecast['Prediksi'].apply(lambda x: max(0, x))
            
            fig_forecast = go.Figure()
            hist_plot = df_ts.tail(21) # Ambil 3 minggu terakhir
            
            fig_forecast.add_trace(go.Scatter(
                x=hist_plot.index, y=hist_plot['Jumlah'], 
                mode='lines+markers', name='Data Historis', line=dict(color='#89b4fa', width=3)
            ))
            fig_forecast.add_trace(go.Scatter(
                x=df_forecast['Tanggal'], y=df_forecast['Prediksi'], 
                mode='lines+markers', name='Proyeksi AI', line=dict(color='#f38ba8', dash='dot', width=3)
            ))
            
            fig_forecast.update_layout(
                template="plotly_dark",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_forecast, use_container_width=True)
            
        except Exception as e:
            st.error(f"Gagal melakukan kalkulasi AI: {e}")

# ==========================================
# MENU 4: KALKULATOR FINANSIAL
# ==========================================
elif menu == "🧮 Kalkulator Finansial":
    st.title("Simulasi Anggaran & Tabungan")
    
    col_target, col_budget = st.columns(2)
    
    with col_target:
        st.subheader("🎯 Kalkulator Target")
        with st.container(border=True):
            nama_target = st.text_input("Nama Target", "Laptop Baru / Liburan")
            nominal_target = st.number_input("Nominal Target (Rp)", min_value=0, value=10000000, step=500000)
            jangka_waktu = st.number_input("Berapa Bulan?", min_value=1, value=6)
            
            if nominal_target > 0:
                per_bulan = nominal_target / jangka_waktu
                st.success(f"Anda perlu menyisihkan **Rp {per_bulan:,.0f} / bulan**.")
                
    with col_budget:
        st.subheader("📊 Anggaran 50/30/20")
        with st.container(border=True):
            gaji = st.number_input("Estimasi Pendapatan Bulan Ini (Rp)", min_value=0, value=5000000, step=100000)
            
            if gaji > 0:
                kebutuhan = gaji * 0.50
                keinginan = gaji * 0.30
                tabungan = gaji * 0.20
                
                st.markdown(f"**Kebutuhan Pokok (50%):** Rp {kebutuhan:,.0f}")
                st.markdown(f"**Keinginan/Hobi (30%):** Rp {keinginan:,.0f}")
                st.markdown(f"**Investasi/Tabungan (20%):** Rp {tabungan:,.0f}")

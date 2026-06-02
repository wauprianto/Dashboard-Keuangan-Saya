import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import random
from statsmodels.tsa.arima.model import ARIMA
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
                if password_input == "220303": 
                    st.session_state['logged_in'] = True
                    st.rerun()
                else:
                    st.error("❌ Password salah!")
    st.stop() 

if st.sidebar.button("🚪 Logout"):
    st.session_state['logged_in'] = False
    st.rerun()

st.rerun()

# -- CUSTOM CSS ---
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
    ["🏠 Dashboard", "📈 Analyze", "🔮 AI Predict"]
)
st.sidebar.markdown("---")
st.sidebar.caption("© 2026 | Financial Dashboard & Analytics")
st.sidebar.caption("Prianto Sanema Wau")

kumpulan_motivasi = [
    "Membangun stabilitas finansial itu seperti melatih algoritma machine learning; butuh kesabaran, input data yang konsisten, dan evaluasi berkelanjutan.",
    "Perjalanan panjang berdiri di kereta setiap hari mungkin melelahkan, tapi jadikan itu saksi bisu perjuanganmu membangun masa depan yang solid.",
    "Angka tidak pernah berbohong. Disiplin mencatat statistik hari ini adalah kunci untuk memprediksi kebebasan finansial di masa depan."
]

# ==========================================
# MENU 1: BERANDA & INPUT
# ==========================================
if menu == "🏠 Dashboard":
    st.title("Ringkasan Hari Ini & Input Transaksi")
    st.info(f"💡 **Quote Hari Ini:** *{random.choice(kumpulan_motivasi)}*")
    
    # 1. KOMPUTASI METRIK
    hari_ini = pd.to_datetime(datetime.today().date())
    df_harian = df[df['Tanggal'] == hari_ini]
    
    pemasukan_harian = df_harian[df_harian['Tipe'] == 'Pemasukan']['Jumlah'].sum()
    pengeluaran_harian = df_harian[df_harian['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
    
    total_pemasukan_semua = df[df['Tipe'] == 'Pemasukan']['Jumlah'].sum()
    total_pengeluaran_semua = df[df['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
    saldo_akhir = total_pemasukan_semua - total_pengeluaran_semua
    
    # 2. SISTEM DETEKSI ANOMALI (Z-SCORE) - DIREVISI
    df_pengeluaran_all = df[df['Tipe'] == 'Pengeluaran']
    if not df_pengeluaran_all.empty and pengeluaran_harian > 0: # Hanya memicu jika ada pengeluaran hari ini
        pengeluaran_hist = df_pengeluaran_all.groupby(df_pengeluaran_all['Tanggal'].dt.date)['Jumlah'].sum()
        if len(pengeluaran_hist) > 2:
            mean_pengeluaran = pengeluaran_hist.mean()
            std_pengeluaran = pengeluaran_hist.std()
            if std_pengeluaran > 0:
                z_score = (pengeluaran_harian - mean_pengeluaran) / std_pengeluaran
                if z_score > 2: # Threshold Anomali
                    st.error(f"⚠️ **Peringatan Anomali Statistik:** Pengeluaran hari ini (Z-Score: {z_score:.2f}) melonjak jauh di atas rata-rata kebiasaan harian Anda (Rp {mean_pengeluaran:,.0f}).")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Pemasukan Hari Ini", f"Rp {pemasukan_harian:,.0f}")
    col2.metric("🔴 Pengeluaran Hari Ini", f"Rp {pengeluaran_harian:,.0f}")
    col3.metric("💎 Saldo Akhir", f"Rp {saldo_akhir:,.0f}")
    
    st.markdown("---")
    
        # 3. POP-UP KALKULATOR DENGAN TOMBOL HITUNG (MENGGUNAKAN FORM)
    with st.popover("🧮 Buka Kalkulator Finansial", use_container_width=True):
        st.markdown("<h3 style='text-align: center;'>Simulasi Anggaran & Tabungan</h3>", unsafe_allow_html=True)
        col_target, col_budget = st.columns(2)
        
        with col_target:
            st.subheader("🎯 Kalkulator Target")
            # Menggunakan st.form agar ada tombol khusus yang tidak langsung mereset layar
            with st.form("form_kalkulator_target", border=True):
                nama_target = st.text_input("Nama Target", "Laptop Baru / Liburan")
                nominal_target = st.number_input("Nominal Target (Rp)", min_value=0, value=10000000, step=500000)
                jangka_waktu = st.number_input("Berapa Bulan?", min_value=1, value=6)
                
                # Ini tombolnya yang sekarang dijamin muncul
                submitted_target = st.form_submit_button("Hitung Target", use_container_width=True)
                
                if submitted_target:
                    if nominal_target > 0:
                        per_bulan = nominal_target / jangka_waktu
                        st.markdown("---")
                        st.success(f"Anda perlu menyisihkan **Rp {per_bulan:,.0f} / bulan**.")
                        
                        persentase = min(saldo_akhir / nominal_target, 1.0)
                        if saldo_akhir >= nominal_target:
                            st.info(f"🎉 Selamat! Saldo saat ini sudah cukup untuk **{nama_target}**!")
                        else:
                            progress_val = max(0.0, persentase) 
                            st.progress(progress_val)
                            st.caption(f"Terkumpul saat ini: **Rp {saldo_akhir:,.0f}** dari Rp {nominal_target:,.0f} ({progress_val*100:.1f}%)")
                    else:
                        st.error("Nominal target harus lebih dari 0.")
                    
        with col_budget:
            st.subheader("📊 Anggaran 50/30/20")
            # Menggunakan st.form untuk sisi anggaran
            with st.form("form_kalkulator_anggaran", border=True):
                gaji = st.number_input("Estimasi Pendapatan Bulan Ini (Rp)", min_value=0, value=5000000, step=100000)
                
                # Ini tombolnya yang sekarang dijamin muncul
                submitted_anggaran = st.form_submit_button("Hitung Anggaran", use_container_width=True)
                
                if submitted_anggaran:
                    if gaji > 0:
                        kebutuhan = gaji * 0.50
                        keinginan = gaji * 0.30
                        tabungan = gaji * 0.20
                        
                        st.markdown("---")
                        st.success("✅ Rincian alokasi ideal Anda:")
                        st.markdown(f"**Kebutuhan Pokok (50%):** Rp {kebutuhan:,.0f}")
                        st.markdown(f"**Keinginan/Hobi (30%):** Rp {keinginan:,.0f}")
                        st.markdown(f"**Investasi/Tabungan (20%):** Rp {tabungan:,.0f}")
                    else:
                        st.error("Pendapatan harus lebih dari 0.")

    st.markdown("<br>", unsafe_allow_html=True)

    col_form, col_tabel = st.columns([1, 1.2])
    
    with col_form:
        st.subheader("📝 Catat Transaksi")
        tanggal = st.date_input("Tanggal Transaksi", datetime.today())
        tipe = st.radio("Jenis", ["Pemasukan", "Pengeluaran"], horizontal=True)
        
        if tipe == "Pemasukan":
            kategori = st.selectbox("Kategori", ["Gaji", "Bonus", "Investasi", "Lain-lain"])
        else:
            kategori = st.selectbox("Kategori", ["Makan/Minum", "Transportasi", "Tagihan", "Belanja", "Hiburan", "Lain-lain"])
            
        jumlah = st.number_input("Jumlah (Rp)", min_value=0, step=5000)
        keterangan = st.text_input("Keterangan (Opsional)")
        
        submit = st.button("💾 Simpan Data", use_container_width=True)
        if submit:
            if jumlah > 0:
                data_baru = pd.DataFrame({'Tanggal': [pd.to_datetime(tanggal)],'Tipe': [tipe],'Kategori': [kategori],'Jumlah': [jumlah],'Keterangan': [keterangan]})
                df = pd.concat([df, data_baru], ignore_index=True)
                save_data(df)
                st.success("✅ Tersimpan!")
                st.rerun()
            else:
                st.error("⚠️ Jumlah tidak boleh nol.")

    # 4. TABEL DENGAN FILTER DINAMIS - DIREVISI (Fungsi Pewarnaan Teks)
    with col_tabel:
        st.subheader("📋 Riwayat Transaksi")
        if not df.empty:
            pilihan_tipe = st.multiselect("Filter Jenis:", options=["Pemasukan", "Pengeluaran"], default=["Pemasukan", "Pengeluaran"])
            
            df_tampil = df[df['Tipe'].isin(pilihan_tipe)].sort_values(by='Tanggal', ascending=False)
            
            # Fungsi mewarnai kolom jumlah berdasarkan tipe
            def color_jumlah(row):
                if row['Tipe'] == 'Pemasukan':
                    return ['color: #00ffcc'] * len(row)
                else:
                    return ['color: #ff4d4d'] * len(row)

            st.dataframe(
                df_tampil[['Tanggal', 'Tipe', 'Kategori', 'Jumlah', 'Keterangan']].style
                .apply(color_jumlah, axis=1)
                .format({
                    "Tanggal": lambda x: x.strftime("%Y-%m-%d"), 
                    "Jumlah": "Rp {:,.0f}"
                }), 
                use_container_width=True, 
                height=230,
                hide_index=True
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
        
        # 5. FITUR EXPORT / DOWNLOAD LAPORAN
        with col_opt2:
            st.markdown("<br>", unsafe_allow_html=True)
            csv = df_bulanan.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Laporan (CSV)",
                data=csv,
                file_name=f"Laporan_Keuangan_{bulan_pilihan}.csv",
                mime="text/csv",
            )
            
        st.markdown("---")
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.subheader("Arus Kas Harian")
            df_tren = df_bulanan.groupby(['Tanggal', 'Tipe'])['Jumlah'].sum().reset_index()
            fig_bar = px.bar(df_tren, x='Tanggal', y='Jumlah', color='Tipe', barmode='group',
                             color_discrete_map={"Pemasukan": "#00ffcc", "Pengeluaran": "#ff4d4d"},
                             template="plotly_dark")
            fig_bar.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig_bar, use_container_width=True)
            
        with col_c2:
            st.subheader("Distribusi Pengeluaran")
            df_pengeluaran = df_bulanan[df_bulanan['Tipe'] == 'Pengeluaran']
            if not df_pengeluaran.empty:
                fig_pie = px.pie(df_pengeluaran, values='Jumlah', names='Kategori', hole=0.5, template="plotly_dark",
                                 color_discrete_sequence=px.colors.sequential.Tealgrn)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                st.info("Tidak ada pengeluaran di bulan ini.")

# ==========================================
# MENU 3: AI PREDIKSI (ARIMA ADVANCED)
# ==========================================
elif menu == "🔮 AI Predict":
    st.title("Proyeksi Pengeluaran (ARIMA with Confidence Interval)")
    st.markdown("Model ini menggunakan algoritma **ARIMA (Autoregressive Integrated Moving Average)** dengan pemetaan *Upper* dan *Lower Bounds* 95% untuk menganalisis batas toleransi volatilitas pengeluaran Anda ke depan.")
    
    df_pengeluaran_all = df[df['Tipe'] == 'Pengeluaran'].copy()
    
    if len(df_pengeluaran_all['Tanggal'].unique()) < 7:
        st.warning("⚠️ Masukkan data pengeluaran minimal 7 hari (beda tanggal) agar AI dapat membaca pola dengan akurat.")
    else:
        df_ts = df_pengeluaran_all.groupby('Tanggal')['Jumlah'].sum().reset_index()
        df_ts = df_ts.set_index('Tanggal').asfreq('D', fill_value=0)
        
        try:
            # Fit Model ARIMA
            model = ARIMA(df_ts['Jumlah'], order=(1, 1, 1))
            model_fit = model.fit()
            
            langkah_prediksi = st.slider("Horizon Prediksi (Hari ke depan):", 3, 30, 7)
            
            # Forecast dengan Confidence Interval (Interval Kepercayaan)
            prediksi_obj = model_fit.get_forecast(steps=langkah_prediksi)
            forecast_mean = prediksi_obj.predicted_mean.apply(lambda x: max(0, x))
            conf_int = prediksi_obj.conf_int()
            lower_bound = conf_int.iloc[:, 0].apply(lambda x: max(0, x))
            upper_bound = conf_int.iloc[:, 1].apply(lambda x: max(0, x))
            
            tanggal_forecast = pd.date_range(start=df_ts.index[-1] + pd.Timedelta(days=1), periods=langkah_prediksi)
            
            # Visualisasi Plotly Advanced
            fig_forecast = go.Figure()
            hist_plot = df_ts.tail(21)
            
            # Area Historis
            fig_forecast.add_trace(go.Scatter(x=hist_plot.index, y=hist_plot['Jumlah'], mode='lines+markers', name='Data Aktual', line=dict(color='#89b4fa', width=3)))
            
            # Upper Bound (Batas Atas)
            fig_forecast.add_trace(go.Scatter(x=tanggal_forecast, y=upper_bound, mode='lines', line=dict(width=0), showlegend=False))
            # Lower Bound (Batas Bawah) dengan fill
            fig_forecast.add_trace(go.Scatter(x=tanggal_forecast, y=lower_bound, mode='lines', fill='tonexty', fillcolor='rgba(243, 139, 168, 0.2)', line=dict(width=0), name='95% Confidence Interval'))
            # Garis Prediksi Tengah
            fig_forecast.add_trace(go.Scatter(x=tanggal_forecast, y=forecast_mean, mode='lines+markers', name='Proyeksi Rata-rata', line=dict(color='#f38ba8', dash='dot', width=3)))
            
            fig_forecast.update_layout(
                template="plotly_dark", plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_forecast, use_container_width=True)
            
        except Exception as e:
            st.error(f"Gagal melakukan kalkulasi AI: {e}")

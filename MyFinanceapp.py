import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz  
import os
import json
import tempfile
import requests
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
import google.generativeai as genai
import warnings
from streamlit_gsheets import GSheetsConnection  # TAMBAHAN: Library Google Sheets

# Coba load FPDF untuk cetak PDF
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

# -- CUSTOM CSS (ADAPTIF CERAH/GELAP) ---
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: var(--secondary-background-color);
        border-left: 5px solid #3498db;
        padding: 15px 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="stForm"] {
        background-color: var(--secondary-background-color);
        border: 1px solid var(--border-color);
        border-radius: 15px;
        padding: 25px;
    }
    /* Bola Melayang AI */
    div[data-testid="stPopover"]:last-of-type > button {
        position: fixed !important;
        top: 70px !important;
        right: 25px !important;
        width: 65px !important;
        height: 65px !important;
        border-radius: 50% !important;
        background: linear-gradient(135deg, #a29bfe, #74b9ff) !important;
        color: white !important;
        font-size: 30px !important;
        z-index: 99999 !important;
        box-shadow: 0 6px 15px rgba(0, 0, 0, 0.3) !important;
        padding: 0 !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# --- INISIALISASI DATA (KONEKSI GOOGLE SHEETS API) ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # Membaca data langsung dari lembar kerja Sheet1
        df = conn.read(worksheet="Sheet1")
        
        # Antisipasi jika database kosong atau kolom belum terbentuk
        if df.empty or 'Tanggal' not in df.columns:
            return pd.DataFrame(columns=['Tanggal', 'Tipe', 'Kategori', 'Jumlah', 'Keterangan'])
            
        df['Tanggal'] = pd.to_datetime(df['Tanggal'])
        return df
    except Exception as e:
        # Kembalikan dataframe kosong terstruktur jika pembacaan gagal/awal sistem
        return pd.DataFrame(columns=['Tanggal', 'Tipe', 'Kategori', 'Jumlah', 'Keterangan'])

def save_data(df_baru):
    try:
        # Memperbarui data secara menyeluruh ke Google Sheets
        conn.update(worksheet="Sheet1", data=df_baru)
        # Hapus cache internal Streamlit agar inputan langsung ter-render di halaman utama
        st.cache_data.clear()
    except Exception as e:
        st.error(f"❌ Gagal sinkronisasi ke Google Sheets: {e}")

# Memuat data aktif
df = load_data()

def tebak_kategori(keterangan, tipe):
    teks = keterangan.lower()
    if tipe == "Pengeluaran":
        if any(kata in teks for kata in ['makan', 'minum', 'nasi', 'kopi', 'warteg']): return "Makan/Minum"
        if any(kata in teks for kata in ['kereta', 'krl', 'bensin', 'parkir']): return "Transportasi"
        if any(kata in teks for kata in ['listrik', 'wifi', 'kuota', 'bpjs']): return "Tagihan"
        if any(kata in teks for kata in ['game', 'anime', 'bioskop', 'netflix']): return "Hiburan"
        if any(kata in teks for kata in ['baju', 'shopee', 'indomaret', 'belanja']): return "Belanja"
    else:
        if any(kata in teks for kata in ['gaji', 'upah']): return "Gaji"
        if any(kata in teks for kata in ['bonus', 'thr']): return "Bonus"
        if any(kata in teks for kata in ['saham', 'kripto']): return "Investasi"
    return "Lain-lain"

# --- SIDEBAR NAVIGATION ---
st.sidebar.markdown("## Smart Finance")
st.sidebar.markdown("---")
menu = st.sidebar.radio("Navigasi Dashboard:", ["🏠 Dashboard", "📈 Analyze", "🔮 Advanced Stats & Predict"])
st.sidebar.markdown("---")

# FITUR 13: LIVE API PORTOFOLIO EKSTERNAL
st.sidebar.caption("🌍 Live Global Market")
try:
    btc_res = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=3)
    if btc_res.status_code == 200:
        btc_price = float(btc_res.json()['price'])
        st.sidebar.info(f"**Bitcoin:** ${btc_price:,.2f}")
except:
    st.sidebar.caption("API Market tidak tersedia.")
    
st.sidebar.markdown("🔗 [Buka Market Binance (BTC)](https://www.binance.com/en/trade/BTC_USDT)")
st.sidebar.markdown("---")

if st.sidebar.button("🧹 Hapus Cache Aplikasi", use_container_width=True):
    st.cache_data.clear()
    st.sidebar.success("Cache dibersihkan!")
    st.rerun()
    
st.sidebar.caption("© 2026 | Analytics Dashboard")

# ==========================================
# MENU 1: BERANDA & INPUT
# ==========================================
if menu == "🏠 Dashboard":
    st.title("Ringkasan Hari Ini & Input Transaksi")
    
    waktu_wib = pd.Timestamp.utcnow() + pd.Timedelta(hours=7)
    waktu_sekarang = waktu_wib.normalize().tz_localize(None)
    kemarin = waktu_sekarang - pd.Timedelta(days=1)
    
    if not df.empty:
        df['Tanggal_Clean'] = pd.to_datetime(df['Tanggal']).dt.normalize()
        df_harian = df[df['Tanggal_Clean'] == waktu_sekarang]
        df_kemarin = df[df['Tanggal_Clean'] == kemarin]
        
        in_hari_ini = df_harian[df_harian['Tipe'] == 'Pemasukan']['Jumlah'].sum()
        in_kemarin = df_kemarin[df_kemarin['Tipe'] == 'Pemasukan']['Jumlah'].sum()
        out_hari_ini = df_harian[df_harian['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
        out_kemarin = df_kemarin[df_kemarin['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
        saldo_akhir = df[df['Tipe'] == 'Pemasukan']['Jumlah'].sum() - df[df['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
    else:
        in_hari_ini = in_kemarin = out_hari_ini = out_kemarin = saldo_akhir = 0

    delta_in = int(in_hari_ini - in_kemarin)
    delta_out = int(out_hari_ini - out_kemarin)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("🟢 Pemasukan Hari Ini", f"Rp {in_hari_ini:,.0f}", delta=f"{delta_in:,.0f} vs kemarin")
    col2.metric("🔴 Pengeluaran Hari Ini", f"Rp {out_hari_ini:,.0f}", delta=f"{delta_out:,.0f} vs kemarin", delta_color="inverse")
    col3.metric("💎 Saldo Akhir (Aktual)", f"Rp {saldo_akhir:,.0f}")
    
    st.markdown("---")
    
    col_gauge, col_form = st.columns([1, 1.5])
    
    with col_gauge:
        st.subheader("🏎️ Burn Rate Meter")
        batas_aman = 150000 
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = out_hari_ini,
            title = {'text': "Batas Pengeluaran Harian", 'font': {'size': 14}},
            gauge = {
                'axis': {'range': [None, batas_aman * 2]},
                'bar': {'color': "#3498db"},
                'steps' : [
                    {'range': [0, batas_aman], 'color': "rgba(46, 204, 113, 0.2)"},
                    {'range': [batas_aman, batas_aman*2], 'color': "rgba(231, 76, 60, 0.2)"}],
                'threshold': {'line': {'color': "red", 'width': 4}, 'thickness': 0.75, 'value': batas_aman}
            }
        ))
        fig_gauge.update_layout(height=250, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig_gauge, use_container_width=True, theme="streamlit")
        
        st.subheader("📸 Scan Struk (AI Vision)")
        file_struk = st.file_uploader("Upload foto struk belanja:", type=['png', 'jpg', 'jpeg'])
        if file_struk:
            if st.button("Proses Struk dengan AI", use_container_width=True):
                try:
                    import PIL.Image
                    img_struk = PIL.Image.open(file_struk)
                    api_key_saya = st.secrets["Gemini_API_Key"]
                    genai.configure(api_key=api_key_saya)
                    model_vision = genai.GenerativeModel('gemini-3.1-flash-lite')
                    
                    prompt_vision = """
                    Baca struk ini. Ekstrak total belanja (hanya angka bulat, tanpa tulisan Rp/titik/koma) 
                    dan tebak kategori (Pilih salah satu: Makan/Minum, Transportasi, Tagihan, Belanja, Hiburan, Lain-lain). 
                    Format output HANYA JSON: {"Kategori": "...", "Jumlah": 15000}
                    """
                    respon_vision = model_vision.generate_content([prompt_vision, img_struk])
                    hasil_vision = json.loads(respon_vision.text.replace('```json\n', '').replace('```', '').strip())
                    
                    df = pd.concat([df, pd.DataFrame([{'Tanggal': pd.to_datetime(waktu_sekarang), 'Tipe': 'Pengeluaran', 'Kategori': hasil_vision['Kategori'], 'Jumlah': hasil_vision['Jumlah'], 'Keterangan': 'Input dari Scan Struk'}])], ignore_index=True)
                    save_data(df)
                    st.success(f"✅ Sukses discan! Kategori: {hasil_vision['Kategori']} | Rp {hasil_vision['Jumlah']:,.0f}")
                    st.rerun()
                except Exception as e:
                    st.error("Gagal membaca struk. Pastikan foto terang dan API Key valid.")

        st.subheader("🪄 Magic Input")
        with st.form("magic_form", border=True):
            magic_teks = st.text_input("Ketik transaksi natural:", placeholder="Cth: Tadi naik kereta 15000")
            if st.form_submit_button("Catat Otomatis (AI)"):
                if magic_teks:
                    try:
                        api_key_saya = st.secrets["Gemini_API_Key"]
                        genai.configure(api_key=api_key_saya)
                        model = genai.GenerativeModel('gemini-3.1-flash-lite')
                        prompt = f"""Ekstrak teks ini jadi format JSON. Kunci: 'Tipe' (Pemasukan/Pengeluaran), 'Kategori' (Makan/Minum, Transportasi, Tagihan, Belanja, Hiburan, Gaji, Bonus, Lain-lain), 'Jumlah' (angka bulat), 'Keterangan' (string). Teks: "{magic_teks}". Hanya output JSON."""
                        respon = model.generate_content(prompt)
                        hasil = json.loads(respon.text.replace('```json\n', '').replace('```', '').strip())
                        
                        df = pd.concat([df, pd.DataFrame([{'Tanggal': pd.to_datetime(waktu_sekarang), 'Tipe': hasil['Tipe'], 'Kategori': hasil['Kategori'], 'Jumlah': hasil['Jumlah'], 'Keterangan': hasil['Keterangan']}])], ignore_index=True)
                        save_data(df)
                        st.success(f"Dicatat: {hasil['Kategori']} - Rp {hasil['Jumlah']}")
                        st.rerun()
                    except Exception as e:
                        st.error("Gagal diproses AI. Pastikan API valid.")
                        
    with col_form:
        st.subheader("📝 Catat Manual")
        if 'form_key' not in st.session_state: st.session_state.form_key = 0
            
        tanggal = st.date_input("Tanggal Transaksi", waktu_wib.date())
        tipe = st.radio("Jenis", ["Pemasukan", "Pengeluaran"], horizontal=True)
        keterangan = st.text_input("Keterangan", placeholder="Cth: Makan Siang", key=f"ket_{st.session_state.form_key}")
        prediksi_kat = tebak_kategori(keterangan, tipe) if keterangan else "Lain-lain"
        
        list_kat = ["Gaji", "Bonus", "Investasi", "Lain-lain"] if tipe == "Pemasukan" else ["Makan/Minum", "Transportasi", "Tagihan", "Belanja", "Hiburan", "Lain-lain"]
        idx = list_kat.index(prediksi_kat) if prediksi_kat in list_kat else (len(list_kat)-1)
        kategori = st.selectbox("Kategori", list_kat, index=idx)
        jumlah = st.number_input("Jumlah (Rp)", min_value=0, step=5000, key=f"jumlah_{st.session_state.form_key}")
        
        if st.button("💾 Simpan Data Manual", use_container_width=True):
            if jumlah > 0:
                data_baru = pd.DataFrame({'Tanggal': [pd.to_datetime(tanggal)],'Tipe': [tipe],'Kategori': [kategori],'Jumlah': [jumlah],'Keterangan': [keterangan]})
                df = pd.concat([df, data_baru], ignore_index=True)
                save_data(df)
                st.session_state.form_key += 1
                st.success("✅ Tersimpan!")
                st.rerun()
                
    st.markdown("---")
    
    st.subheader("📋 Riwayat Transaksi")
    if not df.empty:
        pilihan_tipe = st.multiselect("Filter Jenis:", options=["Pemasukan", "Pengeluaran"], default=["Pemasukan", "Pengeluaran"])
        
        df_tampil = df[df['Tipe'].isin(pilihan_tipe)].sort_values(by='Tanggal', ascending=False)
        df_tampil = df_tampil[['Tanggal', 'Tipe', 'Kategori', 'Jumlah', 'Keterangan']].copy()
        
        df_tampil['Jumlah'] = df_tampil['Jumlah'].apply(lambda x: f"{int(x):,}".replace(",", "."))
        
        def color_jumlah(row):
            return ['color: #2ecc71'] * len(row) if row['Tipe'] == 'Pemasukan' else ['color: #e74c3c'] * len(row)
            
        st.dataframe(
            df_tampil.style.apply(color_jumlah, axis=1).format({"Tanggal": lambda x: pd.to_datetime(x).strftime("%Y-%m-%d")}), 
            use_container_width=True, height=350, hide_index=True
        )
    else:
        st.markdown("<div style='text-align: center; color: gray;'>Belum ada riwayat transaksi.</div>", unsafe_allow_html=True)

# ==========================================
# MENU 2: ANALISIS BULANAN 
# ==========================================
elif menu == "📈 Analyze":
    st.title("Visualisasi & Analisis Bulanan")
    if df.empty:
        st.warning("Belum ada data.")
    else:
        df['Bulan_Tahun'] = df['Tanggal'].dt.to_period('M')
        list_bulan_str = [str(b) for b in sorted(df['Bulan_Tahun'].unique(), reverse=True)]
        
        col_opt1, col_opt2, col_opt3 = st.columns([1, 1.5, 1.5])
        with col_opt1:
            bulan_pilihan = st.selectbox("Pilih Periode", list_bulan_str)
        df_bulanan = df[df['Bulan_Tahun'] == bulan_pilihan]
        
        in_bln = df_bulanan[df_bulanan['Tipe'] == 'Pemasukan']['Jumlah'].sum()
        out_bln = df_bulanan[df_bulanan['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
        sisa_saldo = in_bln - out_bln
        
        with col_opt2:
            st.markdown("<br>", unsafe_allow_html=True)
            csv = df_bulanan.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Ekspor CSV", data=csv, file_name=f"Data_{bulan_pilihan}.csv", mime="text/csv", use_container_width=True)
            
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
                
                tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                pdf.output(tmp_file.name)
                with open(tmp_file.name, "rb") as f: pdf_bytes = f.read()
                st.download_button("📄 Ekspor PDF", data=pdf_bytes, file_name=f"Laporan_{bulan_pilihan}.pdf", mime="application/pdf", use_container_width=True)
            else:
                st.button("📄 PDF (Perlu 'fpdf')", disabled=True, use_container_width=True)

        st.markdown("---")
        
        st.subheader("Sankey Diagram")
        df_keluar = df_bulanan[df_bulanan['Tipe'] == 'Pengeluaran'].groupby('Kategori')['Jumlah'].sum().reset_index()
        label_node = ["Pemasukan Bulanan"] + df_keluar['Kategori'].tolist() + ["Sisa Saldo"]
        sumber = [0] * (len(df_keluar) + 1)
        tujuan = list(range(1, len(label_node)))
        nilai = df_keluar['Jumlah'].tolist() + [max(0, sisa_saldo)]
        
        if sisa_saldo < 0: label_node.pop(); sumber.pop(); tujuan.pop(); nilai.pop()

        if in_bln > 0 or out_bln > 0:
            fig_sankey = go.Figure(data=[go.Sankey(
                node = dict(pad=15, thickness=20, line=dict(color="black", width=0.5), label=label_node, color=["#3498db"] + ["#e74c3c"] * len(df_keluar) + ["#2ecc71"]),
                link = dict(source=sumber, target=tujuan, value=nilai, color="rgba(189, 195, 199, 0.4)")
            )])
            st.plotly_chart(fig_sankey, use_container_width=True, theme="streamlit")
            
        st.markdown("---")

        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.subheader("Cash Flow")
            df_tren = df_bulanan.groupby(['Tanggal', 'Tipe'])['Jumlah'].sum().reset_index()
            fig_bar = px.bar(df_tren, x='Tanggal', y='Jumlah', color='Tipe', color_discrete_map={"Pemasukan": "#3498db", "Pengeluaran": "#e74c3c"})
            st.plotly_chart(fig_bar, use_container_width=True, theme="streamlit")
            
        with col_c2:
            st.subheader("Distribusi Pengeluaran")
            if not df_keluar.empty:
                fig_pie = px.pie(df_keluar, values='Jumlah', names='Kategori', hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                st.plotly_chart(fig_pie, use_container_width=True, theme="streamlit")

        st.markdown("---")
        
        st.subheader("🤖 Segmentasi Gaya Hidup (K-Means)")
        df_peng_hari = df_bulanan[df_bulanan['Tipe']=='Pengeluaran'].groupby(df_bulanan['Tanggal'].dt.date)['Jumlah'].sum().reset_index()
        if len(df_peng_hari) >= 5: 
            X = df_peng_hari[['Jumlah']].values
            kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
            df_peng_hari['Cluster'] = kmeans.fit_predict(X)
            
            pusat = kmeans.cluster_centers_.flatten()
            urutan = np.argsort(pusat)
            label_map = {urutan[0]: "Hemat", urutan[1]: "Normal", urutan[2]: "Boros"}
            df_peng_hari['Gaya Hidup'] = df_peng_hari['Cluster'].map(label_map)
            
            fig_cluster = px.scatter(df_peng_hari, x='Tanggal', y='Jumlah', color='Gaya Hidup', size='Jumlah', color_discrete_map={"Hemat":"#2ecc71", "Normal":"#3498db", "Boros":"#e74c3c"})
            st.plotly_chart(fig_cluster, use_container_width=True, theme="streamlit")
        else:
            st.info("Butuh minimal 5 hari transaksi untuk mengaktifkan AI Clustering.")

# ==========================================
# MENU 3: ADVANCED PREDICT & STATS
# ==========================================
elif menu == "🔮 Advanced Stats & Predict":
    st.title("Statistika Lanjut & Prediksi")
    if df.empty:
        st.warning("⚠️ Belum ada data transaksi.")
    else:
        df_pengeluaran = df[df['Tipe'] == 'Pengeluaran'].copy()
        
        if len(df_pengeluaran['Tanggal'].unique()) < 7:
            st.warning("⚠️ Butuh data pengeluaran 7 hari berbeda.")
        else:
            df_ts = df_pengeluaran.groupby('Tanggal')['Jumlah'].sum().reset_index().set_index('Tanggal').asfreq('D', fill_value=0)
            
            tab1, tab2, tab3, tab4 = st.tabs(["📈 ARIMA Model", "🎲 Monte Carlo", "📊 Uji Asumsi (ADF)"])
            
            with tab1:
                st.subheader("Proyeksi Tren (ARIMA)")
                try:
                    model = ARIMA(df_ts['Jumlah'], order=(1, 1, 1))
                    model_fit = model.fit()
                    prediksi_obj = model_fit.get_forecast(steps=7)
                    forecast_mean = prediksi_obj.predicted_mean.apply(lambda x: max(0, x))
                    tanggal_fc = pd.date_range(start=df_ts.index[-1] + pd.Timedelta(days=1), periods=7)
                    
                    fig_fc = go.Figure()
                    fig_fc.add_trace(go.Scatter(x=df_ts.tail(20).index, y=df_ts.tail(20)['Jumlah'], name='Aktual', line=dict(color='#3498db', width=3)))
                    fig_fc.add_trace(go.Scatter(x=tanggal_fc, y=forecast_mean, name='Prediksi', line=dict(color='#e74c3c', dash='dot', width=3)))
                    st.plotly_chart(fig_fc, use_container_width=True, theme="streamlit")
                except:
                    st.error("Model ARIMA gagal berkonvergensi.")

            with tab2:
                st.subheader("🧠 Model Hybrid ARIMA-LSTM")
                st.write("Menggabungkan kemampuan prediksi linear (ARIMA) dengan pengenalan pola non-linear (LSTM) pada residual data.")
                
                if st.button("🚀 Jalankan Kalkulasi Hybrid (Komputasi Berat)", use_container_width=True):
                    with st.spinner("Memuat TensorFlow dan memproses Jaringan Saraf Tiruan..."):
                        try:
                            from tensorflow.keras.models import Sequential
                            from tensorflow.keras.layers import LSTM, Dense
                            from sklearn.preprocessing import MinMaxScaler
                            
                            model_arima = ARIMA(df_ts['Jumlah'], order=(1, 1, 1))
                            model_arima_fit = model_arima.fit()
                            
                            residuals = model_arima_fit.resid.values.reshape(-1, 1)
                            
                            scaler = MinMaxScaler(feature_range=(-1, 1))
                            resid_scaled = scaler.fit_transform(residuals)
                            
                            def create_dataset(dataset, look_back=3):
                                X, Y = [], []
                                for i in range(len(dataset)-look_back-1):
                                    a = dataset[i:(i+look_back), 0]
                                    X.append(a)
                                    Y.append(dataset[i + look_back, 0])
                                return np.array(X), np.array(Y)
                                
                            look_back = 3
                            X, Y = create_dataset(resid_scaled, look_back)
                            
                            if len(X) == 0:
                                st.error("Data historis terlalu sedikit untuk melatih LSTM. Tambahkan lebih banyak data pengeluaran.")
                            else:
                                X = np.reshape(X, (X.shape[0], 1, X.shape[1]))
                                
                                lstm_model = Sequential()
                                lstm_model.add(LSTM(50, input_shape=(1, look_back)))
                                lstm_model.add(Dense(1))
                                lstm_model.compile(loss='mean_squared_error', optimizer='adam')
                                lstm_model.fit(X, Y, epochs=20, batch_size=1, verbose=0)
                                
                                langkah_prediksi = 7
                                arima_forecast = model_arima_fit.forecast(steps=langkah_prediksi).values
                                
                                input_seq = resid_scaled[-look_back:].reshape(1, 1, look_back)
                                lstm_pred_scaled = []
                                for _ in range(langkah_prediksi):
                                    pred = lstm_model.predict(input_seq, verbose=0)
                                    lstm_pred_scaled.append(pred[0,0])
                                    input_seq = np.append(input_seq[:, :, 1:], pred).reshape(1, 1, look_back)
                                    
                                lstm_pred = scaler.inverse_transform(np.array(lstm_pred_scaled).reshape(-1, 1)).flatten()
                                
                                hybrid_forecast = arima_forecast + lstm_pred
                                hybrid_forecast = np.maximum(hybrid_forecast, 0)
                                
                                tanggal_fc = pd.date_range(start=df_ts.index[-1] + pd.Timedelta(days=1), periods=langkah_prediksi)
                                fig_hybrid = go.Figure()
                                fig_hybrid.add_trace(go.Scatter(x=df_ts.tail(20).index, y=df_ts.tail(20)['Jumlah'], name='Data Aktual', line=dict(color='#3498db', width=3)))
                                fig_hybrid.add_trace(go.Scatter(x=tanggal_fc, y=hybrid_forecast, name='Prediksi Hybrid (ARIMA+LSTM)', line=dict(color='#9b59b6', dash='dash', width=3)))
                                
                                st.plotly_chart(fig_hybrid, use_container_width=True, theme="streamlit")
                                st.success("✅ Pemodelan Hybrid ARIMA-LSTM Berhasil Dieksekusi!")
                                
                        except ImportError:
                            st.error("⚠️ Library `tensorflow` atau `scikit-learn` belum terinstal. Tambahkan di requirements.txt!")
                        except Exception as e:
                            st.error(f"Gagal memproses LSTM: {e}")

            with tab3:
                st.subheader("🎲 Monte Carlo (100 Skenario)")
                mean_p = df_ts['Jumlah'].mean(); std_p = df_ts['Jumlah'].std()
                simulasi = np.zeros((30, 100))
                for i in range(100):
                    rw = np.maximum(np.random.normal(loc=mean_p, scale=std_p, size=30), 0)
                    simulasi[:, i] = np.cumsum(rw)
                    
                fig_mc = go.Figure()
                for i in range(100):
                    fig_mc.add_trace(go.Scatter(y=simulasi[:, i], mode='lines', line=dict(color='rgba(52, 152, 219, 0.1)'), showlegend=False))
                st.plotly_chart(fig_mc, use_container_width=True, theme="streamlit")
                st.caption(f"Estimasi puncak pengeluaran 30 hari ke depan: Rp {np.percentile(simulasi[-1, :], 95):,.0f}")

            with tab4:
                st.subheader("Analisis Diagnostik Runtun Waktu (Time-Series)")
                st.write("Pengujian akar unit (Unit Root Test) untuk memastikan data pengeluaran memenuhi asumsi stasioneritas sebelum pemodelan lanjutan.")
                hasil = adfuller(df_ts['Jumlah'].values)
                st.code(f"ADF Statistic: {hasil[0]:.4f}\np-value: {hasil[1]:.4f}\nCrit Value 5%: {hasil[4]['5%']:.4f}")
                if hasil[1] < 0.05: st.success("Data stasioner (Tolak H0).")
                else: st.error("Data tidak stasioner. Lakukan differencing.")

# ==========================================
# FITUR CHAT BUBBLE AI
# ==========================================
with st.popover("💬", use_container_width=False):
    st.markdown("<h4 style='text-align: center;'>AI Advisor</h4>", unsafe_allow_html=True)
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = [{"role": "assistant", "content": "Halo! Aku AI Advisor Kamu, Ada yang bisa dibantu?"}]

    chat_container = st.container(height=300)
    with chat_container:
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]): 
                st.markdown(msg["content"])
                if "image" in msg and msg["image"] is not None:
                    st.image(msg["image"], width=200)

    with st.popover("➕ Upload Foto", use_container_width=True):
        uploaded_img = st.file_uploader("", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
        if uploaded_img:
            st.success("Foto siap dikirim!")

    user_msg = st.chat_input("Ketik pesan...")

    if user_msg:
        waktu_wib_chat = pd.Timestamp.utcnow() + pd.Timedelta(hours=7)
        bulan_ini_chat = waktu_wib_chat.to_period('M')
        
        if not df.empty:
            df_chat = df.copy()
            df_chat['Tanggal'] = pd.to_datetime(df_chat['Tanggal'])
            df_chat['Bulan_Tahun'] = df_chat['Tanggal'].dt.to_period('M')
            df_bulan_ini = df_chat[df_chat['Bulan_Tahun'] == bulan_ini_chat]
            
            in_bln = df_bulan_ini[df_bulan_ini['Tipe'] == 'Pemasukan']['Jumlah'].sum()
            out_bln = df_bulan_ini[df_bulan_ini['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
            sisa_bln = in_bln - out_bln
            saldo_total = df_chat[df_chat['Tipe'] == 'Pemasukan']['Jumlah'].sum() - df_chat[df_chat['Tipe'] == 'Pengeluaran']['Jumlah'].sum()
        else:
            in_bln = out_bln = sisa_bln = saldo_total = 0
        
        tz_jakarta = pytz.timezone('Asia/Jakarta')
        waktu_sekarang_chat = datetime.now(tz_jakarta)
        teks_waktu = waktu_sekarang_chat.strftime("%A, %d %B %Y, jam %H:%M WIB")
        
        user_entry = {"role": "user", "content": user_msg}
        
        import PIL.Image
        img_obj = None
        if uploaded_img:
            img_obj = PIL.Image.open(uploaded_img)
            user_entry["image"] = img_obj
            
        st.session_state.chat_history.append(user_entry)
        
        with chat_container:
            with st.chat_message("user"):
                st.markdown(user_msg)
                if img_obj:
                    st.image(img_obj, width=200)
                    
        try:
            genai.configure(api_key=st.secrets["Gemini_API_Key"])
            model_ai = genai.GenerativeModel('gemini-3.1-flash-lite')
            
            profil_pribadi = st.secrets.get("USER_BIO", "Pengguna aplikasi ini")
            
            instruksi_sistem = f"""Kamu adalah Dimas, asisten AI finansial dan teman ngobrol yang asik.
            Profil Pengguna: {profil_pribadi}
            
            INFORMASI WAKTU SAAT INI (PENTING):
            Sekarang adalah {teks_waktu}. Gunakan acuan ini secara akurat jika pengguna menanyakan jam, hari, atau tanggal.
            
            DATA FINANSIAL REAL-TIME DASHBOARD BULAN INI ({bulan_ini_chat}):
            - Total Pemasukan Bulan Ini: Rp {in_bln:,.0f}
            - Total Pengeluaran Bulan Ini: Rp {out_bln:,.0f}
            - Sisa Saldo Bulan Ini: Rp {sisa_bln:,.0f}
            - Saldo Akhir Aktual (Keseluruhan): Rp {saldo_total:,.0f}
            
            Aturan Ketat Merespons:
            1. Jika user hanya menyapa (seperti 'Halo', 'Pagi', 'Test'), balas dengan santai dan akrab TANPA menjabarkan angka-angka keuangan di atas.
            2. Jika user hanya bertanya tentang keuangannya, sisa saldo, kondisi dompet, pengeluaran, atau analisis boros/tidaknya, gunakan data angka riil di atas untuk memberikan jawaban analitis yang cerdas, solutif, dan objektif.
            3. jika user bertanya dengan pertanyaan diluar keuangan tolong dijawab sesuai konteks pertanyaannya dengan cermat.
            """
            
            prompt_parts = [instruksi_sistem, f"Pesan Pengguna: {user_msg}"]
            if img_obj:
                prompt_parts.append(img_obj)
                
            response = model_ai.generate_content(prompt_parts)
            
            st.session_state.chat_history.append({"role": "assistant", "content": response.text})
            st.rerun()
        except Exception as e:
            st.error(f"Gagal memuat AI. Pastikan API valid. Error: {e}")

import streamlit as st
import pandas as pd
import json
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import streamlit.components.v1 as components
from plotly.subplots import make_subplots
from datetime import datetime

st.set_page_config(page_title="Katılım Endeksi Panelim", layout="wide")

# ------------------------------------------------------------------
# BIST Katılım 30 (XK030) evreni - 1 Mayıs 2026 duyurusuna göre.
# Endeks içeriği yılda 2 kez (Mayıs / Kasım) güncellenir.
# Yeni dönemde değişiklik olursa bu listeyi güncellemek yeterli.
# ------------------------------------------------------------------
KATILIM_TÜM = [
    "AAGYO", "ACSEL", "AHGAZ", "AHSGY", "AKFYE", "AKHAN", "ALBRK", "ALBTN", "ALCTL", "ALFAS", "ALKA", "ALKIM", "ALKLC", "ALTNY", "ALVES", "ANGEN", "ARASE", "ARDYZ", "ARENA", "ARFYE", "ASELS", "ATAKP", "ATATP", "AVPGY", "AYEN", "BAHKM", "BASGZ", "BAYRK", "BEGYO", "BERA", "BESTE", "BETAE", "BIENY", "BIMAS", "BINBN", "BINHO", "BMSTL", "BORSK", "BOSSA", "BRISA", "BRLSM", "BSOKE", "BUCIM", "BURCE", "BURVA", "BYDNR", "CANTE", "CATES", "CELHA", "CEMTS", "CEMZY", "CIMSA", "CMBTN", "CVKMD", "CWENE", "DAPGM", "DARDL", "DCTTR", "DENGE", "DGATE", "DITAS", "DMSAS", "DNISI", "DOFER", "DOFRB", "DOGUB", "DYOBY", "EBEBK", "EDATA", "EDIP", "EGEPO", "EGPRO", "EGGUB", "EKSUN", "EKGYO", "ELITE", "EMPAE", "ENJSA", "EREGL", "ESCOM", "EUPWR", "EYGYO", "FADE", "FONET", "FORMT", "FORTE", "FRMPL", "FZLGY", "GEDZA", "GENIL", "GENKM", "GENTS", "GEREL", "GESAN", "GOKNR", "GOLDA", "GOLTS", "GOODY", "GMTAS", "GRSEL", "GRTHO", "GUBRF", "GUNDG", "HATSN", "HKTM", "HOROZ", "HRKET", "IHEVA", "IHLAS", "IHLGM", "IHYAY", "IMASM", "INGRM", "INTEM", "ISDMR", "IZFAS", "IZINV", "JANTS", "KARSN", "KATMR", "KBORU", "KCAER", "KIMMR", "KLSER", "KLSYN", "KNFRT", "KOCMT", "KONKA", "KONYA", "KOPOL", "KOTON", "KRDMA", "KRDMB", "KRDMD", "KRONT", "KRPLS", "KRSTL", "KRVGD", "KTLEV", "KUTPO", "KZBGY", "LKMNH", "LOGO", "LXGYO", "MAGEN", "MAKIM", "MARBL", "MAVI", "MCARD", "MEDTR", "MEGMT", "MEKAG", "MERCN", "MERKO", "MEYSU", "MNDTR", "MOBTL", "MOPAS", "MPARK", "NETAS", "NETCD", "NTGAZ", "OBASE", "OBAMS", "ONCSM", "ORGE", "OSTIM", "OZATD", "OZGYO", "OZRDN", "OZYSR", "PAGYO", "PARSN", "PASEU", "PENGD", "PENTA", "PETKM", "PKART", "PLTUR", "PNSUT", "POLHO", "PRKME", "QUAGR", "QUICK", "RALYH", "RGYAS", "RNPOL", "RUBNS", "SAFKR", "SAMAT", "SANEL", "SARKY", "SAYAS", "SDTTR", "SELEC", "SEKUR", "SELVA", "SMART", "SMRVA", "SNGYO", "SNICA", "SOHOE", "SOKE", "SRVGY", "SSAAT", "SUNTK", "SURGY", "SUWEN", "SVGYO", "TARKM", "TERA", "TEZOL", "THYAO", "TKFEN", "TKNSA", "TMPOL", "TUCLK", "TUKAS", "TUPRS", "TUREX", "TURGG", "UCAYM", "UFUK", "ULAS", "ULUSE", "USAK", "VAKKO", "VANGD", "YATAS", "YEOTK", "YIGIT", "YUNSA", "ZERGY"
]

MA_PERIODS = [21, 55, 144]  # Fibonacci bazlı hareketli ortalamalar


@st.cache_data(ttl=900, show_spinner=False)
def get_history(ticker: str, period: str = "2y") -> pd.DataFrame:
    """Tek bir hisse için günlük OHLCV verisi çeker (.IS uzantılı BIST sembolü)."""
    df = yf.Ticker(f"{ticker}.IS").history(period=period, interval="1d", auto_adjust=False)
    return df


@st.cache_data(ttl=900, show_spinner=False)
def get_top_movers(universe: list[str], n: int = 10 , lookback: int = 5) -> pd.DataFrame:
    """Evrendeki hisseleri son 'lookback' işlem günündeki YÜZDE DEĞİŞİMİNE göre sıralar (mutlak değer,
    hem en çok yükselen hem en çok düşen dahil), ilk n'i döner."""
    rows = []
    for t in universe:
        try:
            df = get_history(t, period="1mo")
            if df.empty or len(df) < 2:
                continue
            if len(df) < lookback + 1:
                base_close = df["Close"].iloc[0]
                base_date = df.index[0].date()
            else:
                base_close = df["Close"].iloc[-(lookback + 1)]
                base_date = df.index[-(lookback + 1)].date()
            last = df.iloc[-1]
            pct = (last["Close"] - base_close) / base_close * 100
            rows.append({
                "Sembol": t,
                "Son Fiyat": last["Close"],
                "Değişim %": pct,
                "Hacim (adet)": last["Volume"],
                "Baz Tarih": base_date,
                "Tarih": df.index[-1].date(),
            })
        except Exception:
            continue
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows)
    out["_abs"] = out["Değişim %"].abs()
    out = out.sort_values("_abs", ascending=False).drop(columns="_abs").reset_index(drop=True)
    return out.head(n)

def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for p in MA_PERIODS:
        df[f"MA{p}"] = df["Close"].rolling(p).mean()

    ema13 = df["Close"].ewm(span=13, adjust=False).mean()
    ema21 = df["Close"].ewm(span=21, adjust=False).mean()
    df["MACD"] = ema13 - ema21
    df["Signal"] = df["MACD"].ewm(span=8, adjust=False).mean()
    df["Hist"] = df["MACD"] - df["Signal"]
    return df

def render_chart(ticker: str, df: pd.DataFrame, revision: int = 0, height: int = 650):
    """Mum grafiği + MA + MACD'yi düz Python listeleriyle çizer, autoscale destekler."""

    def col(name):
        s = df[name].round(4)
        return [None if pd.isna(v) else float(v) for v in s]

    payload = {
        "dates": df.index.strftime("%Y-%m-%d").tolist(),
        "open": col("Open"), "high": col("High"),
        "low": col("Low"), "close": col("Close"),
        "ma21": col("MA21"), "ma55": col("MA55"), "ma144": col("MA144"),
        "macd": col("MACD"), "signal": col("Signal"), "hist": col("Hist"),
    }
    payload_json = json.dumps(payload)

    html = f"""
    <div id="chart-{ticker}" style="width:100%; background:#0e1117;"></div>
    <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
    <script>
    (function() {{
        var d = {payload_json};
        var chartDiv = document.getElementById('chart-{ticker}');
        // Hafta sonu ve tatil gibi işlem olmayan günleri tespit edip boşlukları kapatıyoruz
        var haveDates = {{}};
        d.dates.forEach(function(ds) {{ haveDates[ds] = true; }});
        var missingDates = [];
        if (d.dates.length > 1) {{
            var cur = new Date(d.dates[0]);
            var last = new Date(d.dates[d.dates.length - 1]);
            while (cur <= last) {{
                var ds = cur.toISOString().split('T')[0];
                var day = cur.getUTCDay(); // 0=pazar, 6=cumartesi
                if (day !== 0 && day !== 6 && !haveDates[ds]) {{
                    missingDates.push(ds);
                }}
                cur.setUTCDate(cur.getUTCDate() + 1);
            }}
        }}

        var candle = {{
            type: 'candlestick', name: 'Fiyat',
            x: d.dates, open: d.open, high: d.high, low: d.low, close: d.close,
            increasing: {{line: {{color: '#26a69a'}}}},
            decreasing: {{line: {{color: '#ef5350'}}}},
            xaxis: 'x', yaxis: 'y',
        }};
        var ma21 = {{type: 'scatter', mode: 'lines', name: 'MA21', x: d.dates, y: d.ma21,
                     line: {{width: 1.5, color: '#f5a623'}}, xaxis: 'x', yaxis: 'y'}};
        var ma55 = {{type: 'scatter', mode: 'lines', name: 'MA55', x: d.dates, y: d.ma55,
                     line: {{width: 1.5, color: '#4a90d9'}}, xaxis: 'x', yaxis: 'y'}};
        var ma144 = {{type: 'scatter', mode: 'lines', name: 'MA144', x: d.dates, y: d.ma144,
                      line: {{width: 1.5, color: '#b06fd6'}}, xaxis: 'x', yaxis: 'y'}};

        var histColors = d.hist.map(function(v, i) {{
            if (v === null || v === undefined) return 'rgba(0,0,0,0)';
            var prev = i > 0 ? d.hist[i - 1] : null;
            if (v >= 0) {{
                return (prev !== null && v < prev) ? '#a5d6cf' : '#26a69a';
            }} else {{
                return (prev !== null && v > prev) ? '#f7b8b5' : '#ef5350';
            }}
        }});
        var histBar = {{type: 'bar', name: 'Histogram', x: d.dates, y: d.hist,
                        marker: {{color: histColors, opacity: 0.6}}, xaxis: 'x', yaxis: 'y2'}};
        var macdLine = {{type: 'scatter', mode: 'lines', name: 'MACD', x: d.dates, y: d.macd,
                         line: {{width: 1.3, color: '#2962ff'}}, xaxis: 'x', yaxis: 'y2'}};
        var signalLine = {{type: 'scatter', mode: 'lines', name: 'Sinyal', x: d.dates, y: d.signal,
                           line: {{width: 1.3, color: '#ff6d00'}}, xaxis: 'x', yaxis: 'y2'}};

        var layout = {{
            height: {height},
            paper_bgcolor: '#0e1117', plot_bgcolor: '#0e1117',
            font: {{color: '#e0e0e0'}},
            margin: {{l: 50, r: 50, t: 30, b: 30}},
            dragmode: 'pan',
            uirevision: '{revision}',
            showlegend: true,
            legend: {{orientation: 'h', y: 1.05, x: 1, xanchor: 'right'}},
            grid: {{rows: 2, columns: 1, pattern: 'independent'}},
          xaxis: {{
                domain: [0, 1], anchor: 'y', gridcolor: '#2a2e39', rangeslider: {{visible: false}},
                rangebreaks: [{{bounds: ['sat', 'mon']}}, {{values: missingDates}}],
            }},
            yaxis: {{domain: [0.32, 1], anchor: 'x', gridcolor: '#2a2e39', title: '{ticker}'}},
            yaxis2: {{domain: [0, 0.25], anchor: 'x', gridcolor: '#2a2e39', title: 'MACD'}},
        }};

        Plotly.newPlot(chartDiv, [candle, ma21, ma55, ma144, histBar, macdLine, signalLine], layout,
            {{responsive: true, scrollZoom: true, displaylogo: false}});

        function autoscaleY(eventdata) {{
            var xr = null;
            if (eventdata['xaxis.range[0]'] !== undefined) {{
                xr = [new Date(eventdata['xaxis.range[0]']).getTime(),
                      new Date(eventdata['xaxis.range[1]']).getTime()];
            }} else if (eventdata['xaxis.autorange']) {{
                Plotly.relayout(chartDiv, {{'yaxis.autorange': true, 'yaxis2.autorange': true}});
                return;
            }} else {{
                return;
            }}

            var xs = d.dates.map(function(s) {{ return new Date(s).getTime(); }});
            var yMin = Infinity, yMax = -Infinity;
            var mMin = Infinity, mMax = -Infinity;

            for (var i = 0; i < xs.length; i++) {{
                if (xs[i] < xr[0] || xs[i] > xr[1]) continue;
                [d.high[i], d.low[i], d.ma21[i], d.ma55[i], d.ma144[i]].forEach(function(v) {{
                    if (v === null || v === undefined || isNaN(v)) return;
                    if (v < yMin) yMin = v;
                    if (v > yMax) yMax = v;
                }});
                [d.macd[i], d.signal[i], d.hist[i]].forEach(function(v) {{
                    if (v === null || v === undefined || isNaN(v)) return;
                    if (v < mMin) mMin = v;
                    if (v > mMax) mMax = v;
                }});
            }}

            var update = {{}};
            if (isFinite(yMin) && isFinite(yMax)) {{
                var pad = (yMax - yMin) * 0.08 || 1;
                update['yaxis.range'] = [yMin - pad, yMax + pad];
            }}
            if (isFinite(mMin) && isFinite(mMax)) {{
                var pad2 = (mMax - mMin) * 0.1 || 1;
                update['yaxis2.range'] = [mMin - pad2, mMax + pad2];
            }}
            if (Object.keys(update).length) Plotly.relayout(chartDiv, update);
        }}

        chartDiv.on('plotly_relayout', autoscaleY);
    }})();
    </script>
    """
    components.html(html, height=height + 20)

# ------------------------------------------------------------------
# ARAYÜZ
# ------------------------------------------------------------------
st.title("📊 Katılım Endeksi Panelim")
st.caption(
    "BIST Katılım Tüm evreni içinden günün en çok değişen 10 hissesi · "
    "MACD (13,21,8) · Hareketli Ortalama 21 / 55 / 144"
)

col_a, col_b = st.columns([1, 5])
with col_a:
    if st.button("🔄 Verileri yenile"):
        st.cache_data.clear()

with st.spinner("Veriler çekiliyor..."):
    top10_katilim = get_top_movers(KATILIM_TÜM, n=10)

if top10_katilim.empty:
    st.error(
        "Veri çekilemedi. Yahoo Finance şu an erişilemiyor olabilir, "
        "birkaç dakika sonra tekrar deneyin."
    )
    st.stop()

st.subheader("Son 5 işlem gününde en çok değişen 10 Katılım hissesi")
show = top10_katilim.copy()
show["Son Fiyat"] = show["Son Fiyat"].map(lambda x: f"{x:,.2f} TL")
show["Değişim %"] = show["Değişim %"].map(lambda x: f"{x:+,.2f}%")
show["Hacim (adet)"] = show["Hacim (adet)"].map(lambda x: f"{x:,.0f}")
st.dataframe(show, use_container_width=True, hide_index=True)

st.divider()

tabs = st.tabs(top10_katilim["Sembol"].tolist())
for tab, ticker in zip(tabs, top10_katilim["Sembol"].tolist()):
    with tab:
        with st.spinner(f"{ticker} verisi hazırlanıyor..."):
            hist = get_history(ticker, period="2y")
            if hist.empty:
                st.warning("Bu hisse için veri bulunamadı.")
                continue
            hist = compute_indicators(hist)

            rev_key = f"revision_{ticker}"
            if rev_key not in st.session_state:
                st.session_state[rev_key] = 0

            if st.button("🔍 Zoom'u sıfırla", key=f"reset_{ticker}"):
                st.session_state[rev_key] += 1

            render_chart(ticker, hist, revision=st.session_state[rev_key], height=650)

            last_row = hist.iloc[-1]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Son Kapanış", f"{last_row['Close']:.2f} TL")
            c2.metric("MA21", f"{last_row['MA21']:.2f}" if not np.isnan(last_row['MA21']) else "-")
            c3.metric("MA55", f"{last_row['MA55']:.2f}" if not np.isnan(last_row['MA55']) else "-")
            c4.metric("MA144", f"{last_row['MA144']:.2f}" if not np.isnan(last_row['MA144']) else "-")

st.divider()
st.caption(
    f"Son güncelleme: {datetime.now().strftime('%d.%m.%Y %H:%M')} · "
    "Veri kaynağı: Yahoo Finance (yaklaşık 15-20 dk gecikmeli olabilir) · "
    "Bu panel yatırım tavsiyesi değildir."
)
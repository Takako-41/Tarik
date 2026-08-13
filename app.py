import streamlit as st
import pandas as pd
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
KATILIM_30 = [
    "AKSA", "ALTNY", "ASELS", "BSOKE", "BIMAS", "CWENE", "CANTE", "CIMSA",
    "DAPGM", "EKGYO", "ENJSA", "EREGL", "EUPWR", "GENIL", "GESAN", "GUBRF",
    "GLRMK", "GRSEL", "KRDMD", "KTLEV", "KONTR", "KUYAS", "MAVI", "MPARK",
    "OBAMS", "PASEU", "PETKM", "TUREX", "TUPRS", "YEOTK",
]

MA_PERIODS = [21, 55, 144]  # Fibonacci bazlı hareketli ortalamalar


@st.cache_data(ttl=900, show_spinner=False)
def get_history(ticker: str, period: str = "2y") -> pd.DataFrame:
    """Tek bir hisse için günlük OHLCV verisi çeker (.IS uzantılı BIST sembolü)."""
    df = yf.Ticker(f"{ticker}.IS").history(period=period, interval="1d")
    return df


@st.cache_data(ttl=900, show_spinner=False)
def get_top5_by_volume(universe: list[str]) -> pd.DataFrame:
    """Evrendeki hisseleri son günün TL işlem hacmine göre sıralar, ilk 5'i döner."""
    rows = []
    for t in universe:
        try:
            df = get_history(t, period="5d")
            if df.empty:
                continue
            last = df.iloc[-1]
            tl_hacim = last["Close"] * last["Volume"]
            rows.append({
                "Sembol": t,
                "Son Fiyat": last["Close"],
                "Hacim (adet)": last["Volume"],
                "TL Hacim": tl_hacim,
                "Tarih": df.index[-1].date(),
            })
        except Exception:
            continue
    if not rows:
        return pd.DataFrame()
    out = pd.DataFrame(rows).sort_values("TL Hacim", ascending=False).reset_index(drop=True)
    return out.head(5)

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


def plot_stock(ticker: str, df: pd.DataFrame , revision: int = 0):
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.7, 0.3], vertical_spacing=0.04,
        subplot_titles=(f"{ticker} - Fiyat & Hareketli Ortalamalar", "MACD"),
    )

    fig.add_trace(go.Candlestick(
        x=df.index, open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="Fiyat",
        increasing_line_color="#26a69a", decreasing_line_color="#ef5350",
    ), row=1, col=1)

    colors = {"MA21": "#f5a623", "MA55": "#4a90d9", "MA144": "#b06fd6"}
    for p in MA_PERIODS:
        col = f"MA{p}"
        fig.add_trace(go.Scatter(
            x=df.index, y=df[col], name=col, mode="lines",
            line=dict(width=1.5, color=colors.get(col)),
        ), row=1, col=1)

    hist_colors = np.where(df["Hist"] >= 0, "#26a69a", "#ef5350")
    fig.add_trace(go.Bar(
        x=df.index, y=df["Hist"], name="Histogram",
        marker_color=hist_colors, opacity=0.6,
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD"], name="MACD", mode="lines",
        line=dict(width=1.3, color="#2962ff"),
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Signal"], name="Sinyal", mode="lines",
        line=dict(width=1.3, color="#ff6d00"),
    ), row=2, col=1)

    fig.update_layout(
        height=650, xaxis_rangeslider_visible=False,
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_white",
        dragmode="pan",
        uirevision=str(revision),
    )
    return fig

def render_autoscale_chart(fig, height=650):
    fig_json = fig.to_json()
    html = f"""
    <div id="chart-div" style="width:100%;"></div>
    <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
    <script>
    var figure = {fig_json};
    var chartDiv = document.getElementById('chart-div');
    Plotly.newPlot(chartDiv, figure.data, figure.layout,
        {{responsive: true, scrollZoom: true, displaylogo: false}});
        
function autoscaleY(eventdata) {{
        var xrange = null;
        if (eventdata['xaxis.range[0]'] !== undefined && eventdata['xaxis.range[1]'] !== undefined) {{
            xrange = [new Date(eventdata['xaxis.range[0]']).getTime(),
                      new Date(eventdata['xaxis.range[1]']).getTime()];
        }} else if (eventdata['xaxis2.range[0]'] !== undefined && eventdata['xaxis2.range[1]'] !== undefined) {{
            xrange = [new Date(eventdata['xaxis2.range[0]']).getTime(),
                      new Date(eventdata['xaxis2.range[1]']).getTime()];
        }} else if (eventdata['xaxis.autorange'] || eventdata['xaxis2.autorange']) {{
            Plotly.relayout(chartDiv, {{'yaxis.autorange': true, 'yaxis2.autorange': true}});
            return;
        }} else {{
            return;
        }}

        var yaxes = {{'y': {{min: Infinity, max: -Infinity}}, 'y2': {{min: Infinity, max: -Infinity}}}};

        chartDiv.data.forEach(function(trace) {{
            var axisKey = trace.yaxis === 'y2' ? 'y2' : 'y';
            var xs = trace.x.map(function(d) {{ return new Date(d).getTime(); }});
            for (var i = 0; i < xs.length; i++) {{
                if (xs[i] >= xrange[0] && xs[i] <= xrange[1]) {{
                    var vals = [];
                    if (trace.type === 'candlestick') {{
                        vals = [trace.high[i], trace.low[i]];
                    }} else if (trace.y) {{
                        vals = [trace.y[i]];
                    }}
                    vals.forEach(function(v) {{
                        if (v === null || v === undefined || isNaN(v)) return;
                        if (v < yaxes[axisKey].min) yaxes[axisKey].min = v;
                        if (v > yaxes[axisKey].max) yaxes[axisKey].max = v;
                    }});
                }}
            }}
        }});

        var update = {{}};
        if (isFinite(yaxes['y'].min) && isFinite(yaxes['y'].max)) {{
            var pad = (yaxes['y'].max - yaxes['y'].min) * 0.08;
            update['yaxis.range'] = [yaxes['y'].min - pad, yaxes['y'].max + pad];
        }}
        if (isFinite(yaxes['y2'].min) && isFinite(yaxes['y2'].max)) {{
            var pad2 = (yaxes['y2'].max - yaxes['y2'].min) * 0.1;
            update['yaxis2.range'] = [yaxes['y2'].min - pad2, yaxes['y2'].max + pad2];
        }}
        if (Object.keys(update).length > 0) {{
            Plotly.relayout(chartDiv, update);
        }}
    }}

    chartDiv.on('plotly_relayout', autoscaleY);
    </script>
    """
    components.html(html, height=height + 20)

# ------------------------------------------------------------------
# ARAYÜZ
# ------------------------------------------------------------------
st.title("📊 Katılım Endeksi Panelim")
st.caption(
    "BIST Katılım 30 evreni içinden günün en yüksek TL hacimli 5 hissesi · "
    "MACD (13,21,8) · Hareketli Ortalama 21 / 55 / 144"
)

col_a, col_b = st.columns([1, 5])
with col_a:
    if st.button("🔄 Verileri yenile"):
        st.cache_data.clear()

with st.spinner("Hacim verileri çekiliyor..."):
    top5 = get_top5_by_volume(KATILIM_30)

if top5.empty:
    st.error(
        "Veri çekilemedi. Yahoo Finance şu an erişilemiyor olabilir, "
        "birkaç dakika sonra tekrar deneyin."
    )
    st.stop()

st.subheader("Bugünün en yüksek hacimli 5 hissesi (Katılım 30 içinden)")
show = top5.copy()
show["Son Fiyat"] = show["Son Fiyat"].map(lambda x: f"{x:,.2f} TL")
show["Hacim (adet)"] = show["Hacim (adet)"].map(lambda x: f"{x:,.0f}")
show["TL Hacim"] = show["TL Hacim"].map(lambda x: f"{x:,.0f} TL")
st.dataframe(show, use_container_width=True, hide_index=True)

st.divider()

tabs = st.tabs(top5["Sembol"].tolist())
for tab, ticker in zip(tabs, top5["Sembol"].tolist()):
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

            fig = plot_stock(ticker, hist, revision=st.session_state[rev_key])
            render_autoscale_chart(fig, height=650)
            
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

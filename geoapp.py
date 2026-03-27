import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.spatial import ConvexHull

# --------------------------------------------------
# Configuração da página
# --------------------------------------------------
st.set_page_config(
    page_title="Mapa de Lojas por Coordenador",
    layout="wide"
)

st.title("🗺️ Mapa de Lojas por Coordenador")

# --------------------------------------------------
# Carregar dados
# --------------------------------------------------
@st.cache_data
def load_data():
    return pd.read_csv("geodata.csv")

df_agg = load_data()

# 🔥 Padronizar nomes de colunas (evita KeyError)
df_agg.columns = df_agg.columns.str.strip().str.upper()

# 🔥 Garantir lat/long numéricos
df_agg['LATITUDE'] = pd.to_numeric(df_agg['LATITUDE'], errors='coerce')
df_agg['LONGITUDE'] = pd.to_numeric(df_agg['LONGITUDE'], errors='coerce')
df_agg = df_agg.dropna(subset=['LATITUDE', 'LONGITUDE'])

# --------------------------------------------------
# Filtro (apenas coordenador)
# --------------------------------------------------
st.sidebar.header("Filtros")

coords = sorted(df_agg["COORDENAÇÃO"].dropna().unique().tolist())

coord_sel = st.sidebar.selectbox(
    "Coordenador",
    options=["Todos"] + coords,
    index=0
)

# --------------------------------------------------
# Funções auxiliares
# --------------------------------------------------
def filter_points(df, coord_filter):
    if coord_filter == "Todos":
        return df.copy()
    return df[df["COORDENAÇÃO"] == coord_filter]


def compute_bbox_center_zoom(df_points):
    if df_points.empty:
        return {"lat": -14.2350, "lon": -51.9253}, 3.5

    lat_min, lat_max = df_points["LATITUDE"].min(), df_points["LATITUDE"].max()
    lon_min, lon_max = df_points["LONGITUDE"].min(), df_points["LONGITUDE"].max()

    center = {
        "lat": (lat_min + lat_max) / 2,
        "lon": (lon_min + lon_max) / 2
    }

    span = max(lat_max - lat_min, lon_max - lon_min)

    if span > 30: zoom = 2.5
    elif span > 15: zoom = 3.0
    elif span > 8: zoom = 3.5
    elif span > 4: zoom = 4.0
    elif span > 2: zoom = 4.5
    elif span > 1: zoom = 5.0
    elif span > 0.5: zoom = 5.5
    else: zoom = 6.0

    return center, zoom


def neutral_fill(alpha=0.15):
    return f"rgba(60,60,60,{alpha})"

# --------------------------------------------------
# Filtrar dados
# --------------------------------------------------
df_points = filter_points(df_agg, coord_sel)

# --------------------------------------------------
# Criar mapa (pontos)
# --------------------------------------------------
fig = px.scatter_mapbox(
    df_points,
    lat="LATITUDE",
    lon="LONGITUDE",
    color="COORDENADOR",
    size="QTD_LOJAS",
    hover_name="CIDADE",
    hover_data={
        "COORDENADOR": True,
        "QTD_LOJAS": True,
        "LATITUDE": False,
        "LONGITUDE": False
    },
    height=600
)

# --------------------------------------------------
# Polígonos (Convex Hull por coordenador)
# --------------------------------------------------
coords_to_draw = (
    df_points["COORDENAÇÃO"].dropna().unique()
    if coord_sel == "Todos"
    else [coord_sel]
)

for coord in coords_to_draw:
    df_coord = df_agg[df_agg["COORDENAÇÃO"] == coord]

    pts = (
        df_coord[["LONGITUDE", "LATITUDE"]]
        .drop_duplicates()
        .to_numpy()
    )

    if len(pts) < 3:
        continue

    hull = ConvexHull(pts)
    polygon_lon = pts[hull.vertices, 0].tolist() + [pts[hull.vertices, 0][0]]
    polygon_lat = pts[hull.vertices, 1].tolist() + [pts[hull.vertices, 1][0]]

    fig.add_trace(
        go.Scattermapbox(
            lon=polygon_lon,
            lat=polygon_lat,
            mode="lines",
            fill="toself",
            fillcolor=neutral_fill(0.15),
            line=dict(color="rgba(0,0,0,0)"),
            showlegend=False,
            text=[str(coord)] * len(polygon_lon),
            hovertemplate="<b>Coordenador:</b> %{text}<extra></extra>"
        )
    )

# --------------------------------------------------
# Layout
# --------------------------------------------------
center, zoom = compute_bbox_center_zoom(df_points)

fig.update_layout(
    mapbox_style="open-street-map",
    mapbox_center=center,
    mapbox_zoom=zoom,
    margin=dict(r=0, t=40, l=0, b=0),
    title=f"Coordenador: {coord_sel}"
)

# --------------------------------------------------
# Render
# --------------------------------------------------
st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# Resumo
# --------------------------------------------------
total_lojas = int(df_points["QTD_LOJAS"].sum()) if not df_points.empty else 0

st.markdown(
    f"""
    <p style="font-size:22px; font-weight:bold; margin-top:15px;">
        Total de lojas: {total_lojas}
    </p>
    """,
    unsafe_allow_html=True
)

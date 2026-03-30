import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.spatial import ConvexHull
import requests

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

@st.cache_data
def load_geojson():
    url = "https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson"
    return requests.get(url).json()

df_agg = load_data()
geojson_br = load_geojson()

# --------------------------------------------------
# Filtros (sidebar)
# --------------------------------------------------
st.sidebar.header("Filtros")

regionais = sorted(df_agg["REGIONAL"].dropna().unique())
regional_sel = st.sidebar.selectbox(
    "Regional",
    options=["Todos"] + list(regionais)
)

if regional_sel == "Todos":
    coords_filtrados = sorted(df_agg["COORDENAÇÃO"].dropna().unique())
else:
    coords_filtrados = sorted(
        df_agg[df_agg["REGIONAL"] == regional_sel]["COORDENAÇÃO"].dropna().unique()
    )

coord_sel = st.sidebar.selectbox(
    "Coordenador",
    options=["Todos"] + list(coords_filtrados)
)

# --------------------------------------------------
# Funções auxiliares
# --------------------------------------------------
def current_filters(regional_sel, coord_sel):
    reg = None if regional_sel == "Todos" else regional_sel
    coord = None if coord_sel == "Todos" else coord_sel
    return reg, coord

def filter_points(df, reg, coord):
    if reg is None and coord is None:
        return df.copy()
    if reg and not coord:
        return df[df["REGIONAL"] == reg]
    if reg and coord:
        return df[(df["REGIONAL"] == reg) & (df["COORDENAÇÃO"] == coord)]
    return df[df["COORDENAÇÃO"] == coord]

def compute_bbox_center_zoom(df):
    if df.empty:
        return {"lat": -14.2350, "lon": -51.9253}, 3.5

    lat_min, lat_max = df["latitude"].min(), df["latitude"].max()
    lon_min, lon_max = df["longitude"].min(), df["longitude"].max()

    center = {
        "lat": (lat_min + lat_max) / 2,
        "lon": (lon_min + lon_max) / 2
    }

    span = max(lat_max - lat_min, lon_max - lon_min)

    if span > 30:
        zoom = 2.5
    elif span > 15:
        zoom = 3
    elif span > 8:
        zoom = 3.5
    elif span > 4:
        zoom = 4
    elif span > 2:
        zoom = 4.5
    elif span > 1:
        zoom = 5
    else:
        zoom = 6

    return center, zoom

# --------------------------------------------------
# Aplicar filtros
# --------------------------------------------------
reg_filter, coord_filter = current_filters(regional_sel, coord_sel)
df_points = filter_points(df_agg, reg_filter, coord_filter)

# --------------------------------------------------
# Mapa base (pontos)
# --------------------------------------------------
fig = px.scatter_mapbox(
    df_points,
    lat="latitude",
    lon="longitude",
    color="REGIONAL",
    size="QTD_LOJAS",
    hover_name="CIDADE",
    hover_data={
        "COORDENAÇÃO": True,
        "TIPO": True,
        "latitude": False,
        "longitude": False
    },
    height=600
)

# --------------------------------------------------
# Polígonos (Convex Hull)
# --------------------------------------------------
groups = df_points.groupby(["REGIONAL", "COORDENAÇÃO"])

for (regional, coord), df_group in groups:
    pts = df_group[["longitude", "latitude"]].drop_duplicates().to_numpy()

    if len(pts) < 3:
        continue

    hull = ConvexHull(pts)
    poly_lon = pts[hull.vertices, 0].tolist() + [pts[hull.vertices, 0][0]]
    poly_lat = pts[hull.vertices, 1].tolist() + [pts[hull.vertices, 1][0]]

    fig.add_trace(
        go.Scattermapbox(
            lon=poly_lon,
            lat=poly_lat,
            mode="lines",
            fill="toself",
            fillcolor="rgba(60,60,60,0.15)",
            line=dict(width=0),
            hovertemplate=f"<b>{coord}</b><br>Regional: {regional}<extra></extra>",
            showlegend=False
        )
    )

# --------------------------------------------------
# Layout
# --------------------------------------------------
center, zoom = compute_bbox_center_zoom(df_points)

fig.update_layout(
    mapbox_style="carto-positron",
    mapbox_center=center,
    mapbox_zoom=zoom,
    mapbox_layers=[
        {
            "source": geojson_br,
            "type": "line",
            "color": "black",
            "line": {"width": 1},
            "below": "traces"
        }
    ],
    margin=dict(r=0, t=40, l=0, b=0),
    title=f"Regional: {regional_sel} | Coordenador: {coord_sel}"
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
    <p style="font-size:22px; font-weight:bold;">
        Total de lojas na seleção: {TIPO}
    </p>
    """,
    unsafe_allow_html=True
)

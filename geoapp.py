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

# 🔥 Garantir que lat/long são numéricos
df_agg['latitude'] = pd.to_numeric(df_agg['latitude'], errors='coerce')
df_agg['longitude'] = pd.to_numeric(df_agg['longitude'], errors='coerce')
df_agg = df_agg.dropna(subset=['latitude', 'longitude'])

# --------------------------------------------------
# Filtros
# --------------------------------------------------
st.sidebar.header("Filtros")

coords = sorted(df_agg['COORDENADOR'].dropna().unique().tolist())
coord_sel = st.sidebar.selectbox("Coordenador", ["Todos"] + coords)

# --------------------------------------------------
# Funções auxiliares
# --------------------------------------------------
def filter_points(df, coord):
    if coord == "Todos":
        return df
    return df[df["COORDENADOR"] == coord]

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

    if span > 30: zoom = 2.5
    elif span > 15: zoom = 3
    elif span > 8: zoom = 3.5
    elif span > 4: zoom = 4
    elif span > 2: zoom = 4.5
    elif span > 1: zoom = 5
    elif span > 0.5: zoom = 5.5
    else: zoom = 6

    return center, zoom

# --------------------------------------------------
# Aplicar filtro
# --------------------------------------------------
df_points = filter_points(df_agg, coord_sel)

# DEBUG (pode remover depois)
st.write(f"Total de pontos: {len(df_points)}")

# --------------------------------------------------
# Mapa
# --------------------------------------------------
fig = px.scatter_mapbox(
    df_points,
    lat='latitude',
    lon='longitude',
    color='COORDENADOR',
    size='QTD_LOJAS',
    hover_name='CIDADE',
    zoom=4,
    height=600
)

# --------------------------------------------------
# Polígonos
# --------------------------------------------------
for coord in df_points["COORDENADOR"].unique():

    df_coord = df_points[df_points["COORDENADOR"] == coord]
    pts = df_coord[['longitude', 'latitude']].drop_duplicates().to_numpy()

    if len(pts) < 3:
        continue

    hull = ConvexHull(pts)

    lon = pts[hull.vertices, 0].tolist() + [pts[hull.vertices, 0][0]]
    lat = pts[hull.vertices, 1].tolist() + [pts[hull.vertices, 1][0]]

    fig.add_trace(go.Scattermapbox(
        lon=lon,
        lat=lat,
        mode='lines',
        fill='toself',
        fillcolor='rgba(0,0,0,0.1)',
        line=dict(color='rgba(0,0,0,0)'),
        showlegend=False,
        hovertemplate=f"<b>Coordenador:</b> {coord}<extra></extra>"
    ))

# --------------------------------------------------
# Layout
# --------------------------------------------------
center, zoom = compute_bbox_center_zoom(df_points)

fig.update_layout(
    mapbox_style="carto-positron",
    mapbox_center=center,
    mapbox_zoom=zoom,
    margin={"r":0,"t":40,"l":0,"b":0}
)

# --------------------------------------------------
# Render
# --------------------------------------------------
st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# Resumo
# --------------------------------------------------
total_lojas = int(df_points['QTD_LOJAS'].sum()) if not df_points.empty else 0

st.markdown(
    f"<h3>Total de lojas: {total_lojas}</h3>",
    unsafe_allow_html=True
)

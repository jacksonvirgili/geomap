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

# --------------------------------------------------
# Filtros encadeados (sidebar)
# --------------------------------------------------
st.sidebar.header("Filtros")

regionais = sorted(df_agg["REGIONAL"].dropna().unique().tolist())
regional_sel = st.sidebar.selectbox(
    "Regional",
    options=["Todos"] + regionais,
    index=0
)

if regional_sel == "Todos":
    coords_filtrados = sorted(
        df_agg["COORDENADOR"].dropna().unique().tolist()
    )
else:
    coords_filtrados = sorted(
        df_agg.loc[
            df_agg["REGIONAL"] == regional_sel,
            "COORDENADOR"
        ].dropna().unique().tolist()
    )

coord_sel = st.sidebar.selectbox(
    "Coordenador",
    options=["Todos"] + coords_filtrados,
    index=0
)

# --------------------------------------------------
# Funções auxiliares
# --------------------------------------------------
def current_filters(regional_sel, coord_sel):
    """Converte seleção textual para filtros (None ou valor)."""
    reg_filter = None if regional_sel == "Todos" else regional_sel
    coord_filter = None if coord_sel == "Todos" else coord_sel
    return reg_filter, coord_filter


def filter_points(df, reg_filter, coord_filter):
    """Retorna apenas os pontos que devem aparecer."""
    if reg_filter is None and coord_filter is None:
        return df.copy()

    if reg_filter is not None and coord_filter is None:
        return df[df["REGIONAL"] == reg_filter]

    if reg_filter is not None and coord_filter is not None:
        return df[
            (df["REGIONAL"] == reg_filter) &
            (df["COORDENADOR"] == coord_filter)
        ]

    # Apenas coordenador (todas regionais onde ele exista)
    return df[df["COORDENADOR"] == coord_filter]


def compute_bbox_center_zoom(df_points):
    """Calcula center e zoom aproximados."""
    if df_points.empty:
        return {"lat": -14.2350, "lon": -51.9253}, 3.5

    lat_min, lat_max = (
        float(df_points["latitude"].min()),
        float(df_points["latitude"].max())
    )
    lon_min, lon_max = (
        float(df_points["longitude"].min()),
        float(df_points["longitude"].max())
    )

    center = {
        "lat": (lat_min + lat_max) / 2,
        "lon": (lon_min + lon_max) / 2
    }

    lat_span = max(0.001, lat_max - lat_min)
    lon_span = max(0.001, lon_max - lon_min)
    span = max(lat_span, lon_span)

    if span > 30:
        zoom = 2.5
    elif span > 15:
        zoom = 3.0
    elif span > 8:
        zoom = 3.5
    elif span > 4:
        zoom = 4.0
    elif span > 2:
        zoom = 4.5
    elif span > 1:
        zoom = 5.0
    elif span > 0.5:
        zoom = 5.5
    else:
        zoom = 6.0

    return center, zoom

# --------------------------------------------------
# Determina filtros e dados a exibir
# --------------------------------------------------
reg_filter, coord_filter = current_filters(regional_sel, coord_sel)
df_points = filter_points(df_agg, reg_filter, coord_filter)

# --------------------------------------------------
# Grupos (REGIONAL, COORDENADOR) para polígonos
# --------------------------------------------------
if reg_filter is None and coord_filter is None:
    groups_to_draw = sorted(
        df_agg.groupby(["REGIONAL", "COORDENADOR"]).groups.keys()
    )

elif reg_filter is not None and coord_filter is None:
    groups_to_draw = sorted(
        df_agg[df_agg["REGIONAL"] == reg_filter]
        .groupby(["REGIONAL", "COORDENADOR"])
        .groups.keys()
    )

elif reg_filter is not None and coord_filter is not None:
    groups_to_draw = [(reg_filter, coord_filter)]

else:  # apenas coordenador
    groups_to_draw = sorted(
        df_agg[df_agg["COORDENADOR"] == coord_filter]
        .groupby(["REGIONAL", "COORDENADOR"])
        .groups.keys()
    )

# --------------------------------------------------
# Scatter Mapbox (pontos filtrados)
# --------------------------------------------------
fig = px.scatter_mapbox(
    df_points,
    lat="latitude",
    lon="longitude",
    color="REGIONAL",
    size="QTD_LOJAS",
    hover_name="CIDADE",
    hover_data={
        "COORDENADOR": True,
        "QTD_LOJAS": True,
        "latitude": False,
        "longitude": False
    },
    height=600
)

# --------------------------------------------------
# Polígonos (Convex Hull por grupo)
# --------------------------------------------------
def neutral_fill(alpha=0.15):
    return f"rgba(60,60,60,{alpha})"


for regional, coord in groups_to_draw:
    df_coord = df_agg[
        (df_agg["REGIONAL"] == regional) &
        (df_agg["COORDENADOR"] == coord)
    ]

    pts = (
        df_coord[["longitude", "latitude"]]
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
            hovertemplate=(
                "<b>Coordenador:</b> %{text}<br>"
                f"Regional: {regional}"
                "<extra></extra>"
            ),
            text=[str(coord)] * len(polygon_lon),
            opacity=0.95
        )
    )

# --------------------------------------------------
# Layout final (Brasil apenas)
# --------------------------------------------------
center, zoom = compute_bbox_center_zoom(df_points)
titulo = f"Regional: {regional_sel} | Coordenador: {coord_sel}"

fig.update_layout(
    mapbox_style="white-bg",
    mapbox_center={"lat": -14.2350, "lon": -51.9253},
    mapbox_zoom=3.5,
    mapbox_layers=[
        {
            "source": geojson_br,
            "type": "fill",
            "color": "#eef3f8",
            "opacity": 0.75,
            "below": "traces"
        },
        {
            "source": geojson_br,
            "type": "line",
            "color": "black",
            "line": {"width": 1.2},
            "below": "traces"
        },
    ],
    margin=dict(r=0, t=40, l=0, b=0),
    title=f"{titulo}<br>"
)

# --------------------------------------------------
# Render no Streamlit
# --------------------------------------------------
st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------
# Resumo
# --------------------------------------------------
total_lojas = int(df_points["QTD_LOJAS"].sum()) if not df_points.empty else 0

st.markdown(
    f"""
    <p style="font-size:22px; font-weight:bold; margin-top:15px;">
        Total de lojas na seleção: {total_lojas}
    </p>
    """,
    unsafe_allow_html=True
)

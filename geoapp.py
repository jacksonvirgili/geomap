import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(layout="wide")

st.title("🗺️ Mapa de Lojas por Coordenador")

# =========================
# 📥 CARREGAR DADOS
# =========================
df = pd.read_csv("sua_base.csv")  # ajuste o nome aqui

# garantir tipos corretos
df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

df = df.dropna(subset=["latitude", "longitude"])

# =========================
# 🎛️ FILTRO INTELIGENTE
# =========================
st.sidebar.header("Filtros")

coords = sorted(df["COORDENAÇÃO"].dropna().unique())

coords_sel = st.sidebar.multiselect(
    "Coordenadores",
    options=["Todos"] + coords,
    default=["Todos"]
)

# evitar conflito "Todos" + outros
if "Todos" in coords_sel and len(coords_sel) > 1:
    coords_sel = ["Todos"]

# aplicar filtro
if "Todos" in coords_sel or len(coords_sel) == 0:
    df_points = df.copy()
    coords_ativos = coords
else:
    df_points = df[df["COORDENAÇÃO"].isin(coords_sel)]
    coords_ativos = coords_sel

# =========================
# 🎨 CORES POR COORDENAÇÃO
# =========================
palette = (
    px.colors.qualitative.Dark24 +
    px.colors.qualitative.Alphabet +
    px.colors.qualitative.Set3
)

coord_to_color = {
    c: palette[i % len(palette)] for i, c in enumerate(sorted(coords_ativos))
}

# =========================
# 📊 SEPARAR TIPOS
# =========================
df_loja = df_points[df_points["TIPO"] != "CASA"]
df_casa = df_points[df_points["TIPO"] == "CASA"]

# =========================
# 🗺️ CRIAR MAPA
# =========================
fig = go.Figure()

# 🔷 POLÍGONOS POR COORDENAÇÃO
for coord, df_coord in df_loja.groupby("COORDENAÇÃO"):

    if len(df_coord) < 3:
        continue  # precisa de pelo menos 3 pontos

    df_coord = df_coord.sort_values(by=["latitude", "longitude"])

    lats = df_coord["latitude"].tolist()
    lons = df_coord["longitude"].tolist()

    # fechar polígono
    lats.append(lats[0])
    lons.append(lons[0])

    fig.add_trace(go.Scattermapbox(
        lat=lats,
        lon=lons,
        mode="lines",
        fill="toself",
        fillcolor=coord_to_color.get(coord, "#333333"),
        line=dict(width=2, color=coord_to_color.get(coord, "#333333")),
        opacity=0.2,
        name=f"Área {coord}",
        showlegend=False,
        hoverinfo="skip"
    ))

# 🔵 LOJAS (por coordenação)
for coord, df_coord in df_loja.groupby("COORDENAÇÃO"):

    if df_coord.empty:
        continue

    fig.add_trace(go.Scattermapbox(
        lat=df_coord["latitude"],
        lon=df_coord["longitude"],
        mode="markers",
        marker=dict(
            size=12,
            color=coord_to_color.get(coord, "#333333"),
            opacity=0.9
        ),
        hovertext=df_coord["CIDADE"],
        text=df_coord["COORDENAÇÃO"],
        hovertemplate="<b>Cidade:</b> %{hovertext}<br><b>Coordenação:</b> %{text}<extra></extra>",
        name=coord,
        showlegend=True
    ))

# ⚫ CASAS (preto) + coord no hover
if not df_casa.empty:
    fig.add_trace(go.Scattermapbox(
        lat=df_casa["latitude"],
        lon=df_casa["longitude"],
        mode="markers",
        marker=dict(
            size=14,
            color="black",
            opacity=0.7
        ),
        hovertext=df_casa["CIDADE"],
        text=df_casa["COORDENAÇÃO"],
        hovertemplate="<b>CASA</b><br>Cidade: %{hovertext}<br>Coordenação: %{text}<extra></extra>",
        name="CASA",
        showlegend=True
    ))

# =========================
# ⚙️ CONFIG MAPA
# =========================
fig.update_layout(
    mapbox_style="open-street-map",
    mapbox_zoom=5,
    mapbox_center={
        "lat": df_points["latitude"].mean(),
        "lon": df_points["longitude"].mean()
    },
    margin={"r":0,"t":40,"l":0,"b":0},
    title="Distribuição de Lojas por Coordenador"
)

# =========================
# 📺 EXIBIR
# =========================
st.plotly_chart(fig, use_container_width=True)

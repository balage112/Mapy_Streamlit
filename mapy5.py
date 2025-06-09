import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import matplotlib.pyplot as plt
import openpyxl

st.set_page_config(page_title="📍 Mapa zástav", layout="wide")

st.title("📍 Interaktivní mapa zástav nemovitostí")
st.markdown("<br>", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Nahraj soubor 'podklad.xlsx' nebo 'podklad_gps.xlsx'", type=["xlsx"])

if uploaded_file:
    filename = uploaded_file.name

    if "gps" in filename.lower():
        df = pd.read_excel(uploaded_file)
    else:
        df_raw = pd.read_excel(uploaded_file)

        df1 = df_raw[["Deal - Title", "Deal - Č. úvěru", "Deal - 1. nemovitost - HODNOTA:", "Deal - Adresa zástavy 1"]].copy()
        df1 = df1.rename(columns={"Deal - Adresa zástavy 1": "Adresa"})

        df2 = df_raw[["Deal - Title", "Deal - Č. úvěru", "Deal - 2. nemovitost - HODNOTA:", "Deal - Adresa zástavy 2"]].copy()
        df2 = df2.rename(columns={"Deal - Adresa zástavy 2": "Adresa"})

        df = pd.concat([df1, df2], ignore_index=True)
        df = df[df["Adresa"].notna()]

        geolocator = Nominatim(user_agent="mapa_nemovitosti")
        geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
        df["location"] = df["Adresa"].apply(geocode)
        df["lat"] = df["location"].apply(lambda loc: loc.latitude if loc else None)
        df["lon"] = df["location"].apply(lambda loc: loc.longitude if loc else None)
        df = df[df["lat"].notna() & df["lon"].notna()]

        reverse = RateLimiter(geolocator.reverse, min_delay_seconds=1)
        def get_region(lat, lon):
            try:
                location = reverse((lat, lon), exactly_one=True, language="cs")
                address = location.raw.get("address", {})
                return address.get("state")
            except:
                return None

        df["Kraj"] = df.apply(lambda row: get_region(row["lat"], row["lon"]), axis=1)

    st.sidebar.markdown("## 🎛️ Filtry")
    st.sidebar.markdown("---")

    min_val = int(df["Deal - 1. nemovitost - HODNOTA:"].min())
    max_val = int(df["Deal - 1. nemovitost - HODNOTA:"].max())

    if min_val < max_val:
        formatted_min = f"{min_val:,}".replace(",", " ") + " Kč"
        formatted_max = f"{max_val:,}".replace(",", " ") + " Kč"

        st.sidebar.markdown("💰 **Rozmezí hodnoty (Kč)**")
        st.sidebar.markdown(f"<div style='color: #f39c12; font-size: 14px;'>{formatted_min} – {formatted_max}</div>", unsafe_allow_html=True)

        value_range = st.sidebar.slider(
            "Rozmezí hodnot",
            min_val,
            max_val,
            (min_val, max_val),
            step=100000,
            label_visibility="collapsed"
        )
        df = df[df["Deal - 1. nemovitost - HODNOTA:"].between(*value_range)]
    else:
        st.sidebar.info(f"💰 Všechny nemovitosti mají hodnotu: {min_val:,} Kč")

    st.sidebar.markdown("---")

    st.sidebar.markdown("#### 🗺️ Vyber kraj")
    all_regions = [
        "Hlavní město Praha", "Středočeský kraj", "Jihočeský kraj", "Plzeňský kraj", "Karlovarský kraj",
        "Ústecký kraj", "Liberecký kraj", "Královéhradecký kraj", "Pardubický kraj", "Kraj Vysočina",
        "Jihomoravský kraj", "Zlínský kraj", "Olomoucký kraj", "Moravskoslezský kraj", "Trnavský kraj"
    ]

    select_all_regions = st.sidebar.checkbox("✅ Vybrat všechny kraje", value=True, key="select_all_regions")
    selected_regions = st.sidebar.multiselect(
        "Kraje",
        options=all_regions,
        default=all_regions if select_all_regions else []
    )

    filtered_df = df[df["Kraj"].isin(selected_regions)]

    st.markdown("### 📊 Počet nemovitostí podle krajů")
    region_counts = df["Kraj"].value_counts().reset_index()
    region_counts.columns = ["Kraj", "Počet nemovitostí"]
    st.dataframe(region_counts, use_container_width=True)

    if not region_counts.empty:
        max_region = region_counts.iloc[0]
        min_region = region_counts.iloc[-1]

        st.markdown(f"""
        ✅ **Nejvíce nemovitostí** je v kraji: **{max_region['Kraj']}** ({max_region['Počet nemovitostí']})  
        ❌ **Nejméně nemovitostí** je v kraji: **{min_region['Kraj']}** ({min_region['Počet nemovitostí']})
        """)

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(region_counts["Kraj"], region_counts["Počet nemovitostí"], color="skyblue")
        ax.set_ylabel("Počet")
        ax.set_title("Počet nemovitostí podle krajů")
        plt.xticks(rotation=45, ha="right")
        st.pyplot(fig)

    st.markdown("### 🗺️ Zobrazení na mapě")
    map_center = [49.5, 15.5]
    m = folium.Map(location=map_center, zoom_start=7, control_scale=True)

    for _, row in filtered_df.iterrows():
        popup_text = f"""
        <b style='font-size:16px;'>{row['Deal - Title']}</b><br>
        <b>Úvěr:</b> {row['Deal - Č. úvěru']}<br>
        <b>Hodnota:</b> {row['Deal - 1. nemovitost - HODNOTA:']:,} Kč<br>
        <b>Adresa:</b> {row['Adresa']}<br>
        <b>Kraj:</b> {row['Kraj']}
        """
        folium.Marker(
            location=[row["lat"], row["lon"]],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=row["Deal - Title"],
            icon=folium.Icon(color="blue", icon="home", prefix="fa")
        ).add_to(m)

    st_folium(m, width=1100, height=600)
else:
    st.info("📂 Nahraj prosím soubor 'podklad.xlsx' nebo již zpracovaný 'podklad_gps.xlsx'.")

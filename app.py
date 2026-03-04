import streamlit as st


# ==========================================
# 1. LOGIC LAYER (Core Processing Functions)
# ==========================================
def get_tpl(heavy_vehicles):
    if heavy_vehicles <= 5:
        return "TPL1"
    elif heavy_vehicles <= 50:
        return "TPL2"
    elif heavy_vehicles <= 125:
        return "TPL3"
    elif heavy_vehicles <= 250:
        return "TPL4"
    elif heavy_vehicles <= 325:
        return "TPL5"
    else:
        return "TPL6"


def get_climate(precipitation):
    if precipitation > 600:
        return "H"
    elif precipitation >= 250:
        return "h"
    elif precipitation >= 50:
        return "a"
    else:
        return "d"


def get_soil_category(rtr_class):
    cat_I = ["A1", "A2", "A3", "A4", "TfAi"]
    cat_II = [
        "B2",
        "B4",
        "B5",
        "B6",
        "C1Ai",
        "C1B5",
        "C1B6",
        "C2Ai",
        "C2B5",
        "C2B6",
        "TcAi",
        "TfBi",
        "TcB6",
    ]
    cat_III = ["B1", "D1", "TcB1", "TcB2", "TcB4", "TcB5", "D2", "B3", "TcB3"]
    cat_IV = ["D3", "C1B1", "C1B2", "C1B3", "C1B4", "C2B1", "C2B2", "C2B3", "C2B4"]
    cat_V = ["TxA3", "TxA4"]

    if rtr_class in cat_I:
        return "I"
    elif rtr_class in cat_II:
        return "II"
    elif rtr_class in cat_III:
        return "III"
    elif rtr_class in cat_IV:
        return "IV"
    elif rtr_class in cat_V:
        return "V"
    else:
        return "Non valide"


def get_sti_class(soil_cat, climate, water_table_dist, drainage_type):
    if soil_cat == "V":
        return "Special treatment required (See Chapter IV.6)"
    if water_table_dist < 1.0:
        return {"I": "St0", "II": "St1", "III": "St2", "IV": "St2"}.get(soil_cat)
    else:
        if climate in ["H", "h"]:
            if drainage_type == 2:
                return {"I": "St0", "II": "St1", "III": "St2"}.get(soil_cat)
            else:
                return {"I": "St1", "II": "St2", "III": "St2"}.get(soil_cat)
        elif climate == "a":
            if drainage_type == 2:
                return {"I": "St1", "II": "St2", "III": "St3"}.get(soil_cat)
            else:
                return {"I": "St2", "II": "St3", "III": "St3"}.get(soil_cat)
        else:
            return {"I": "St3", "II": "St3", "III": "St3", "IV": "St3"}.get(
                soil_cat, "St2"
            )


def get_target_pj(structure_type, tpl):
    if structure_type == "Rigide":
        return "P1"
    elif structure_type == "Souple":
        return "P1" if tpl in ["TPL1", "TPL2", "TPL3"] else "P2"
    elif structure_type == "Semi-rigide":
        return "P3" if tpl in ["TPL3", "TPL4"] else "P2"


def calculate_couche_de_forme(tpl, sti, target_pj, material):
    if not sti or "Special" in sti:
        return "Vérification manuelle requise (Sol spécial)."

    # 1. STRICT CATALOGUE LOOKUP FIRST
    if tpl in ["TPL1", "TPL2", "TPL3"]:
        if material == "F2":
            if sti == "St0":
                return "10 cm AC + 30 cm F2 = 40 cm (Donne P1)"
            elif sti == "St1":
                return "10 cm AC + 20 cm F2 = 30 cm (Donne P2)"
            else:
                try:
                    native_p = int(sti[-1])
                    return f"+ 30 cm F2 (Donne P{native_p + 1})"
                except:
                    pass

    elif tpl in ["TPL4", "TPL5", "TPL6"]:
        if material == "F1":
            if sti == "St0":
                return "10 cm AC + 40 cm F1 = 50 cm (Donne P2)"
            elif sti == "St1":
                return "10 cm AC + 25 cm F1 = 35 cm (Donne P2)"
            else:
                try:
                    native_p = int(sti[-1])
                    return f"+ 40 cm F1 (Donne P{native_p + 1})"
                except:
                    pass

        elif material == "MT":
            if sti == "St0":
                return "40 cm MT (Donne P2)"
            elif sti == "St1":
                if target_pj == "P3":
                    return "50 cm MT (Donne P3)"
                return "25 cm MT (Donne P2)"

    # 2. FALLBACK LOGIC
    try:
        native_p = int(sti[-1])
        target_p_val = int(target_pj[-1])
        if native_p >= target_p_val:
            return f"Non nécessaire. Le sol natif ({sti}) satisfait la cible ({target_pj})."
    except:
        pass

    return "Évaluer un renforcement sur mesure."


# ==========================================
# 2. UI LAYER (Sequential Flow)
# ==========================================
st.set_page_config(page_title="Calculateur Couche de Forme", layout="centered")

st.title("Calculateur: Couche de Forme")
st.markdown("Flux de conception séquentiel selon le catalogue des structures.")

# --- STEP 1: TRAFFIC ---
st.header("1. Trafic")
heavy_vehicles = st.number_input(
    "Trafic PL > 8T (Véhicules/Jour)", min_value=0, value=100, step=10
)
tpl = get_tpl(heavy_vehicles)
st.info(f"Classe de trafic retenue: **{tpl}**")

# --- STEP 2: CLIMATE & DRAINAGE ---
st.header("2. Climat & Drainage")
col_c, col_d = st.columns(2)
with col_c:
    precipitation = st.number_input(
        "Précipitation (mm/an)", min_value=0, value=300, step=50
    )
    climate = get_climate(precipitation)
    st.info(f"Climat retenu: **{climate}**")
with col_d:
    water_table = st.number_input(
        "Profondeur nappe (m)", min_value=0.0, value=1.5, step=0.1
    )
    drainage = st.selectbox("Type de drainage", [1, 2])

# --- STEP 3: SOIL TYPE ---
st.header("3. Type de Sol")
rtr_options = [
    "A1",
    "A2",
    "A3",
    "A4",
    "TfAi",
    "B1",
    "B2",
    "B3",
    "B4",
    "B5",
    "B6",
    "C1Ai",
    "C1B5",
    "C1B6",
    "D1",
    "D2",
    "D3",
    "TxA3",
    "TxA4",
]
rtr_class = st.selectbox("Classification RTR", rtr_options, index=6)
soil_cat = get_soil_category(rtr_class)
st.info(f"Catégorie de sol retenue: **{soil_cat}**")

# --- STEP 4: STRUCTURE TYPE & DYNAMIC MATERIAL ---
st.header("4. Structure")
structure = st.selectbox("Type de structure", ["Souple", "Semi-rigide", "Rigide"])

# Dynamic Material Assignment based on TPL constraint
if tpl in ["TPL1", "TPL2", "TPL3"]:
    material = "F2"
    st.write("Matériau Couche de Forme imposé par le trafic: **F2**")
else:
    material = st.selectbox("Choix du matériau Couche de Forme", ["F1", "MT"])

st.divider()

# --- EXECUTION & OUTPUT ---
if st.button("Calculer la structure", type="primary"):

    # Process final calculations
    sti = get_sti_class(soil_cat, climate, water_table, drainage)
    target_pj = get_target_pj(structure, tpl)
    result = calculate_couche_de_forme(tpl, sti, target_pj, material)

    # Display Results
    st.subheader("Diagnostic Système")

    mcol1, mcol2, mcol3, mcol4 = st.columns(4)
    mcol1.metric("Catégorie Sol", f"Cat {soil_cat}")
    mcol2.metric("Climat", climate)
    mcol3.metric(f"Portance Native", sti)
    mcol4.metric("Portance Cible", target_pj)

    st.success(f"**Recommandation Couche de Forme:** {result}")

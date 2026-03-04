import streamlit as st

# ==========================================
# 1. LOGIC LAYER: SUBGRADE (Couche de Forme)
# ==========================================
def get_tpl(heavy_vehicles):
    if heavy_vehicles <= 5: return 'TPL1'
    elif heavy_vehicles <= 50: return 'TPL2'
    elif heavy_vehicles <= 125: return 'TPL3'
    elif heavy_vehicles <= 250: return 'TPL4'
    elif heavy_vehicles <= 325: return 'TPL5'
    else: return 'TPL6'

def get_climate(precipitation):
    if precipitation > 600: return 'H'
    elif precipitation >= 250: return 'h'
    elif precipitation >= 50: return 'a'
    else: return 'd'

def get_soil_category(rtr_class):
    cat_I = ['A1', 'A2', 'A3', 'A4', 'TfAi']
    cat_II = ['B2', 'B4', 'B5', 'B6', 'C1Ai', 'C1B5', 'C1B6', 'C2Ai', 'C2B5', 'C2B6', 'TcAi', 'TfBi', 'TcB6']
    cat_III = ['B1', 'D1', 'TcB1', 'TcB2', 'TcB4', 'TcB5', 'D2', 'B3', 'TcB3']
    cat_IV = ['D3', 'C1B1', 'C1B2', 'C1B3', 'C1B4', 'C2B1', 'C2B2', 'C2B3', 'C2B4']
    cat_V = ['TxA3', 'TxA4']
    if rtr_class in cat_I: return 'I'
    elif rtr_class in cat_II: return 'II'
    elif rtr_class in cat_III: return 'III'
    elif rtr_class in cat_IV: return 'IV'
    elif rtr_class in cat_V: return 'V'
    else: return 'Unknown'

def get_sti_class(soil_cat, climate, water_table_dist, drainage_type):
    if soil_cat == 'V': return "Special"
    if water_table_dist < 1.0: 
        return {'I': 'St0', 'II': 'St1', 'III': 'St2', 'IV': 'St2'}.get(soil_cat)
    else:
        if climate in ['H', 'h']:
            if drainage_type == 2: return {'I': 'St0', 'II': 'St1', 'III': 'St2'}.get(soil_cat)
            else: return {'I': 'St1', 'II': 'St2', 'III': 'St2'}.get(soil_cat)
        elif climate == 'a':
            if drainage_type == 2: return {'I': 'St1', 'II': 'St2', 'III': 'St3'}.get(soil_cat)
            else: return {'I': 'St2', 'II': 'St3', 'III': 'St3'}.get(soil_cat)
        else: 
            return {'I': 'St3', 'II': 'St3', 'III': 'St3', 'IV': 'St3'}.get(soil_cat, 'St2')

def get_target_pj(structure_type, tpl):
    if structure_type == 'Rigide': return 'P1'
    elif structure_type == 'Souple': return 'P1' if tpl in ['TPL1', 'TPL2', 'TPL3'] else 'P2'
    elif structure_type == 'Semi-rigide': return 'P3' if tpl in ['TPL3', 'TPL4'] else 'P2'

def calculate_couche_de_forme(tpl, sti, target_pj, material):
    if not sti or "Special" in sti: return "Vérification manuelle (Sol spécial)."
    if tpl in ['TPL1', 'TPL2', 'TPL3'] and material == 'F2':
        if sti == 'St0': return "10 cm AC + 30 cm F2"
        elif sti == 'St1': return "10 cm AC + 20 cm F2"
        else: return f"+ 30 cm F2"
    elif tpl in ['TPL4', 'TPL5', 'TPL6']:
        if material == 'F1':
            if sti == 'St0': return "10 cm AC + 40 cm F1"
            elif sti == 'St1': return "10 cm AC + 25 cm F1"
            else: return f"+ 40 cm F1"
        elif material == 'MT':
            if sti == 'St0': return "40 cm MT"
            elif sti == 'St1': return "50 cm MT" if target_pj == 'P3' else "25 cm MT"
    try:
        if int(sti[-1]) >= int(target_pj[-1]): return "Non nécessaire."
    except: pass
    return "Évaluer sur mesure."

# ==========================================
# 2. LOGIC LAYER: CONSTRAINT & ROUTING ENGINE
# ==========================================
def get_allowed_surfaces(tpl, zone):
    """Filters allowed surface layers (Table a)."""
    if zone == 'II': return ['RS/ECF', 'EB/mEB']
    surfaces = []
    if tpl in ['TPL1', 'TPL2', 'TPL3', 'TPL4', 'TPL5']: surfaces.append('RS')
    if tpl in ['TPL2', 'TPL3', 'TPL4']: surfaces.append('ECF')
    if tpl in ['TPL4', 'TPL5', 'TPL6']: surfaces.append('EB/mEB')
    return surfaces

def get_fiche_options(structure, zone, tpl):
    """Routes to the correct catalog Fiche based on Zone and Structure (Table 010306)."""
    options = {}
    if zone == 'I':
        if structure == 'Souple':
            options['Fiche 1: Grave non traitée (GN)'] = 1
            if tpl not in ['TPL1', 'TPL6']: options['Fiche 2: Grave émulsion (GE)'] = 2
            if tpl in ['TPL4', 'TPL5', 'TPL6']: options['Fiche 3: Grave bitume (GBB)'] = 3
        elif structure == 'Semi-rigide':
            options['Fiche 4: Grave ciment (GAC)'] = 4
        elif structure == 'Rigide':
            options['Fiche 5: Béton de ciment (BC)'] = 5
    elif zone == 'II':
        if structure == 'Souple':
            options['Fiche 6: Grave non traitée (GN)'] = 6
            if tpl in ['TPL1', 'TPL2', 'TPL3']: options['Fiche 7: Grave émulsion (GE)'] = 7
    return options

def get_pavement_layers(fiche_id, tpl, pj, duree_vie):
    """
    DATA MATRIX SCHEMA.
    This acts as the lookup dictionary for the graphical fiches.
    I have built the architecture and populated examples. 
    You can map the rest of the visual blocks here.
    """
    matrix = {
        1: { # Fiche 1: GN
            'Longue': {
                'P1': {
                    'TPL1': ["15 GND + 25 f3", "15 GNC + 20 f2", "15 GVC + 20 f2", "7 PC + 15 BL"],
                    'TPL2': ["20 GNC + 25 f3", "20 GNB + 20 f2", "20 GVC + 25 f3"],
                    # Populate TPL3...
                }
            },
            'Courte': {
                'P2': {
                    'TPL4': ["20 GNA + 30 f1", "20 GVC + 30 f1"],
                    # Populate TPL5...
                }
            }
        },
        3: { # Fiche 3: GBB
            'Courte': {
                'P2': {
                    'TPL4': ["12 GBB + 30 f1", "12 GBB + 15 f1 + 20 f2", "5 EB + 8 GBB + 25 f1"],
                    'TPL5': ["5 EB + 10 GBB + 20 f1 + 20 f2", "5 EB + 12 GBB + 20 f1"],
                    'TPL6': ["6 EB + 10 GBB + 20 f1 + 10 GBF"]
                }
            }
        }
    }
    
    try:
        layers = matrix[fiche_id][duree_vie][pj][tpl]
        return layers
    except KeyError:
        return ["Données de la fiche non encore transcrites dans le dictionnaire Python."]


# ==========================================
# 3. UI LAYER (Sequential Flow)
# ==========================================
st.set_page_config(page_title="Calculateur VRD - Structure Globale", layout="wide")

st.title("Calculateur: Conception de Chaussée (Catalogue)")
st.markdown("Flux séquentiel: Trafic $\\rightarrow$ Plate-forme $\\rightarrow$ Corps de chaussée")

col1, col2 = st.columns(2)

with col1:
    st.header("1. Contraintes & Trafic")
    heavy_vehicles = st.number_input("Trafic PL > 8T (V/J)", min_value=0, value=150, step=10)
    tpl = get_tpl(heavy_vehicles)
    st.info(f"Classe Trafic: **{tpl}**")
    
    zone = st.radio("Zone Géotechnique", ['I', 'II'], format_func=lambda x: "Zone I (Normale)" if x == 'I' else "Zone II (Instable)")
    duree_vie = st.radio("Durée de vie visée", ['Courte', 'Longue'])

with col2:
    st.header("2. Environnement & Sol")
    precipitation = st.number_input("Précipitation (mm/an)", min_value=0, value=300)
    water_table = st.number_input("Profondeur nappe (m)", min_value=0.0, value=1.5)
    drainage = st.selectbox("Type de drainage", [1, 2])
    
    rtr_class = st.selectbox("Classification RTR", ['A1', 'A2', 'A3', 'B1', 'B2', 'B3', 'B4', 'C1Ai', 'D1', 'D2', 'TxA3'], index=4)

st.divider()

st.header("3. Plate-forme & Couche de Forme")
col3, col4 = st.columns(2)

with col3:
    structure = st.selectbox("Type de structure", ['Souple', 'Semi-rigide', 'Rigide'])
with col4:
    material_cf = 'F2' if tpl in ['TPL1', 'TPL2', 'TPL3'] else st.selectbox("Matériau Couche Forme", ['F1', 'MT'])

climate = get_climate(precipitation)
soil_cat = get_soil_category(rtr_class)
sti = get_sti_class(soil_cat, climate, water_table, drainage)
target_pj = get_target_pj(structure, tpl)

st.write(f"**Portance Native:** {sti} | **Cible Catalogue:** {target_pj}")
cf_result = calculate_couche_de_forme(tpl, sti, target_pj, material_cf)
st.success(f"Couche de Forme: {cf_result}")

st.divider()

st.header("4. Corps de Chaussée (Assises & Roulement)")

# Apply Table Logic dynamically
allowed_surfaces = get_allowed_surfaces(tpl, zone)
fiche_dict = get_fiche_options(structure, zone, tpl)

if not fiche_dict:
    st.error(f"Le catalogue ne prévoit pas de structure {structure} pour la {zone} en {tpl}.")
else:
    col5, col6 = st.columns(2)
    with col5:
        surface_choice = st.selectbox("Revêtement autorisé (Couche de roulement)", allowed_surfaces)
    with col6:
        fiche_name = st.selectbox("Fiche de conception (Couche de base/fondation)", list(fiche_dict.keys()))
        fiche_id = fiche_dict[fiche_name]

    if st.button("Générer les variantes de structure", type="primary"):
        # We assume the platform meets the target Pj after the couche de forme
        final_pj = target_pj 
        
        options = get_pavement_layers(fiche_id, tpl, final_pj, duree_vie)
        
        st.subheader(f"Variantes possibles (Fiche n°{fiche_id} - {final_pj})")
        for i, option in enumerate(options):
            st.code(f"Variante {i+1}:\n[ {surface_choice} ]\n[ {option} ]", language="text")

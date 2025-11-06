import streamlit as st
import pandas as pd
import os

# Configurazione pagina
st.set_page_config(
    page_title="Excel Data Filter",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personalizzato per mobile-first
st.markdown("""
<style>
    /* Mobile-first responsive design */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 100%;
    }
    
    .stButton>button {
        width: 100%;
        padding: 0.75rem;
        font-size: 1rem;
        margin-top: 0.5rem;
    }
    
    .stMultiSelect, .stSelectbox {
        font-size: 1rem;
    }
    
    .filter-group {
        background-color: rgba(51, 128, 141, 0.05);
        padding: 1rem;
        border-radius: 0.5rem;
        border: 2px solid rgba(51, 128, 141, 0.2);
        margin-bottom: 1rem;
    }
    
    .stRadio > label {
        font-size: 1rem;
        padding: 0.5rem 0;
    }
    
    .stDataFrame {
        font-size: 0.9rem;
    }
    
    h1, h2, h3 {
        color: #33808d;
    }
</style>
""", unsafe_allow_html=True)

# Funzioni helper
@st.cache_data
def load_excel_data(file_path):
    """Carica i dati dal file Excel"""
    try:
        df = pd.read_excel(file_path, engine='openpyxl')
        return df
    except Exception as e:
        st.error(f"Errore nel caricamento del file: {e}")
        return None

def get_column_type(df, col_name):
    """Determina se una colonna è numerica o testuale"""
    return 'number' if pd.api.types.is_numeric_dtype(df[col_name]) else 'text'

def apply_single_filter(df, col_name, condition, value):
    """Applica un singolo filtro al dataframe"""
    if df.empty:
        return df
    
    col_type = get_column_type(df, col_name)
    
    if col_type == 'number':
        try:
            num_value = float(value)
            if condition == '>':
                return df[df[col_name] > num_value]
            elif condition == '<':
                return df[df[col_name] < num_value]
            elif condition == '>=':
                return df[df[col_name] >= num_value]
            elif condition == '<=':
                return df[df[col_name] <= num_value]
            elif condition == '=':
                return df[df[col_name] == num_value]
        except:
            return df
    else:
        if condition == 'in':
            return df[df[col_name].isin(value)]
        elif condition == 'not_in':
            return df[~df[col_name].isin(value)]
    
    return df

def apply_filter_group(df, filters, group_logic):
    """Applica un gruppo di filtri con la logica interna specificata"""
    if not filters:
        return df
    
    results = []
    for filter_config in filters:
        col_name = filter_config.get('column')
        condition = filter_config.get('condition')
        value = filter_config.get('value')
        
        if col_name and condition and value is not None:
            if isinstance(value, list) and len(value) == 0:
                continue
            filtered = apply_single_filter(df, col_name, condition, value)
            results.append(set(filtered.index))
    
    if not results:
        return df
    
    if group_logic == 'AND':
        # Intersezione di tutti i set
        final_indices = set.intersection(*results)
    else:  # OR
        # Unione di tutti i set
        final_indices = set.union(*results)
    
    return df.loc[list(final_indices)]

# Inizializzazione session state
if 'filter_groups' not in st.session_state:
    st.session_state.filter_groups = []

if 'group_counter' not in st.session_state:
    st.session_state.group_counter = 0

# Caricamento dati
DATA_FILE = 'data.xlsx'

if not os.path.exists(DATA_FILE):
    st.error(f"⚠️ File '{DATA_FILE}' non trovato nella directory corrente!")
    st.info("Assicurati che il file 'data.xlsx' sia presente nella root del progetto.")
    st.stop()

df_original = load_excel_data(DATA_FILE)

if df_original is None or df_original.empty:
    st.error("Impossibile caricare i dati dal file Excel.")
    st.stop()

columns = df_original.columns.tolist()

# ============= SIDEBAR =============
st.sidebar.title("📊 Pannello di Controllo")

# Selezione colonne
st.sidebar.header("1️⃣ Colonne da Visualizzare")
selected_columns = st.sidebar.multiselect(
    "Seleziona colonne:",
    options=columns,
    default=columns[:5] if len(columns) >= 5 else columns,
    help="Scegli quali colonne visualizzare nei risultati"
)

st.sidebar.markdown("---")

# Configurazione filtri
st.sidebar.header("2️⃣ Configurazione Filtri")

global_logic = st.sidebar.radio(
    "Combina i gruppi di filtri con:",
    options=['AND', 'OR'],
    help="AND: tutti i gruppi devono essere soddisfatti | OR: almeno un gruppo deve essere soddisfatto"
)

st.sidebar.markdown("---")

# Gestione gruppi di filtri
st.sidebar.subheader("Gruppi di Filtri")

# Pulsante per aggiungere gruppo
if st.sidebar.button("➕ Aggiungi Gruppo di Filtri"):
    st.session_state.filter_groups.append({
        'id': st.session_state.group_counter,
        'logic': 'AND',
        'filters': []
    })
    st.session_state.group_counter += 1
    st.rerun()

# Visualizza i gruppi esistenti
groups_to_remove = []

for idx, group in enumerate(st.session_state.filter_groups):
    with st.sidebar.expander(f"📁 Gruppo #{group['id'] + 1}", expanded=True):
        # Logica interna del gruppo
        group['logic'] = st.radio(
            "Logica interna:",
            options=['AND', 'OR'],
            key=f"group_logic_{group['id']}",
            help="Come combinare i filtri all'interno di questo gruppo"
        )
        
        st.markdown("**Filtri in questo gruppo:**")
        
        # Gestione filtri del gruppo
        filters_to_remove = []
        
        for filter_idx, filter_config in enumerate(group['filters']):
            st.markdown(f"**Filtro {filter_idx + 1}**")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Selezione colonna
                filter_config['column'] = st.selectbox(
                    "Colonna:",
                    options=columns,
                    key=f"filter_col_{group['id']}_{filter_idx}",
                    index=columns.index(filter_config['column']) if filter_config.get('column') in columns else 0
                )
                
                col_type = get_column_type(df_original, filter_config['column'])
                
                # Selezione condizione
                if col_type == 'number':
                    conditions = {
                        '>': 'maggiore di (>)',
                        '<': 'minore di (<)',
                        '>=': 'maggiore o uguale a (>=)',
                        '<=': 'minore o uguale a (<=)',
                        '=': 'uguale a (=)'
                    }
                else:
                    conditions = {
                        'in': 'è uno di',
                        'not_in': 'non è uno di'
                    }
                
                filter_config['condition'] = st.selectbox(
                    "Condizione:",
                    options=list(conditions.keys()),
                    format_func=lambda x: conditions[x],
                    key=f"filter_cond_{group['id']}_{filter_idx}"
                )
                
                # Selezione valore
                if col_type == 'number':
                    filter_config['value'] = st.number_input(
                        "Valore:",
                        key=f"filter_val_{group['id']}_{filter_idx}",
                        value=float(filter_config.get('value', 0))
                    )
                else:
                    unique_values = df_original[filter_config['column']].unique().tolist()
                    filter_config['value'] = st.multiselect(
                        "Valori:",
                        options=unique_values,
                        key=f"filter_val_{group['id']}_{filter_idx}",
                        default=filter_config.get('value', [])
                    )
            
            with col2:
                if st.button("🗑️", key=f"remove_filter_{group['id']}_{filter_idx}", help="Rimuovi questo filtro"):
                    filters_to_remove.append(filter_idx)
            
            st.markdown("---")
        
        # Rimuovi filtri marcati
        for filter_idx in reversed(filters_to_remove):
            group['filters'].pop(filter_idx)
        
        # Pulsanti per gestione gruppo
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Aggiungi Filtro", key=f"add_filter_{group['id']}"):
                group['filters'].append({
                    'column': columns[0],
                    'condition': '>',
                    'value': 0
                })
                st.rerun()
        
        with col2:
            if st.button("🗑️ Rimuovi Gruppo", key=f"remove_group_{group['id']}"):
                groups_to_remove.append(idx)

# Rimuovi gruppi marcati
for group_idx in reversed(groups_to_remove):
    st.session_state.filter_groups.pop(group_idx)
    st.rerun()

# ============= AREA PRINCIPALE =============
st.title("📊 Filtro Avanzato Dati Excel")

# Applica filtri
df_filtered = df_original.copy()

if st.session_state.filter_groups:
    group_results = []
    
    for group in st.session_state.filter_groups:
        group_filtered = apply_filter_group(
            df_original,
            group['filters'],
            group['logic']
        )
        group_results.append(set(group_filtered.index))
    
    if group_results:
        if global_logic == 'AND':
            final_indices = set.intersection(*group_results) if group_results else set()
        else:  # OR
            final_indices = set.union(*group_results) if group_results else set()
        
        df_filtered = df_original.loc[list(final_indices)] if final_indices else pd.DataFrame()

# Applica selezione colonne
if selected_columns:
    df_display = df_filtered[selected_columns]
else:
    df_display = df_filtered

# Visualizza risultati
st.subheader("📋 Risultati")
st.info(f"Visualizzazione di **{len(df_display)}** righe su **{len(df_original)}** totali")

if not df_display.empty:
    st.dataframe(
        df_display,
        use_container_width=True,
        height=600
    )
    
    # Opzione per scaricare i risultati
    csv = df_display.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Scarica Risultati (CSV)",
        data=csv,
        file_name="risultati_filtrati.csv",
        mime="text/csv"
    )
else:
    st.warning("⚠️ Nessun risultato trovato con i filtri applicati.")

# Info footer
st.markdown("---")
st.caption("💡 Suggerimento: Usa la sidebar per configurare filtri complessi con logiche nidificate AND/OR")

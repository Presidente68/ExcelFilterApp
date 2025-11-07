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

# CSS personalizzato per mobile-first e formattazione condizionale
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
    
    /* Stile per il pulsante Reset */
    div[data-testid="stButton"] button[kind="secondary"] {
        background-color: #c0152f;
        color: white;
    }
    
    div[data-testid="stButton"] button[kind="secondary"]:hover {
        background-color: #a01228;
        color: white;
    }
    
    /* Stile per la legenda */
    .legenda-section {
        font-size: 0.9rem;
        line-height: 1.6;
    }
    
    .legenda-section h4 {
        color: #33808d;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
        font-size: 1rem;
    }
    
    .legenda-section ul {
        margin-left: 1rem;
    }
    
    .legenda-section li {
        margin-bottom: 0.5rem;
    }
    
    .legenda-section strong {
        color: #33808d;
    }
    
    /* Stile per tabella con colonne bloccate */
    .dataframe-container {
        position: relative;
        overflow-x: auto;
    }
    
    /* Intestazioni più piccole */
    .dataframe thead th {
        font-size: 0.75rem !important;
        line-height: 1.2 !important;
        white-space: normal !important;
        word-wrap: break-word !important;
        padding: 6px 4px !important;
    }
    
    /* Celle dati compatte */
    .dataframe tbody td {
        white-space: nowrap !important;
        padding: 6px 4px !important;
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

def format_value(val, col_name):
    """
    Formatta i valori in base al nome della colonna
    
    Regole di formattazione:
    - Partite Analizzate: Numero intero con separatore migliaia
    - Frequenza Storica, %Cum Freq Storica Serie, SMA/EMA Attuale: Percentuale senza decimali
    - Quota Equa: Decimale con due decimali
    - Ritardo Attuale, Prima/Dopo Media Consec Actual: Numero intero
    - Z-Score (tutti): Decimale con due decimali
    - Media strisce Forza/Debolezza: Numero intero arrotondato
    - Lunghezza ciclo Forza/Debolezza: Numero intero
    - Div, Nome Mercato, Z-Sc. Valore 3X, Z-Sc. Deb_5-10: Testo
    """
    if pd.isna(val):
        return ''
    
    # Testo senza formattazione
    text_columns = ['Div', 'Nome Mercato', 'Z-Sc. Valore 3X', 'Z-Sc. Deb_5-10', 
                    'PQS', 'Veto', 'Appetibilità_Fondo', 'Semaforo_Momentum',
                    'Appetibilità_Medio', 'PET', 'Stato_Forza_Fondo', 
                    'Semaforo_Momentum_Inverso', 'Stato_Forza_Medio']
    
    if col_name in text_columns:
        return str(val)
    
    # Numero intero con separatore migliaia
    if 'Partite Analizzate' in col_name:
        try:
            return f"{int(val):,}".replace(',', '.')
        except:
            return str(val)
    
    # Percentuale senza decimali
    if any(keyword in col_name for keyword in ['Frequenza Storica', '%Cum Freq Storica Serie', 'SMA', 'EMA']) and 'Attuale' in col_name or col_name == 'Frequenza Storica':
        try:
            return f"{val * 100:.0f}%"
        except:
            return str(val)
    
    # Quota Equa: due decimali
    if 'Quota Equa' in col_name:
        try:
            return f"{val:.2f}"
        except:
            return str(val)
    
    # Ritardo Attuale e Prima/Dopo: numero intero
    if 'Ritardo Attuale' in col_name or 'Prima/Dopo Media Consec Actual' in col_name:
        try:
            return f"{int(val)}"
        except:
            return str(val)
    
    # Z-Score: due decimali
    if 'Z-Score' in col_name:
        try:
            return f"{val:.2f}"
        except:
            return str(val)
    
    # Media stripes e Lunghezza ciclo: numero intero
    if 'Media strisce' in col_name or 'Lunghezza ciclo' in col_name:
        try:
            return f"{int(round(val))}"
        except:
            return str(val)
    
    # Default: numero con 2 decimali se numerico, altrimenti testo
    if isinstance(val, (int, float)):
        return f"{val:.2f}"
    
    return str(val)

def apply_conditional_formatting(val, col_name):
    """
    Applica formattazione condizionale basata sul valore e nome colonna
    
    Regole:
    - Z-Score Ritardi Consecutivi: >=2 verde chiaro, >=3 verde scuro
    - Z-Score Valore: <=-2 verde chiaro, <=-3 verde scuro
    - Z-Score ciclo Debolezza: >=2 verde chiaro, >=3 verde scuro
    - Z-Score ciclo Forza: >=2 arancio, >=3 rosso
    """
    if pd.isna(val) or not isinstance(val, (int, float)):
        return ''
    
    # Z-Score Ritardi Consecutivi
    if 'Z-Score Ritardi Consecutivi' in col_name:
        if val >= 3:
            return 'background-color: #2d8659; color: white; font-weight: bold;'
        elif val >= 2:
            return 'background-color: #90ee90; color: #1a5c3a; font-weight: bold;'
    
    # Z-Score Valore (qualsiasi SMA/EMA)
    if 'Z-Score Valore' in col_name:
        if val <= -3:
            return 'background-color: #2d8659; color: white; font-weight: bold;'
        elif val <= -2:
            return 'background-color: #90ee90; color: #1a5c3a; font-weight: bold;'
    
    # Z-Score ciclo Debolezza - VERDE (opportunità)
    if 'Z-Score ciclo Debolezza' in col_name:
        if val >= 3:
            return 'background-color: #2d8659; color: white; font-weight: bold;'
        elif val >= 2:
            return 'background-color: #90ee90; color: #1a5c3a; font-weight: bold;'
    
    # Z-Score ciclo Forza - ARANCIO/ROSSO (allerta)
    if 'Z-Score ciclo Forza' in col_name or 'Z-Score ciclo  Forza' in col_name:
        if val >= 3:
            return 'background-color: #d32f2f; color: white; font-weight: bold;'
        elif val >= 2:
            return 'background-color: #ff9800; color: white; font-weight: bold;'
    
    return ''

def get_column_width(col_name):
    """
    Restituisce la larghezza ottimale per ciascuna colonna
    
    - Nome Mercato: larghezza adattata al contenuto più lungo
    - Colonne numeriche: larghezza compatta
    - Altre colonne: larghezza di default
    """
    # Colonne bloccate e Nome Mercato con larghezza maggiore
    if col_name == 'Nome Mercato':
        return 200  # Larghezza per il contenuto più lungo
    elif col_name == 'Div':
        return 60
    elif col_name == 'Frequenza Storica':
        return 80
    
    # Colonne numeriche compatte
    numeric_compact = ['Partite Analizzate', 'Quota Equa', 'Ritardo Attuale', 
                      'Prima/Dopo Media Consec Actual', 'SMA', 'EMA', 'Z-Score',
                      'Media strisce', 'Lunghezza ciclo', 'PET', 'PQS']
    
    if any(keyword in col_name for keyword in numeric_compact):
        return 85  # Larghezza compatta per numeri
    
    # Default
    return 100

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

def reset_all_filters():
    """Resetta completamente tutti i filtri e lo stato"""
    st.session_state.filter_groups = []
    st.session_state.group_counter = 0
    st.session_state.global_logic = 'AND'
    if 'selected_columns' in st.session_state:
        del st.session_state.selected_columns

# Inizializzazione session state (PERSISTENTE - sopravvive ai refresh)
if 'filter_groups' not in st.session_state:
    st.session_state.filter_groups = []

if 'group_counter' not in st.session_state:
    st.session_state.group_counter = 0

if 'global_logic' not in st.session_state:
    st.session_state.global_logic = 'AND'

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

# LEGENDA - Prima di tutto per facile accesso
with st.sidebar.expander("📖 Legenda Indicatori", expanded=False):
    st.markdown("""
    <div class="legenda-section">
    
    #### 📈 Indicatori Tecnici
    
    **SMA (Simple Moving Average)**  
    Media mobile semplice. SMA50 Attuale è la frequenza dell'evento nelle ultime 50 partite. Dà lo stesso peso a ogni partita.
    
    **EMA (Exponential Moving Average)**  
    Media mobile esponenziale. Simile alla SMA, ma dà più peso alle partite più recenti, rendendola più reattiva ai cambiamenti.
    
    **Z-Score: Valore vs. Ciclo**
    
    - **Z-Score Valore** (es. Z-Score Valore SMA50): Misura la velocità/intensità del trend. Un valore molto negativo (es. -2.5) indica un ritardo intenso e recente.
    
    - **Z-Score ciclo Debolezza/Forza**: Misura la durata/persistenza del trend. Un valore molto positivo (es. +3.0) indica un ciclo di debolezza o forza eccezionalmente lungo.
    
    **Come si attivano i cicli di Debolezza e Forza**  
    ⚠️ Importante: i cicli non iniziano al semplice superamento della media.
    
    - Un **ciclo di Debolezza** inizia solo quando la media mobile scende sotto: **Media Storica - 1 Deviazione Standard**.
    
    - Un **ciclo di Forza** inizia solo quando la media mobile sale sopra: **Media Storica + 1 Deviazione Standard**.
    
    ---
    
    #### 📋 Indicatori di Base
    
    **Div**: Il campionato di riferimento (es. I1 = Serie A).
    
    **Nome Mercato**: Il tipo di scommessa e l'eventuale classe di quote.
    
    **Frequenza Storica**: La percentuale di volte che l'evento si è verificato.
    
    **Quota Equa**: La quota "giusta" calcolata dalla Frequenza Storica.
    
    **Ritardo Attuale**: Da quante partite consecutive l'evento NON si sta verificando.
    
    **Z-Score Ritardi Consecutivi**: Misura la rarità statistica della sequenza di serie "anomale". Valori > 2 indicano una situazione molto rara.
    
    **Z-Sc. Valore 3X**: Almeno 3 Z-Sc. Valore SMA tra 5 e 50 sono < -2 (forte ritardo)
    
    **Z-Sc. Deb_5-10**: gli Z-Score sui CICLI di Deb.za SMA5 E EMA10 sono >2 (Forte ritardo consecutivo oltre 1 dev std)
    
    ---
    
    #### 🎨 Legenda Colori
    
    **Verde chiaro/scuro**: Valori positivi (opportunità)
    - Z-Score Ritardi: ≥2 (chiaro), ≥3 (scuro)
    - Z-Score Valore: ≤-2 (chiaro), ≤-3 (scuro)
    - Z-Score ciclo Debolezza: ≥2 (chiaro), ≥3 (scuro)
    
    **Arancio/Rosso**: Valori di allerta
    - Z-Score ciclo Forza: ≥2 (arancio), ≥3 (rosso)
    
    </div>
    """, unsafe_allow_html=True)

st.sidebar.markdown("---")

# Selezione colonne
st.sidebar.header("1️⃣ Colonne da Visualizzare")

# Usa session_state per persistenza delle colonne selezionate
if 'selected_columns' not in st.session_state:
    st.session_state.selected_columns = columns[:5] if len(columns) >= 5 else columns

selected_columns = st.sidebar.multiselect(
    "Seleziona colonne:",
    options=columns,
    default=st.session_state.selected_columns,
    key='column_selector',
    help="Scegli quali colonne visualizzare nei risultati"
)

# Aggiorna session_state quando cambia la selezione
if selected_columns != st.session_state.selected_columns:
    st.session_state.selected_columns = selected_columns

st.sidebar.markdown("---")

# Configurazione filtri
st.sidebar.header("2️⃣ Configurazione Filtri")

# Logica globale (persistente)
global_logic = st.sidebar.radio(
    "Combina i gruppi di filtri con:",
    options=['AND', 'OR'],
    index=0 if st.session_state.global_logic == 'AND' else 1,
    help="AND: tutti i gruppi devono essere soddisfatti | OR: almeno un gruppo deve essere soddisfatto"
)

# Aggiorna session_state
if global_logic != st.session_state.global_logic:
    st.session_state.global_logic = global_logic

st.sidebar.markdown("---")

# Gestione gruppi di filtri
st.sidebar.subheader("Gruppi di Filtri")

# Pulsanti per gestione globale
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("➕ Aggiungi Gruppo", use_container_width=True):
        st.session_state.filter_groups.append({
            'id': st.session_state.group_counter,
            'logic': 'AND',
            'filters': []
        })
        st.session_state.group_counter += 1
        st.rerun()

with col2:
    if st.button("🔄 Reset Filtri", use_container_width=True, type="secondary"):
        reset_all_filters()
        st.rerun()

# Visualizza i gruppi esistenti
groups_to_remove = []

for idx, group in enumerate(st.session_state.filter_groups):
    with st.sidebar.expander(f"📁 Gruppo #{group['id'] + 1}", expanded=True):
        # Logica interna del gruppo (persistente)
        group_logic_key = f"group_logic_{group['id']}"
        current_logic = group.get('logic', 'AND')
        
        new_logic = st.radio(
            "Logica interna:",
            options=['AND', 'OR'],
            key=group_logic_key,
            index=0 if current_logic == 'AND' else 1,
            help="Come combinare i filtri all'interno di questo gruppo"
        )
        
        # Aggiorna la logica se è cambiata
        if new_logic != group['logic']:
            group['logic'] = new_logic
        
        st.markdown("**Filtri in questo gruppo:**")
        
        # Gestione filtri del gruppo
        filters_to_remove = []
        
        for filter_idx, filter_config in enumerate(group['filters']):
            st.markdown(f"**Filtro {filter_idx + 1}**")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                # Selezione colonna (persistente)
                current_col = filter_config.get('column', columns[0])
                new_col = st.selectbox(
                    "Colonna:",
                    options=columns,
                    key=f"filter_col_{group['id']}_{filter_idx}",
                    index=columns.index(current_col) if current_col in columns else 0
                )
                
                # Se la colonna è cambiata, resetta condizione e valore
                if new_col != filter_config.get('column'):
                    filter_config['column'] = new_col
                    # Resetta condizione e valore per il nuovo tipo di colonna
                    col_type = get_column_type(df_original, new_col)
                    if col_type == 'number':
                        filter_config['condition'] = '>'
                        filter_config['value'] = 0
                    else:
                        filter_config['condition'] = 'in'
                        filter_config['value'] = []
                
                col_type = get_column_type(df_original, filter_config['column'])
                
                # Selezione condizione (persistente)
                if col_type == 'number':
                    conditions = {
                        '>': 'maggiore di (>)',
                        '<': 'minore di (<)',
                        '>=': 'maggiore o uguale a (>=)',
                        '<=': 'minore o uguale a (<=)',
                        '=': 'uguale a (=)'
                    }
                    current_cond = filter_config.get('condition', '>')
                    if current_cond not in conditions:
                        current_cond = '>'
                else:
                    conditions = {
                        'in': 'è uno di',
                        'not_in': 'non è uno di'
                    }
                    current_cond = filter_config.get('condition', 'in')
                    if current_cond not in conditions:
                        current_cond = 'in'
                
                filter_config['condition'] = st.selectbox(
                    "Condizione:",
                    options=list(conditions.keys()),
                    format_func=lambda x: conditions[x],
                    key=f"filter_cond_{group['id']}_{filter_idx}",
                    index=list(conditions.keys()).index(current_cond) if current_cond in conditions else 0
                )
                
                # Selezione valore (persistente)
                if col_type == 'number':
                    current_value = filter_config.get('value', 0)
                    # Assicurati che il valore sia un numero
                    if not isinstance(current_value, (int, float)):
                        current_value = 0
                    
                    filter_config['value'] = st.number_input(
                        "Valore:",
                        key=f"filter_val_{group['id']}_{filter_idx}",
                        value=float(current_value),
                        step=0.01
                    )
                else:
                    unique_values = df_original[filter_config['column']].dropna().unique().tolist()
                    # Converti tutti i valori in stringhe per uniformità
                    unique_values = [str(v) for v in unique_values]
                    unique_values.sort()
                    
                    current_values = filter_config.get('value', [])
                    if not isinstance(current_values, list):
                        current_values = []
                    # Assicurati che i valori salvati siano stringhe
                    current_values = [str(v) for v in current_values if str(v) in unique_values]
                    
                    filter_config['value'] = st.multiselect(
                        "Valori:",
                        options=unique_values,
                        key=f"filter_val_{group['id']}_{filter_idx}",
                        default=current_values
                    )
            
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️", key=f"remove_filter_{group['id']}_{filter_idx}", help="Rimuovi questo filtro"):
                    filters_to_remove.append(filter_idx)
            
            st.markdown("---")
        
        # Rimuovi filtri marcati
        for filter_idx in reversed(filters_to_remove):
            group['filters'].pop(filter_idx)
            st.rerun()
        
        # Pulsanti per gestione gruppo
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Aggiungi Filtro", key=f"add_filter_{group['id']}", use_container_width=True):
                # Determina i valori di default in base al tipo della prima colonna
                first_col = columns[0]
                col_type = get_column_type(df_original, first_col)
                
                if col_type == 'number':
                    default_filter = {
                        'column': first_col,
                        'condition': '>',
                        'value': 0
                    }
                else:
                    default_filter = {
                        'column': first_col,
                        'condition': 'in',
                        'value': []
                    }
                
                group['filters'].append(default_filter)
                st.rerun()
        
        with col2:
            if st.button("🗑️ Rimuovi Gruppo", key=f"remove_group_{group['id']}", use_container_width=True):
                groups_to_remove.append(idx)

# Rimuovi gruppi marcati
for group_idx in reversed(groups_to_remove):
    st.session_state.filter_groups.pop(group_idx)
    st.rerun()

# ============= AREA PRINCIPALE =============
st.title("📊 Filtro Avanzato Dati Excel")

# Mostra info sulla persistenza
st.info("💡 **I filtri rimangono attivi anche dopo il refresh della pagina.** Usa il pulsante 'Reset Filtri' per azzerarli completamente.")

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
        if st.session_state.global_logic == 'AND':
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

# Info sui filtri attivi
if st.session_state.filter_groups:
    total_filters = sum(len(g['filters']) for g in st.session_state.filter_groups)
    st.success(f"✅ **{len(st.session_state.filter_groups)} gruppo/i** attivo/i con **{total_filters} filtro/i** totale/i")
else:
    st.info("ℹ️ Nessun filtro attivo. Aggiungi un gruppo per iniziare a filtrare.")

st.info(f"Visualizzazione di **{len(df_display)}** righe su **{len(df_original)}** totali")

if not df_display.empty:
    # Crea copia del dataframe per la formattazione
    df_formatted = df_display.copy()
    
    # Applica formattazione dei valori
    for col in df_formatted.columns:
        df_formatted[col] = df_formatted[col].apply(lambda x: format_value(x, col))
    
    # Applica formattazione condizionale (colori)
    styled_df = df_display.style.apply(
        lambda col: [apply_conditional_formatting(val, col.name) for val in col],
        axis=0
    ).format(lambda x, col_name: format_value(x, col_name))
    
    # Configura larghezze colonne
    column_config = {}
    for col in selected_columns:
        width = get_column_width(col)
        column_config[col] = st.column_config.Column(
            col,
            width=width
        )
    
    # Definisci le colonne bloccate (pinned)
    pinned_columns = []
    if 'Div' in selected_columns:
        pinned_columns.append('Div')
    if 'Nome Mercato' in selected_columns:
        pinned_columns.append('Nome Mercato')
    if 'Frequenza Storica' in selected_columns:
        pinned_columns.append('Frequenza Storica')
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        height=600,
        column_config=column_config,
        hide_index=True
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
st.caption("💡 **Suggerimento:** I tuoi filtri sono salvati nella sessione e sopravvivono al refresh della pagina. Usa 'Reset Filtri' per ricominciare da zero.")





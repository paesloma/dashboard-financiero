import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import datetime
import plotly.express as px

# --- CONFIGURACIÓN DIRECTA ---
# Usando tu último token generado
TOKEN = "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"
REPO_NAME = "paesloma/dashboard-financiero"
FILE_PATH = "data.csv"

def obtener_datos():
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        raw_data = contents.decoded_content.decode("utf-8")
        
        # --- SOLUCIÓN AL KEYERROR (Limpieza de comas extra) ---
        # Leemos el CSV e ignoramos columnas sin nombre creadas por comas al inicio
        df = pd.read_csv(StringIO(raw_data))
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df.columns = [c.strip() for c in df.columns]
        
        # Re-alineación forzada si el CSV está muy dañado
        cols_necesarias = ["Fecha", "Tipo", "Descripcion", "Monto", "Usuario"]
        if not all(c in df.columns for c in cols_necesarias):
            df = pd.read_csv(StringIO(raw_data), names=cols_necesarias, skiprows=1)
            
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        return df, contents.sha
    except Exception as e:
        # Muestra el error de forma clara para diagnóstico
        st.error(f"Error de conexión (401) o formato: {e}")
        return pd.DataFrame(columns=["Fecha", "Tipo", "Descripcion", "Monto", "Usuario"]), None

def guardar_datos(df, sha):
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        # Guardamos sin índice y con formato limpio
        csv_data = df.to_csv(index=False)
        repo.update_file(FILE_PATH, f"Sync {datetime.datetime.now()}", csv_data, sha)
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- INTERFAZ ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Acceso")
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if pwd in ["1602", "160232"]:
            st.session_state.auth, st.session_state.es_master = True, (pwd == "160232")
            st.rerun()
else:
    df, sha = obtener_datos()
    
    # Saldo
    ingresos = df[df['Tipo'].str.strip() == 'Ingreso']['Monto'].sum()
    egresos = df[df['Tipo'].str.strip() == 'Egreso']['Monto'].sum()
    st.title(f"💰 Saldo Actual: ${ (ingresos - egresos):,.2f }")

    # --- GRÁFICO DE BARRAS (SIEMPRE GENERAR) ---
    if not df.empty:
        st.subheader("📊 Gráfico de Movimientos")
        resumen = df.groupby('Tipo')['Monto'].sum().reset_index()
        fig = px.bar(resumen, x='Tipo', y='Monto', color='Tipo',
                     color_discrete_map={'Ingreso': '#2ecc71', 'Egreso': '#e74c3c'},
                     text_auto='.2s')
        st.plotly_chart(fig, use_container_width=True)

    # --- REGISTRO CON FECHA EDITABLE ---
    if st.session_state.es_master:
        with st.expander("📝 Registrar Movimiento"):
            with st.form("nuevo"):
                f_edit = st.date_input("Fecha", datetime.date.today())
                t_mov = st.selectbox("Tipo", ["Ingreso", "Egreso"])
                m_mov = st.number_input("Monto", min_value=0.0)
                d_mov = st.text_input("Descripción")
                if st.form_submit_button("Guardar"):
                    nueva = pd.DataFrame([{
                        "Fecha": f_edit.strftime("%Y-%m-%d"),
                        "Tipo": t_mov, "Descripcion": d_mov, 
                        "Monto": m_mov, "Usuario": "Master"
                    }])
                    df = pd.concat([df, nueva], ignore_index=True)
                    if guardar_datos(df, sha):
                        st.success("Guardado")
                        st.rerun()

    # SIEMPRE MOSTRAR TABLA
    st.subheader("📋 Registro de Órdenes")
    st.table(df)

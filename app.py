import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import datetime
import plotly.express as px # Asegúrate de tenerlo en requirements.txt

# --- CONFIGURACIÓN ---
TOKEN = "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"
REPO_NAME = "paesloma/dashboard-financiero"
FILE_PATH = "data.csv"

def obtener_datos():
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        raw_data = contents.decoded_content.decode("utf-8")
        df = pd.read_csv(StringIO(raw_data))
        
        # Limpieza automática de columnas fantasma (causadas por comas extra)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Forzar que Monto sea número para el gráfico
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        return df, contents.sha
    except Exception as e:
        return pd.DataFrame(columns=["Fecha", "Tipo", "Descripcion", "Monto", "Usuario"]), None

# --- ACCESO ---
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Control de Acceso")
    pass_input = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if pass_input in ["1602", "160232"]:
            st.session_state.auth = True
            st.session_state.es_master = (pass_input == "160232")
            st.rerun()
else:
    df, sha = obtener_datos()
    
    # --- CÁLCULOS ---
    ingresos = df[df['Tipo'].str.strip() == 'Ingreso']['Monto'].sum()
    egresos = df[df['Tipo'].str.strip() == 'Egreso']['Monto'].sum()
    saldo_total = ingresos - egresos

    st.title(f"💰 Saldo Actual: ${saldo_total:,.2f}")

    # --- GRÁFICO DE BARRAS ---
    st.subheader("📊 Resumen de Gastos vs Ingresos")
    if not df.empty:
        resumen_grafico = df.groupby('Tipo')['Monto'].sum().reset_index()
        fig = px.bar(resumen_grafico, x='Tipo', y='Monto', color='Tipo',
                     color_discrete_map={'Ingreso': '#2ecc71', 'Egreso': '#e74c3c'},
                     text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
    
    # --- REGISTRO MASTER ---
    if st.session_state.es_master:
        with st.expander("➕ Añadir Nuevo Movimiento"):
            with st.form("nuevo_dato"):
                t = st.selectbox("Tipo", ["Ingreso", "Egreso"])
                m = st.number_input("Monto", min_value=0.0)
                d = st.text_input("Descripción")
                if st.form_submit_button("Guardar"):
                    nueva = pd.DataFrame([{"Fecha": str(datetime.date.today()), "Tipo": t, "Descripcion": d, "Monto": m, "Usuario": "Master"}])
                    df = pd.concat([df, nueva], ignore_index=True)
                    # Aquí llamarías a la función de guardado
                    st.success("Dato listo para enviar a GitHub")

    # SIEMPRE MOSTRAR LA TABLA
    st.subheader("📋 Historial de Órdenes")
    st.table(df)

    if st.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

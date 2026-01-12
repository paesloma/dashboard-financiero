import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import datetime
import plotly.express as px

# --- CONFIGURACIÓN ---
# Usando el token proporcionado anteriormente
TOKEN = "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"
REPO_NAME = "paesloma/dashboard-financiero"
FILE_PATH = "data.csv"

def obtener_datos():
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        # Leer CSV y limpiar posibles espacios o comas mal puestas
        df = pd.read_csv(StringIO(contents.decoded_content.decode("utf-8")))
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        return df, contents.sha
    except Exception as e:
        return pd.DataFrame(columns=["Fecha", "Tipo", "Descripcion", "Monto", "Usuario"]), None

def guardar_datos(df, sha):
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        csv_data = df.to_csv(index=False)
        repo.update_file(FILE_PATH, f"Update {datetime.datetime.now()}", csv_data, sha)
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔐 Acceso Dashboard")
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if pwd == "1602":
            st.session_state.autenticado, st.session_state.master = True, False
            st.rerun()
        elif pwd == "160232":
            st.session_state.autenticado, st.session_state.master = True, True
            st.rerun()
        else:
            st.error("Contraseña incorrecta")
else:
    df, sha = obtener_datos()
    
    # Procesamiento de datos para cálculos
    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
    
    # --- CÁLCULOS PARA EL GRÁFICO DE BARRAS ---
    resumen = df.groupby('Tipo')['Monto'].sum().reset_index()
    
    ingresos = df[df['Tipo'] == 'Ingreso']['Monto'].sum()
    egresos = df[df['Tipo'] == 'Egreso']['Monto'].sum()
    saldo = ingresos - egresos

    st.title(f"💰 Saldo Actual: ${saldo:,.2f}")

    # --- GRÁFICO DE BARRAS ---
    st.subheader("📊 Comparativa de Movimientos")
    fig = px.bar(resumen, x='Tipo', y='Monto', color='Tipo',
                 color_discrete_map={'Ingreso': '#00CC96', 'Egreso': '#EF553B'},
                 text_auto='.2s', title="Total Ingresos vs Egresos")
    st.plotly_chart(fig, use_container_width=True)

    # --- MODO MASTER ---
    if st.session_state.master:
        with st.expander("📝 Registrar Nuevo Egreso/Ingreso"):
            with st.form("registro"):
                t = st.selectbox("Tipo", ["Ingreso", "Egreso"])
                m = st.number_input("Monto", min_value=0.0)
                d = st.text_input("Descripción")
                if st.form_submit_button("Guardar en GitHub"):
                    nueva_fila = pd.DataFrame([{
                        "Fecha": str(datetime.date.today()),
                        "Tipo": t, 
                        "Descripcion": d, 
                        "Monto": m, 
                        "Usuario": "Master"
                    }])
                    df = pd.concat([df, nueva_fila], ignore_index=True)
                    if guardar_datos(df, sha):
                        st.success("¡Datos guardados!")
                        st.rerun()

    # --- TABLA DE REGISTROS (REGLA: SIEMPRE MOSTRAR) ---
    st.divider()
    st.subheader("📋 Registro de Órdenes")
    st.table(df)

    if st.button("Cerrar Sesión"):
        st.session_state.autenticado = False
        st.rerun()

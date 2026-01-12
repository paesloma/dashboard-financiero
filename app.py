import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import datetime
import plotly.express as px

# --- CONFIGURACIÓN DIRECTA ---
# Token y Repositorio confirmados para evitar Error 401
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
        
        # Limpieza de columnas fantasma (evita KeyError)
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df.columns = [c.strip() for c in df.columns]
        
        # Convertir Monto a numérico de forma segura
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        return df, contents.sha
    except Exception as e:
        st.error(f"Error al conectar con GitHub: {e}")
        return pd.DataFrame(columns=["Fecha", "Tipo", "Descripcion", "Monto", "Usuario"]), None

def guardar_datos(df, sha):
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        csv_data = df.to_csv(index=False)
        repo.update_file(FILE_PATH, f"Registro {datetime.datetime.now()}", csv_data, sha)
        return True
    except Exception as e:
        st.error(f"No se pudo guardar: {e}")
        return False

# --- SESIÓN ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Acceso")
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if pwd in ["1602", "160232"]:
            st.session_state.auth, st.session_state.es_master = True, (pwd == "160232")
            st.rerun()
else:
    df, sha = obtener_datos()
    
    # Cálculos de Saldo
    ingresos = df[df['Tipo'].str.strip() == 'Ingreso']['Monto'].sum()
    egresos = df[df['Tipo'].str.strip() == 'Egreso']['Monto'].sum()
    saldo = ingresos - egresos

    st.title(f"💰 Saldo Actual: ${saldo:,.2f}")

    # --- GRÁFICO DE BARRAS (Confirmar que 'plotly' esté en requirements.txt) ---
    if not df.empty:
        st.subheader("📊 Comparativa de Ingresos y Egresos")
        resumen = df.groupby('Tipo')['Monto'].sum().reset_index()
        fig = px.bar(resumen, x='Tipo', y='Monto', color='Tipo',
                     color_discrete_map={'Ingreso': '#2ecc71', 'Egreso': '#e74c3c'},
                     text_auto='.2s')
        st.plotly_chart(fig, use_container_width=True)

    # --- REGISTRO CON FECHA EDITABLE (SOLO MASTER) ---
    if st.session_state.es_master:
        with st.expander("📝 Registrar Movimiento"):
            with st.form("nuevo"):
                col1, col2 = st.columns(2)
                # FECHA EDITABLE MANUALMENTE
                f_reg = col1.date_input("Fecha de Registro", datetime.date.today())
                t_mov = col1.selectbox("Tipo", ["Ingreso", "Egreso"])
                m_mov = col2.number_input("Monto", min_value=0.0)
                d_mov = col2.text_input("Descripción")
                
                if st.form_submit_button("Guardar"):
                    nueva = pd.DataFrame([{
                        "Fecha": f_reg.strftime("%Y-%m-%d"),
                        "Tipo": t_mov,
                        "Descripcion": d_mov,
                        "Monto": m_mov,
                        "Usuario": "Master"
                    }])
                    df = pd.concat([df, nueva], ignore_index=True)
                    if guardar_datos(df, sha):
                        st.success(f"Registrado con éxito el {f_reg}")
                        st.rerun()

    # REGLA: SIEMPRE MOSTRAR LA TABLA
    st.subheader("📋 Registro de Órdenes")
    st.table(df)

    if st.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

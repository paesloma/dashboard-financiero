import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import datetime
import plotly.express as px

# --- CONFIGURACIÓN ---
TOKEN = st.secrets["GITHUB_TOKEN"] 
REPO_NAME = "paesloma/dashboard-financiero"
FILE_PATH = "data.csv"

def obtener_datos():
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        df = pd.read_csv(StringIO(contents.decoded_content.decode("utf-8")))
        
        # Limpieza de comas iniciales (evita el KeyError: 'Tipo')
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df.columns = [c.strip() for c in df.columns]
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        
        return df, contents.sha
    except Exception as e:
        st.error(f"Error 401 (Credenciales) o de archivo: {e}")
        return pd.DataFrame(columns=["Fecha", "Tipo", "Descripcion", "Monto", "Usuario"]), None

def guardar_datos(df, sha):
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        csv_data = df.to_csv(index=False)
        repo.update_file(FILE_PATH, f"Registro {datetime.datetime.now()}", csv_data, sha)
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
        return False

# --- INTERFAZ ---
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Acceso")
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if pwd in ["1602", "160232"]:
            st.session_state.auth, st.session_state.master = True, (pwd == "160232")
            st.rerun()
else:
    df, sha = obtener_datos()
    
    # Saldo y Gráfico de Barras
    ingresos = df[df['Tipo'] == 'Ingreso']['Monto'].sum()
    egresos = df[df['Tipo'] == 'Egreso']['Monto'].sum()
    st.metric("💰 Saldo Actual", f"${(ingresos - egresos):,.2f}")

    if not df.empty:
        st.subheader("📊 Gráfico de Barras")
        resumen = df.groupby('Tipo')['Monto'].sum().reset_index()
        fig = px.bar(resumen, x='Tipo', y='Monto', color='Tipo', 
                     color_discrete_map={'Ingreso':'#28a745','Egreso':'#dc3545'})
        st.plotly_chart(fig, use_container_width=True)

    # --- REGISTRO CON FECHA EDITABLE ---
    if st.session_state.master:
        with st.expander("📝 Registrar Movimiento"):
            with st.form("nuevo"):
                col1, col2 = st.columns(2)
                # Aquí puedes editar la fecha manualmente
                fecha_edit = col1.date_input("Fecha de Registro", datetime.date.today())
                tipo_n = col1.selectbox("Tipo", ["Ingreso", "Egreso"])
                monto_n = col2.number_input("Monto", min_value=0.0)
                desc_n = col2.text_input("Descripción")
                
                if st.form_submit_button("Guardar Movimiento"):
                    nueva = pd.DataFrame([{
                        "Fecha": fecha_edit.strftime("%Y-%m-%d"), 
                        "Tipo": tipo_n, 
                        "Descripcion": desc_n, 
                        "Monto": monto_n, 
                        "Usuario": "Master"
                    }])
                    df = pd.concat([df, nueva], ignore_index=True)
                    if guardar_datos(df, sha):
                        st.success(f"Guardado con fecha: {fecha_edit}")
                        st.rerun()

    st.subheader("📋 Registro de Órdenes")
    st.table(df) # Siempre mostrar la tabla

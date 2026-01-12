import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import datetime
import plotly.express as px

# --- CONFIGURACIÓN CON TU TOKEN ---
# He insertado el token directamente para eliminar el error 401
TOKEN = "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"
REPO_NAME = "paesloma/dashboard-financiero"
FILE_PATH = "data.csv"

def obtener_datos():
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        raw_data = contents.decoded_content.decode("utf-8")
        
        # --- SOLUCIÓN AL FORMATO DEL CSV ---
        # Leemos el archivo ignorando columnas vacías al inicio (comas extra)
        df = pd.read_csv(StringIO(raw_data))
        
        # Si hay columnas que empiezan con "Unnamed", las borramos
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Limpiamos los nombres de las columnas por si tienen espacios
        df.columns = [c.strip() for c in df.columns]
        
        # Si por las comas extra los datos se movieron, reasignamos las columnas correctas
        columnas_necesarias = ["Fecha", "Tipo", "Descripcion", "Monto", "Usuario"]
        if len(df.columns) > 5:
            df = df.iloc[:, -5:]
            df.columns = columnas_necesarias
            
        # Aseguramos que Monto sea número
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        return df, contents.sha
    except Exception as e:
        st.error(f"Error crítico de conexión: {e}")
        return pd.DataFrame(columns=["Fecha", "Tipo", "Descripcion", "Monto", "Usuario"]), None

def guardar_datos(df, sha):
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        # Guardamos limpio sin índices ni comas raras
        csv_data = df.to_csv(index=False)
        repo.update_file(FILE_PATH, f"Sync {datetime.datetime.now()}", csv_data, sha)
        return True
    except Exception as e:
        st.error(f"Error al guardar: {e}")
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
    
    # Cálculos
    ingresos = df[df['Tipo'].str.strip() == 'Ingreso']['Monto'].sum()
    egresos = df[df['Tipo'].str.strip() == 'Egreso']['Monto'].sum()
    saldo = ingresos - egresos

    st.title(f"💰 Saldo Actual: ${saldo:,.2f}")

    # --- GRÁFICO DE BARRAS ---
    if not df.empty:
        st.subheader("📊 Gráfico de Movimientos")
        resumen = df.groupby('Tipo')['Monto'].sum().reset_index()
        fig = px.bar(resumen, x='Tipo', y='Monto', color='Tipo',
                     color_discrete_map={'Ingreso': '#2ecc71', 'Egreso': '#e74c3c'},
                     text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

    # --- REGISTRO CON FECHA EDITABLE ---
    if st.session_state.es_master:
        with st.expander("📝 Registrar Movimiento"):
            with st.form("nuevo"):
                col1, col2 = st.columns(2)
                f_edit = col1.date_input("Fecha", datetime.date.today())
                t_mov = col1.selectbox("Tipo", ["Ingreso", "Egreso"])
                m_mov = col2.number_input("Monto", min_value=0.0)
                d_mov = col2.text_input("Descripción")
                
                if st.form_submit_button("Guardar"):
                    nueva = pd.DataFrame([{
                        "Fecha": f_edit.strftime("%Y-%m-%d"),
                        "Tipo": t_mov, "Descripcion": d_mov, 
                        "Monto": m_mov, "Usuario": "Master"
                    }])
                    df = pd.concat([df, nueva], ignore_index=True)
                    if guardar_datos(df, sha):
                        st.success("Guardado exitosamente")
                        st.rerun()

    # REGLA: SIEMPRE MOSTRAR LA TABLA
    st.subheader("📋 Registro de Órdenes")
    st.table(df)

    if st.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import datetime
import plotly.express as px

# --- CONFIGURACIÓN ---
TOKEN = "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"
REPO_NAME = "paesloma/dashboard-financiero"
FILE_PATH = "data.csv"

def obtener_datos():
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        df = pd.read_csv(StringIO(contents.decoded_content.decode("utf-8")))
        
        # LIMPIEZA CRÍTICA: Eliminar columnas vacías producidas por comas extra
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Asegurar que las columnas tengan el nombre correcto y sin espacios
        df.columns = [c.strip() for c in df.columns]
        
        # Convertir Monto a número y Fecha a string para evitar errores
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        df['Tipo'] = df['Tipo'].astype(str).str.strip()
        
        return df, contents.sha
    except Exception as e:
        st.error(f"Error al obtener datos: {e}")
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
            st.session_state.auth = True
            st.session_state.es_master = (pwd == "160232")
            st.rerun()
else:
    df, sha = obtener_datos()
    
    # --- CÁLCULOS ---
    ingresos = df[df['Tipo'] == 'Ingreso']['Monto'].sum()
    egresos = df[df['Tipo'] == 'Egreso']['Monto'].sum()
    saldo = ingresos - egresos

    st.title(f"💰 Saldo Actual: ${saldo:,.2f}")

    # --- SOLUCIÓN AL GRÁFICO ---
    st.subheader("📊 Gráfico de Barras: Ingresos vs Egresos")
    if not df.empty:
        # Agrupamos datos para el gráfico
        df_grafico = df.groupby('Tipo')['Monto'].sum().reset_index()
        fig = px.bar(df_grafico, x='Tipo', y='Monto', color='Tipo',
                     color_discrete_map={'Ingreso': '#28a745', 'Egreso': '#dc3545'},
                     text_auto='.2s')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay datos suficientes para generar el gráfico.")

    # --- SOLUCIÓN A LA FECHA (MODO MASTER) ---
    if st.session_state.es_master:
        with st.expander("📝 Registrar Nuevo Movimiento"):
            with st.form("form_registro"):
                col1, col2 = st.columns(2)
                tipo_n = col1.selectbox("Tipo", ["Ingreso", "Egreso"])
                monto_n = col1.number_input("Monto", min_value=0.0)
                desc_n = col2.text_input("Descripción")
                # Se genera la fecha automáticamente aquí
                fecha_n = datetime.date.today().strftime("%Y-%m-%d") 
                
                if st.form_submit_button("Guardar Movimiento"):
                    nueva_fila = pd.DataFrame([{
                        "Fecha": fecha_n, 
                        "Tipo": tipo_n, 
                        "Descripcion": desc_n, 
                        "Monto": monto_n, 
                        "Usuario": "Master"
                    }])
                    df = pd.concat([df, nueva_fila], ignore_index=True)
                    if guardar_datos(df, sha):
                        st.success(f"✅ Registrado con fecha: {fecha_n}")
                        st.rerun()

    # REGLA: SIEMPRE MOSTRAR LA TABLA
    st.subheader("📋 Historial de Órdenes")
    st.table(df)

    if st.button("Salir"):
        st.session_state.auth = False
        st.rerun()

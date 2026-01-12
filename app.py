import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import datetime

# --- CONFIGURACIÓN CON EL NUEVO TOKEN ---
# Token actualizado para resolver el error 401
TOKEN = "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"
REPO_NAME = "paesloma/dashboard-financiero"
FILE_PATH = "data.csv"

def obtener_datos():
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        raw_data = contents.decoded_content.decode("utf-8")
        
        # --- LIMPIEZA DE DATOS (Solución al KeyError y comas extra) ---
        # Leemos el CSV y eliminamos columnas sin nombre (causadas por comas al inicio)
        df = pd.read_csv(StringIO(raw_data))
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        
        # Limpiamos espacios en los nombres de las columnas
        df.columns = [c.strip() for c in df.columns]
        
        # Si por error de formato las columnas están desplazadas, forzamos el orden
        columnas_correctas = ["Fecha", "Tipo", "Descripcion", "Monto", "Usuario"]
        if not all(c in df.columns for c in columnas_correctas) and len(df.columns) >= 5:
            df = df.iloc[:, -5:]
            df.columns = columnas_correctas
            
        # Aseguramos que Monto sea numérico para evitar errores de cálculo
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        return df, contents.sha
    except Exception as e:
        # Captura y muestra errores de conexión (como el 401) o de lectura
        st.error(f"Error de conexión o lectura: {e}")
        return pd.DataFrame(columns=["Fecha", "Tipo", "Descripcion", "Monto", "Usuario"]), None

def guardar_datos(df, sha):
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        # Guardamos el CSV limpio para evitar que se corrompa el archivo
        csv_data = df.to_csv(index=False)
        repo.update_file(FILE_PATH, f"Registro {datetime.datetime.now()}", csv_data, sha)
        return True
    except Exception as e:
        st.error(f"Error al guardar datos: {e}")
        return False

# --- LÓGICA DE ACCESO ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.title("🔐 Acceso Dashboard")
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if pwd in ["1602", "160232"]:
            st.session_state.auth = True
            st.session_state.es_master = (pwd == "160232")
            st.rerun()
else:
    df, sha = obtener_datos()
    
    # --- CÁLCULO DE SALDO (Sin gráficas por estabilidad) ---
    if not df.empty and 'Tipo' in df.columns:
        ingresos = df[df['Tipo'].str.strip() == 'Ingreso']['Monto'].sum()
        egresos = df[df['Tipo'].str.strip() == 'Egreso']['Monto'].sum()
        saldo_total = ingresos - egresos
    else:
        saldo_total = 0.0

    st.title(f"💰 Saldo Actual: ${saldo_total:,.2f}")

    # --- REGISTRO CON FECHA EDITABLE (Solo para Master) ---
    if st.session_state.es_master:
        with st.expander("📝 Registrar Nuevo Movimiento"):
            with st.form("formulario_registro"):
                col1, col2 = st.columns(2)
                # Permite editar la fecha manualmente
                f_reg = col1.date_input("Fecha", datetime.date.today())
                t_mov = col1.selectbox("Tipo", ["Ingreso", "Egreso"])
                m_mov = col2.number_input("Monto", min_value=0.0)
                d_mov = col2.text_input("Descripción")
                
                if st.form_submit_button("Guardar Movimiento"):
                    nueva_fila = pd.DataFrame([{
                        "Fecha": f_reg.strftime("%Y-%m-%d"),
                        "Tipo": t_mov, 
                        "Descripcion": d_mov, 
                        "Monto": m_mov, 
                        "Usuario": "Master"
                    }])
                    df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
                    if guardar_datos(df_actualizado, sha):
                        st.success("✅ Datos sincronizados correctamente")
                        st.rerun()

    # --- TABLA DE DATOS (Regla: Siempre mostrar) ---
    st.subheader("📋 Registro de Órdenes")
    st.table(df)

    if st.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

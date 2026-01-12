import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import datetime

# --- CONFIGURACIÓN ---
# Token con permisos 'repo' activados
TOKEN = "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"
REPO_NAME = "paesloma/dashboard-financiero"
FILE_PATH = "data.csv"

def obtener_datos():
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        raw_data = contents.decoded_content.decode("utf-8")
        
        # Limpieza de formato para evitar errores de lectura
        df = pd.read_csv(StringIO(raw_data))
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df.columns = [c.strip() for c in df.columns]
        
        # Asegurar que Monto sea numérico
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        return df, contents.sha
    except Exception as e:
        # Captura el error 401 que ves en pantalla
        st.error(f"Error de conexión (401): {e}")
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
    
    # Cálculos de Saldo (Protección contra tablas vacías)
    if not df.empty and 'Tipo' in df.columns:
        ingresos = df[df['Tipo'].str.strip() == 'Ingreso']['Monto'].sum()
        egresos = df[df['Tipo'].str.strip() == 'Egreso']['Monto'].sum()
        saldo_total = ingresos - egresos
    else:
        saldo_total = 0.0

    st.title(f"💰 Saldo Actual: ${saldo_total:,.2f}")

    # --- REGISTRO CON FECHA EDITABLE ---
    if st.session_state.es_master:
        with st.expander("📝 Registrar Movimiento"):
            with st.form("nuevo_dato"):
                col1, col2 = st.columns(2)
                # Fecha editable manualmente
                f_reg = col1.date_input("Fecha", datetime.date.today())
                t_mov = col1.selectbox("Tipo", ["Ingreso", "Egreso"])
                m_mov = col2.number_input("Monto", min_value=0.0)
                d_mov = col2.text_input("Descripción")
                
                if st.form_submit_button("Guardar"):
                    nueva = pd.DataFrame([{
                        "Fecha": f_reg.strftime("%Y-%m-%d"),
                        "Tipo": t_mov, "Descripcion": d_mov, 
                        "Monto": m_mov, "Usuario": "Master"
                    }])
                    df_final = pd.concat([df, nueva], ignore_index=True)
                    if guardar_datos(df_final, sha):
                        st.success("¡Guardado correctamente!")
                        st.rerun()

    # REGLA: SIEMPRE MOSTRAR LA TABLA
    st.subheader("📋 Registro de Órdenes")
    st.table(df)

    if st.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

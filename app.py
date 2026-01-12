import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import datetime

# --- CONFIGURACIÓN ---
# Si desbloqueaste el token en GitHub con "Allow Secret", este funcionará.
TOKEN = "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"
REPO_NAME = "paesloma/dashboard-financiero"
FILE_PATH = "data.csv"

def obtener_datos():
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        raw_data = contents.decoded_content.decode("utf-8")
        
        # Limpieza automática para evitar KeyErrors
        df = pd.read_csv(StringIO(raw_data))
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df.columns = [c.strip() for c in df.columns]
        
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        return df, contents.sha
    except Exception as e:
        # Muestra el error 401 de tus capturas de forma amigable
        st.error(f"⚠️ GitHub bloqueó el acceso (401). Verifica que pulsaste 'Allow Secret'. Detalle: {e}")
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
            st.session_state.auth, st.session_state.master = True, (pwd == "160232")
            st.rerun()
else:
    df, sha = obtener_datos()
    
    # Prevención del ValueError: Solo calcula si la tabla no está vacía
    if not df.empty and 'Tipo' in df.columns:
        ingresos = df[df['Tipo'].str.strip() == 'Ingreso']['Monto'].sum()
        egresos = df[df['Tipo'].str.strip() == 'Egreso']['Monto'].sum()
        saldo = ingresos - egresos
    else:
        saldo = 0.0

    st.title(f"💰 Saldo Actual: ${saldo:,.2f}")

    # --- REGISTRO CON FECHA EDITABLE ---
    if st.session_state.master:
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
                        st.success("¡Guardado!")
                        st.rerun()

    # REGLA: SIEMPRE MOSTRAR TABLA
    st.subheader("📋 Registro de Órdenes")
    st.table(df)

import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import datetime

# --- CONFIGURACIÓN ---
TOKEN = st.secrets["GITHUB_TOKEN"]
REPO = st.secrets["REPO_NAME"]
FILE_PATH = "data.csv"

def get_data():
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO)
        contents = repo.get_contents(FILE_PATH)
        df = pd.read_csv(StringIO(contents.decoded_content.decode()))
        return df, contents.sha
    except:
        return pd.DataFrame(columns=["Fecha", "Tipo", "Monto", "Descripcion"]), None

def save_data(df, sha):
    g = Github(TOKEN)
    repo = g.get_repo(REPO)
    csv_content = df.to_csv(index=False)
    if sha:
        repo.update_file(FILE_PATH, "Update data", csv_content, sha)
    else:
        repo.create_file(FILE_PATH, "Initial data", csv_content)

# --- LOGIN ---
if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    pwd = st.text_input("Contraseña", type="password")
    if st.button("Entrar"):
        if pwd == "1602" or pwd == "160232":
            st.session_state.auth = True
            st.session_state.is_master = (pwd == "160232")
            st.rerun()
else:
    # --- DASHBOARD ---
    df, sha = get_data()
    saldo = df[df['Tipo']=='Ingreso']['Monto'].sum() - df[df['Tipo']=='Egreso']['Monto'].sum() if not df.empty else 0
    
    st.title("💰 Saldo Actual: $" + str(round(saldo, 2)))
    
    if st.session_state.is_master:
        st.subheader("Registrar Movimiento (Modo Master)")
        with st.form("registro"):
            tipo = st.selectbox("Tipo", ["Ingreso", "Egreso"])
            monto = st.number_input("Monto", min_value=0.0)
            desc = st.text_input("Descripción")
            if st.form_submit_button("Guardar"):
                new_data = pd.DataFrame([{"Fecha": datetime.date.today(), "Tipo": tipo, "Monto": monto, "Descripcion": desc}])
                df = pd.concat([df, new_data], ignore_index=True)
                save_data(df, sha)
                st.success("Guardado en GitHub")
                st.rerun()
    
    st.table(df) # Siempre mostrar la tabla

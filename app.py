import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import datetime
import time

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Dashboard Financiero", layout="wide")

# --- GESTIÓN DE SECRETOS Y CONEXIÓN GITHUB ---
# Para que esto funcione en local, crea un archivo .streamlit/secrets.toml
# En Streamlit Cloud, agrégalos en la configuración de la app.
try:
    GITHUB_TOKEN = st.secrets["GITHUB_TOKEN"]
    REPO_NAME = st.secrets["REPO_NAME"] # Ejemplo: "usuario/finanzas-dashboard"
    FILE_PATH = "data.csv"
except:
    st.error("Faltan los secretos (GITHUB_TOKEN o REPO_NAME). Configúralos en .streamlit/secrets.toml")
    st.stop()

# --- FUNCIONES DE BASE DE DATOS (GITHUB) ---

def get_data_from_github():
    """Descarga los datos actuales desde el archivo CSV en GitHub."""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        csv_data = contents.decoded_content.decode("utf-8")
        df = pd.read_csv(StringIO(csv_data))
        return df, contents.sha
    except Exception as e:
        # Si el archivo no existe, retornamos un DataFrame vacío y None para el SHA
        return pd.DataFrame(columns=["Fecha", "Tipo", "Descripcion", "Monto", "Usuario"]), None

def save_data_to_github(df, sha_actual):
    """Sube el DataFrame actualizado a GitHub."""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(REPO_NAME)
        csv_content = df.to_csv(index=False)
        
        # Mensaje de commit
        commit_message = f"Actualización de saldo: {datetime.datetime.now()}"
        
        if sha_actual:
            repo.update_file(FILE_PATH, commit_message, csv_content, sha_actual)
        else:
            repo.create_file(FILE_PATH, commit_message, csv_content)
        return True
    except Exception as e:
        st.error(f"Error al guardar en GitHub: {e}")
        return False

# --- LÓGICA DE AUTENTICACIÓN ---

def login():
    st.markdown("## 🔒 Ingreso al Sistema")
    password = st.text_input("Ingrese su contraseña", type="password")
    
    if st.button("Ingresar"):
        if password == "1602":
            st.session_state["role"] = "user"
            st.rerun()
        elif password == "160232":
            st.session_state["role"] = "master"
            st.rerun()
        else:
            st.error("Contraseña incorrecta")

def logout():
    st.session_state["role"] = None
    st.rerun()

# --- INTERFAZ DEL DASHBOARD ---

def main_dashboard():
    # Cargar datos
    df, sha = get_data_from_github()
    
    # Calcular Saldo
    if not df.empty:
        ingresos = df[df['Tipo'] == 'Ingreso']['Monto'].sum()
        egresos = df[df['Tipo'] == 'Egreso']['Monto'].sum()
        saldo_actual = ingresos - egresos
    else:
        saldo_actual = 0.0

    # Header y Botón de Salida
    col_header, col_log = st.columns([8, 1])
    with col_header:
        st.title("📊 Dashboard Financiero")
        role_label = "Administrador (Master)" if st.session_state["role"] == "master" else "Usuario Visualizador"
        st.caption(f"Logueado como: {role_label}")
    with col_log:
        if st.button("Salir"):
            logout()

    st.markdown("---")

    # --- KPI PRINCIPAL ---
    # Mostramos el saldo grande para ambos usuarios
    st.metric(label="💰 Saldo Actual", value=f"${saldo_actual:,.2f}")

    # --- SECCIÓN MASTER (INGRESO DE DATOS) ---
    if st.session_state["role"] == "master":
        st.markdown("### 🛠 Gestión de Movimientos")
        with st.expander("Agregar Nuevo Movimiento", expanded=True):
            with st.form("entry_form"):
                col1, col2 = st.columns(2)
                with col1:
                    tipo = st.selectbox("Tipo de Movimiento", ["Ingreso", "Egreso"])
                    monto = st.number_input("Monto ($)", min_value=0.01, format="%.2f")
                with col2:
                    descripcion = st.text_input("Descripción / Motivo")
                    fecha = st.date_input("Fecha", datetime.date.today())
                
                submitted = st.form_submit_button("Guardar Movimiento")
                
                if submitted:
                    new_row = {
                        "Fecha": str(fecha),
                        "Tipo": tipo,
                        "Descripcion": descripcion,
                        "Monto": monto,
                        "Usuario": "Master"
                    }
                    # Agregar al DataFrame
                    new_df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    
                    # Guardar en GitHub
                    with st.spinner("Guardando en base de datos GitHub..."):
                        success = save_data_to_github(new_df, sha)
                        if success:
                            st.success("¡Movimiento guardado exitosamente!")
                            time.sleep(1)
                            st.rerun()

    # --- VISUALIZACIÓN DE DATOS (PARA AMBOS) ---
    st.markdown("### 📈 Historial y Análisis")
    
    if not df.empty:
        # Pestañas para organizar la vista
        tab1, tab2 = st.tabs(["Tabla de Registros", "Gráfico de Evolución"])
        
        with tab1:
            st.dataframe(df.sort_values(by="Fecha", ascending=False), use_container_width=True)
        
        with tab2:
            # Preprocesamiento para gráfico
            df['Fecha'] = pd.to_datetime(df['Fecha'])
            df_chart = df.copy()
            # Convertir egresos a negativo para el gráfico de flujo
            df_chart.loc[df_chart['Tipo'] == 'Egreso', 'Monto'] = -df_chart['Monto']
            df_chart = df_chart.sort_values('Fecha')
            df_chart['Saldo Acumulado'] = df_chart['Monto'].cumsum()
            
            st.line_chart(df_chart, x='Fecha', y='Saldo Acumulado')
    else:
        st.info("Aún no hay registros en la base de datos.")

# --- PUNTO DE ENTRADA ---
if __name__ == "__main__":
    if "role" not in st.session_state:
        st.session_state["role"] = None

    if st.session_state["role"] is None:
        login()
    else:
        main_dashboard()

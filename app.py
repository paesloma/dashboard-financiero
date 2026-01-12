import streamlit as st
import pandas as pd
from github import Github
from io import StringIO
import datetime
import plotly.express as px

# --- CONFIGURACIÓN CON TU TOKEN ---
# He copiado el token que proporcionaste para solucionar el error 401
TOKEN = "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"
REPO_NAME = "paesloma/dashboard-financiero"
FILE_PATH = "data.csv"

def obtener_datos():
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        contents = repo.get_contents(FILE_PATH)
        # Decodificar y limpiar el CSV de comas iniciales extras
        raw_data = contents.decoded_content.decode("utf-8")
        df = pd.read_csv(StringIO(raw_data))
        
        # Limpieza: eliminar columnas vacías generadas por errores de formato en el CSV
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
        df.columns = [c.strip() for c in df.columns]
        
        # Asegurar que Monto sea numérico para los cálculos y el gráfico
        df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        return df, contents.sha
    except Exception as e:
        st.error(f"Error de conexión o lectura: {e}")
        return pd.DataFrame(columns=["Fecha", "Tipo", "Descripcion", "Monto", "Usuario"]), None

def guardar_datos(df, sha):
    try:
        g = Github(TOKEN)
        repo = g.get_repo(REPO_NAME)
        csv_data = df.to_csv(index=False)
        repo.update_file(FILE_PATH, f"Registro {datetime.datetime.now()}", csv_data, sha)
        return True
    except Exception as e:
        st.error(f"Error al guardar en GitHub: {e}")
        return False

# --- INTERFAZ ---
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
    
    # Cálculos de Saldo
    ingresos = df[df['Tipo'].str.strip() == 'Ingreso']['Monto'].sum() if not df.empty else 0
    egresos = df[df['Tipo'].str.strip() == 'Egreso']['Monto'].sum() if not df.empty else 0
    saldo_total = ingresos - egresos

    st.title(f"💰 Saldo Actual: ${saldo_total:,.2f}")

    # --- GRÁFICO DE BARRAS ---
    # Para que funcione, recuerda tener 'plotly' en tu requirements.txt
    if not df.empty:
        st.subheader("📊 Comparativa de Movimientos")
        resumen = df.groupby('Tipo')['Monto'].sum().reset_index()
        fig = px.bar(resumen, x='Tipo', y='Monto', color='Tipo',
                     color_discrete_map={'Ingreso': '#2ecc71', 'Egreso': '#e74c3c'},
                     text_auto='.2s', title="Ingresos vs Egresos")
        st.plotly_chart(fig, use_container_width=True)

    # --- REGISTRO CON FECHA EDITABLE (SOLO MASTER) ---
    if st.session_state.es_master:
        with st.expander("📝 Registrar Nuevo Movimiento"):
            with st.form("registro_form"):
                col1, col2 = st.columns(2)
                # Fecha editable manualmente
                fecha_manual = col1.date_input("Fecha de Registro", datetime.date.today())
                tipo_mov = col1.selectbox("Tipo", ["Ingreso", "Egreso"])
                monto_mov = col2.number_input("Monto", min_value=0.0)
                desc_mov = col2.text_input("Descripción")
                
                if st.form_submit_button("Guardar Movimiento"):
                    nueva_fila = pd.DataFrame([{
                        "Fecha": fecha_manual.strftime("%Y-%m-%d"),
                        "Tipo": tipo_mov,
                        "Descripcion": desc_mov,
                        "Monto": monto_mov,
                        "Usuario": "Master"
                    }])
                    df_actualizado = pd.concat([df, nueva_fila], ignore_index=True)
                    if guardar_datos(df_actualizado, sha):
                        st.success(f"✅ Guardado con fecha {fecha_manual}")
                        st.rerun()

    # REGLA: SIEMPRE MOSTRAR LA TABLA
    st.subheader("📋 Registro de Órdenes")
    st.table(df)

    if st.button("Cerrar Sesión"):
        st.session_state.auth = False
        st.rerun()

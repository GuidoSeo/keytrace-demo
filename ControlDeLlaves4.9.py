import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime, date
from fpdf import FPDF

# Configuración de página
st.set_page_config(page_title="KeyTrace Pro v4.9", page_icon="🏢", layout="wide")

# --- BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('trazabilidad_llaves_v4.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS llaves 
                 (id INTEGER PRIMARY KEY, nombre_propiedad TEXT, estado TEXT, poseedor_actual TEXT, 
                  titular TEXT, direccion TEXT, cp TEXT, ultima_modificacion TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS historial 
                 (id INTEGER PRIMARY KEY, activo TEXT, accion TEXT, responsable TEXT, inquilino TEXT, 
                  dni TEXT, operacion TEXT, monto TEXT, moneda TEXT, duracion TEXT, renovacion TEXT, 
                  actualizacion TEXT, fecha TEXT, observaciones TEXT)''')
    conn.commit()
    return conn

conn = init_db()

# --- FUNCIONES AUXILIARES ---
def highlight_estado(val):
    if val == 'Prestada': return 'background-color: #ff4b4b; color: white; font-weight: bold;'
    if val == 'Disponible': return 'background-color: #28a745; color: white; font-weight: bold;'
    return ''

def log_historial(datos):
    c = conn.cursor()
    c.execute("""INSERT INTO historial (activo, accion, responsable, inquilino, dni, operacion, 
                 monto, moneda, duracion, renovacion, actualizacion, fecha, observaciones) 
                 VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""", datos)
    conn.commit()

def generar_pdf(df):
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Reporte de Trazabilidad - KeyTrace Pro", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 10, f"Generado el: {date.today()}", ln=True, align='R')
    pdf.ln(5)
    cols = ["Fecha", "Propiedad", "Movimiento", "Agente", "Cliente", "Monto"]
    pdf.set_fill_color(200, 220, 255); pdf.set_font("Arial", 'B', 10)
    for col in cols: pdf.cell(45, 10, col, 1, 0, 'C', True)
    pdf.ln()
    pdf.set_font("Arial", size=9)
    for _, row in df.iterrows():
        pdf.cell(45, 10, str(row['Fecha/Hora'])[:16], 1)
        pdf.cell(45, 10, str(row['Propiedad'])[:22], 1)
        pdf.cell(45, 10, str(row['Movimiento']), 1)
        pdf.cell(45, 10, str(row['Agente'])[:22], 1)
        pdf.cell(45, 10, str(row['Cliente'])[:22], 1)
        pdf.cell(45, 10, f"{row['Mon.']} {row['Monto']}", 1)
        pdf.ln()
    return bytes(pdf.output())

# --- MANEJO DE MENSAJES DE ÉXITO ---
if "success_msg" in st.session_state:
    st.success(st.session_state.success_msg)
    st.balloons()
    del st.session_state.success_msg

# --- BARRA LATERAL (BRANDING) ---
logo_path = "logo.png"
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, use_container_width=True)
else:
    st.sidebar.markdown("<h1 style='text-align: center; color: #4F8BF9;'>🏢 KeyTrace</h1>", unsafe_allow_html=True)

st.sidebar.markdown("---")
choice = st.sidebar.selectbox("Menú Principal", ["📊 Dashboard", "📤 Movimientos", "⚙️ Administración", "📜 Historial Completo"])
st.sidebar.markdown("---")
st.sidebar.info("Software v4.9\nMVP Inmobiliaria & Logística")

# --- 1. DASHBOARD ---
if choice == "📊 Dashboard":
    st.title("📊 Resumen de Activos")
    df_db = pd.read_sql_query("SELECT * FROM llaves", conn)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Activos", len(df_db))
    col2.metric("En Uso", len(df_db[df_db['estado'] == 'Prestada']))
    col3.metric("Disponibles", len(df_db[df_db['estado'] == 'Disponible']))

    st.divider()
    busqueda_dash = st.text_input("🔍 Filtro rápido (Nombre, Titular o Dirección)")
    df_show = df_db.copy()
    if busqueda_dash:
        df_show = df_db[df_db['nombre_propiedad'].str.contains(busqueda_dash, case=False) | 
                        df_db['titular'].str.contains(busqueda_dash, case=False) | 
                        df_db['direccion'].str.contains(busqueda_dash, case=False)]

    if not df_show.empty:
        event = st.dataframe(df_show.style.map(highlight_estado, subset=['estado']), use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
        
        if len(event.selection.rows) > 0:
            idx = event.selection.rows[0]
            row = df_show.iloc[idx]
            st.markdown(f"### 📋 Ficha Técnica: {row['nombre_propiedad']}")
            with st.container(border=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.write(f"**Propietario:** {row['titular']}")
                    st.write(f"**Dirección:** {row['direccion']}")
                with c2:
                    st.write(f"**Estado:** {row['estado']}")
                    st.write(f"**Poseedor:** {row['poseedor_actual']}")
                with c3:
                    st.write(f"**CP:** {row['cp']}")
                    st.write(f"**Última Act.:** {row['ultima_modificacion']}")
            
            st.write("**Historial Específico:**")
            df_m = pd.read_sql_query(f"SELECT fecha, accion, responsable, inquilino, observaciones FROM historial WHERE activo='{row['nombre_propiedad']}' ORDER BY id DESC LIMIT 5", conn)
            st.table(df_m)
    else:
        st.info("No hay activos.")

# --- 2. MOVIMIENTOS ---
elif choice == "📤 Movimientos":
    st.title("📤 Registro de Movimiento")
    df_llaves = pd.read_sql_query("SELECT * FROM llaves", conn)
    if not df_llaves.empty:
        with st.form("form_movimiento", clear_on_submit=True):
            col_left, col_right = st.columns(2)
            with col_left:
                activo_sel = st.selectbox("Seleccione el Activo", df_llaves['nombre_propiedad'].tolist())
                responsable = st.text_input("Responsable de la llave (Agente)")
                inquilino = st.text_input("Nombre del Inquilino / Comprador")
                dni = st.text_input("DNI Inquilino")
                tipo_op = st.radio("Tipo de Operación", ["Alquiler", "Venta"])
            with col_right:
                accion = st.radio("Acción de Llave", ["Salida", "Entrada"])
                monto = st.text_input("Monto ($)")
                moneda = st.selectbox("Moneda", ["USD", "ARS"])
                duracion = st.text_input("Duración Alquiler (Ej: 24 meses)")
                renovacion = st.checkbox("¿Opción a renovación?")
                actualizacion = st.number_input("Actualización (meses)", min_value=0, step=1)
                notas = st.text_area("Observaciones adicionales")

            if st.form_submit_button("🚀 GUARDAR REGISTRO"):
                estado_actual = df_llaves[df_llaves['nombre_propiedad'] == activo_sel]['estado'].values[0]
                if accion == "Salida" and estado_actual == "Prestada":
                    st.error(f"La llave de {activo_sel} ya está afuera.")
                elif not responsable or not inquilino:
                    st.error("Complete responsable e inquilino.")
                else:
                    fecha_hoy = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c = conn.cursor()
                    if tipo_op == "Venta":
                        c.execute("DELETE FROM llaves WHERE nombre_propiedad=?", (activo_sel,))
                        log_historial((activo_sel, "VENTA", responsable, inquilino, dni, tipo_op, monto, moneda, "", "", "", fecha_hoy, notas))
                    else:
                        est = "Prestada" if accion == "Salida" else "Disponible"
                        c.execute("UPDATE llaves SET estado=?, poseedor_actual=?, ultima_modificacion=? WHERE nombre_propiedad=?", (est, responsable if accion=="Salida" else "Nadie", fecha_hoy, activo_sel))
                        log_historial((activo_sel, accion, responsable, inquilino, dni, tipo_op, monto, moneda, duracion, str(renovacion), str(actualizacion), fecha_hoy, notas))
                    conn.commit()
                    st.session_state.success_msg = "Realizado correctamente"
                    st.rerun()

# --- 3. ADMINISTRACIÓN ---
elif choice == "⚙️ Administración":
    st.title("⚙️ Gestión de Inventario")
    tab1, tab2 = st.tabs(["➕ Alta de Activo", "🗑️ Baja de Activo"])
    
    with tab1:
        with st.form("alta_pro", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                n = st.text_input("Nombre del Activo")
                t = st.text_input("Titular (Dueño)")
            with col2:
                d = st.text_input("Dirección")
                cp_input = st.text_input("Código Postal")
            
            if st.form_submit_button("💾 GUARDAR"):
                if n and t:
                    c = conn.cursor()
                    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("INSERT INTO llaves (nombre_propiedad, estado, poseedor_actual, titular, direccion, cp, ultima_modificacion) VALUES (?,?,?,?,?,?,?)", 
                              (n, "Disponible", "Nadie", t, d, cp_input, fecha))
                    log_historial((n, "ALTA", "ADMIN", "", "", "", "", "", "", "", "", fecha, "Alta inicial de activo"))
                    conn.commit()
                    st.session_state.success_msg = "Realizado correctamente"
                    st.rerun()
                else:
                    st.error("Nombre y Titular son obligatorios.")

    with tab2:
        df_del = pd.read_sql_query("SELECT nombre_propiedad FROM llaves", conn)
        if not df_del.empty:
            with st.form("baja_pro", clear_on_submit=True):
                b_sel = st.selectbox("Activo a eliminar", df_del['nombre_propiedad'].tolist())
                mot = st.text_input("Motivo de la eliminación definitiva")
                confirm = st.checkbox("Confirmo la eliminación permanente")
                
                if st.form_submit_button("❌ ELIMINAR DEFINITIVAMENTE"):
                    if confirm and mot:
                        c = conn.cursor()
                        c.execute("DELETE FROM llaves WHERE nombre_propiedad=?", (b_sel,))
                        log_historial((b_sel, "BORRADO", "ADMIN", "", "", "", "", "", "", "", "", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), mot))
                        conn.commit()
                        st.session_state.success_msg = "Realizado correctamente"
                        st.rerun()
                    else:
                        st.error("Debe indicar motivo y confirmar la casilla.")

# --- 4. HISTORIAL COMPLETO ---
elif choice == "📜 Historial Completo":
    st.title("📜 Historial de Trazabilidad")
    c1, c2, c3 = st.columns(3)
    f_d = c1.date_input("Desde", date(2024, 1, 1))
    f_h = c2.date_input("Hasta", date.today())
    df_h = pd.read_sql_query("SELECT * FROM historial ORDER BY id DESC", conn)
    act_s = c3.selectbox("Activo", ["TODOS"] + df_h['activo'].unique().tolist())
    df_h['fecha_dt'] = pd.to_datetime(df_h['fecha']).dt.date
    df_f = df_h[(df_h['fecha_dt'] >= f_d) & (df_h['fecha_dt'] <= f_h)]
    if act_s != "TODOS": df_f = df_f[df_f['activo'] == act_s]
    df_disp = df_f.drop(columns=['fecha_dt', 'id']).rename(columns={'activo':'Propiedad','accion':'Movimiento','responsable':'Agente','inquilino':'Cliente','dni':'DNI','operacion':'Contrato','monto':'Monto','moneda':'Mon.','fecha':'Fecha/Hora'})
    st.dataframe(df_disp, use_container_width=True, hide_index=True)
    if not df_disp.empty:
        if st.button("📄 Generar Reporte PDF"):
            pdf_bytes = generar_pdf(df_disp)
            st.download_button(label="📥 Descargar PDF", data=pdf_bytes, file_name=f"Reporte_{date.today()}.pdf", mime="application/pdf")
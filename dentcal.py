import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta, date
import time as t_sleep
import pymysql  # Usamos pymysql directamente para mayor estabilidad en la nube
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(
    page_title="DentCal: Gestión Odontológica",
    page_icon="🦷",  
    layout="wide"
)

def conectar_db():
    return pymysql.connect(
        host=st.secrets["db_host"],
        port=int(st.secrets["db_port"]),
        user=st.secrets["db_user"],
        password=st.secrets["db_password"],
        database=st.secrets["db_name"],
        autocommit=True,
        ssl={'ssl': {}}  # 🚨 ESTA LÍNEA ES LA CLAVE: Activa el cifrado TLS obligatorio de TiDB
    )

import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generar_pdf_recibo(id_cita, nombre_paciente, total, metodo, regimen, observaciones=""):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    
    # Estilos personalizados para tu clínica
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor("#1E3A8A"), spaceAfter=10)
    sub_style = ParagraphStyle('SubStyle', parent=styles['Normal'], fontSize=10, textColor=colors.gray, spaceAfter=20)
    normal_style = ParagraphStyle('Norm', parent=styles['Normal'], fontSize=11, spaceAfter=8)
    
    # Encabezado
    story.append(Paragraph("🦷 DENTCAL - CONTROL PROFESIONAL", title_style))
    story.append(Paragraph("Recibo Oficial de Pago e Historial Clínico", sub_style))
    story.append(Spacer(1, 15))
    
    # Datos del comprobante
    story.append(Paragraph(f"<b>Código de Cita:</b> {id_cita}", normal_style))
    story.append(Paragraph(f"<b>Paciente:</b> {nombre_paciente}", normal_style))
    story.append(Paragraph(f"<b>Régimen Contable:</b> {regimen}", normal_style))
    story.append(Paragraph(f"<b>Método de Recaudación:</b> {metodo}", normal_style))
    if observaciones:
        story.append(Paragraph(f"<b>Observaciones:</b> {observaciones}", normal_style))
    
    story.append(Spacer(1, 20))
    
    # Tabla de montos
    data_tabla = [
        [Paragraph("<b>Concepto</b>", normal_style), Paragraph("<b>Total Asentado</b>", normal_style)],
        ["Liquidación de Servicio Dental", f"${total:,.2f}"]
    ]
    
    t = Table(data_tabla, colWidths=[350, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor("#F3F4F6")),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
    ]))
    story.append(t)
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

####facturacion######
def mostrar_modulo_facturacion(id_cita_sel, id_paciente_sel, nombre_paciente):
    st.markdown("### 🧾 Panel de Liquidación y Caja Chica")
    st.write(f"**Paciente:** {nombre_paciente} | **Código de Cita:** {id_cita_sel}")

    # --- CONTROL DE MEMORIA DE CARGOS ---
    # Inicializa el "carrito de compras" en la sesión para que no se borre al dar clics
    if 'items_factura' in st.session_state:
        if st.session_state.get('cita_actual_factura') != id_cita_sel:
            st.session_state['items_factura'] = []
            st.session_state['cita_actual_factura'] = id_cita_sel
    else:
        st.session_state['items_factura'] = []
        st.session_state['cita_actual_factura'] = id_cita_sel

    # --- PANELES EN PARALELO (FISCAL Y ENTRADAS) ---
    st.write("---")
    col_izq, col_der = st.columns(2)

    with col_izq:
        st.write("#### 🛡️ Clasificación Contable (Auditoría)")
        regimen = st.selectbox(
            "Seleccione Régimen Fiscal para esta venta:",
            ["Régimen General", "Cuota Fija"],
            help="Cuota Fija guarda el ingreso plano sin desglosar impuestos. Régimen General permite registrar IVA y retenciones."
        )
        
        metodo_pago = st.selectbox("Método de Recaudación:", ["Efectivo", "Tarjeta", "Transferencia"])
        anticipo = st.number_input("Monto de Anticipo / Abono previo dejado ($):", min_value=0.0, value=0.0, step=5.0)

    with col_der:
        st.write("#### 🦷 Agregar Procedimientos o Insumos")
        tipo_item = st.selectbox("Categoría del Cargo:", ["Consulta", "Procedimiento", "Insumo"])
        
        # Sugerencias rápidas para agilizar el trabajo de la secretaria
        if tipo_item == "Consulta":
            desc_sug = "Consulta Odontológica General"
            precio_sug = 30.0
        elif tipo_item == "Procedimiento":
            desc_sug = "Limpieza Profiláctica / Resina"
            precio_sug = 40.0
        else:
            desc_sug = "Insumo: Cepillo Ortodóntico / Medicamento"
            precio_sug = 10.0

        descripcion = st.text_input("Detalle del concepto:", value=desc_sug)
        c_cant, c_prec = st.columns(2)
        cantidad = c_cant.number_input("Cant:", min_value=1, value=1, step=1)
        precio_uni = c_prec.number_input("Precio Unitario ($):", min_value=0.0, value=precio_sug, step=5.0)

        if st.button("➕ Añadir Línea al Recibo", use_container_width=True):
            st.session_state['items_factura'].append({
                "tipo": tipo_item,
                "descripcion": descripcion,
                "cantidad": cantidad,
                "precio": precio_uni,
                "total": cantidad * precio_uni
            })
            st.toast(f"Agregado: {descripcion}")
            st.rerun()

    # --- TABLA DE DESGLOSE VISUAL ---
    if st.session_state['items_factura']:
        st.write("---")
        st.write("#### 📋 Detalles del Recibo Actual")
        df_items = pd.DataFrame(st.session_state['items_factura'])
        st.dataframe(df_items[['tipo', 'descripcion', 'cantidad', 'precio', 'total']], use_container_width=True)
        
        if st.button("🗑️ Vaciar Cuenta"):
            st.session_state['items_factura'] = []
            st.rerun()

        # --- LÓGICA DE MATEMÁTICA FISCAL ---
        subtotal = float(df_items['total'].sum())
        
        if regimen == "Cuota Fija":
            iva = 0.00
            retencion = 0.00
            st.caption("ℹ️ *Régimen de Cuota Fija seleccionado: El total se registrará neto sin desglosar débitos fiscales.*")
        else:
            # En Régimen General, dejamos casillas opcionales por si la consulta está exenta pero vendiste un insumo con IVA
            c_tax1, c_tax2 = st.columns(2)
            aplica_iva = c_tax1.checkbox("¿Cobrar IVA (15%) sobre el Subtotal?", value=False)
            aplica_ir = c_tax2.checkbox("¿Aplicar Retención de IR (2%)?", value=False)
            
            iva = subtotal * 0.15 if aplica_iva else 0.00
            retencion = subtotal * 0.02 if aplica_ir else 0.00

        # El total final a pagar en caja resta el anticipo que el cliente dio antes
        total_neto = max(0.0, subtotal + iva - retencion - float(anticipo))

        # Cuadro de Resumen Contable Estético
        st.markdown(f"""
        <div style='background-color: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 5px solid #1f3864; margin-top:15px;'>
            <h4 style='margin:0 0 10px 0; color:#1f3864;'>📊 Balance de Cuenta para Auditoría</h4>
            <table style='width:100%; font-size:14px; border-collapse: collapse;'>
                <tr><td><b>Subtotal Bruto:</b></td><td style='text-align:right;'>${subtotal:,.2f}</td></tr>
                <tr><td><b>IVA Cobrado (+):</b></td><td style='text-align:right; color:#2e7d32;'>${iva:,.2f}</td></tr>
                <tr><td><b>Retención Recibida (-):</b></td><td style='text-align:right; color:#b30000;'>${retencion:,.2f}</td></tr>
                <tr><td><b>Abono / Anticipo Previo (-):</b></td><td style='text-align:right; color:#0066cc;'>${anticipo:,.2f}</td></tr>
                <tr style='font-size:18px; font-weight:bold; border-top:1px solid #ccc;'>
                    <td><span style='color:#1f3864;'>Monto Neto Real a Recaudar:</span></td>
                    <td style='text-align:right; color:#1f3864;'>${total_neto:,.2f}</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
        
        observaciones = st.text_area("Observaciones Contables / Clínicas:")

        # --- GUARDADO INMUTABLE EN TIDB ---
        if st.button("🔒 Procesar Venta y Asentar en Libros", type="primary", use_container_width=True):
            conn_fac = None
            try:
                conn_fac = conectar_db()
                cursor_fac = conn_fac.cursor()
                
                # 1. Insertamos la Cabecera de la Factura
                query_cab = """
                    INSERT INTO facturas (
                        id_cita, id_paciente, monto_anticipo, monto_subtotal, monto_total, 
                        regimen_fiscal, impuesto_iva, retencion_ir, estado_pago, metodo_pago, observaciones
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'Pagado', %s, %s)
                """
                cursor_fac.execute(query_cab, (
                    id_cita_sel, id_paciente_sel, anticipo, subtotal, total_neto, 
                    regimen, iva, retencion, metodo_pago, observaciones
                ))
                id_factura_generada = cursor_fac.lastrowid

                # 2. Insertamos el desglose de los conceptos uno por uno
                query_det = """
                    INSERT INTO detalles_factura (id_factura, tipo_item, descripcion, cantidad, precio_unitario)
                    VALUES (%s, %s, %s, %s, %s)
                """
                for item in st.session_state['items_factura']:
                    cursor_fac.execute(query_det, (
                        id_factura_generada, item['tipo'], item['descripcion'], item['cantidad'], item['precio']
                    ))

                # 3. Forzamos a que la cita cambie automáticamente a estado 'Asistió' al facturarse
                cursor_fac.execute("UPDATE citas SET estado = 'Asistió' WHERE id_cita = %s", (id_cita_sel,))
                
                conn_fac.commit()
                cursor_fac.close()
                
                st.success("🎉 ¡Asiento contable registrado con éxito! Operación guardada para la próxima auditoría.")
                st.session_state['items_factura'] = []  # Vaciamos el carrito
                st.session_state['factura_activa'] = False  # Cerramos el módulo
                st.rerun()

            except Exception as e:
                st.error(f"Error crítico de persistencia: {e}")
            finally:
                if conn_fac:
                    conn_fac.close()
    else:
        st.info("El recibo está vacío. Añada conceptos desde el bloque de la derecha para calcular el desglose financiero.")
    

def validar_login(usuario, contra):
    try:
        conn = conectar_db()  # Forzamos la conexión TLS de TiDB Cloud
        cursor = conn.cursor()
        # Buscamos en tu tabla de usuarios de la nube
        query = "SELECT rol FROM usuarios WHERE username = %s AND password = %s"
        cursor.execute(query, (usuario, contra))
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        if resultado:
          return resultado[0] 
        return None
    except Exception as e:
        # Si da error de "Insecure transport", sabremos de inmediato qué función falta corregir
        st.error(f"Error en login: {e}")
        return None
    
if 'rol' not in st.session_state:
    st.session_state.rol = None

if 'usuario' not in st.session_state:
    st.session_state.usuario = None

# --- CONTROL DE ACCESO ---
if st.session_state.rol is None:
    st.title("🦷 DentCal: Acceso Clínico")
    with st.form("login_form"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Ingresar al Sistema"):
            rol_encontrado = validar_login(u, p)
            if rol_encontrado:
                st.session_state.rol = rol_encontrado
                st.session_state.usuario = u
                st.rerun()
            else:
                st.error("Credenciales incorrectas")
    st.stop()


def modulo_admin_usuarios():
    st.title("⚙️ Panel de Administración Maestro (DentCal)")
    st.info(f"Sesión iniciada como Administrador")

    conn = conectar_db()
    try:
        # 1. VISUALIZACIÓN DE USUARIOS
        st.write("### 👥 Personal en el Sistema")
        df_users = pd.read_sql("SELECT id_usuario, username, rol FROM usuarios", conn)
        st.dataframe(df_users, use_container_width=True)
        
        st.divider()

        # 2. GESTIÓN DE CREDENCIALES
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("### ➕ Registrar Nuevo Personal")
            with st.form("nuevo_user_form"):
                n_user = st.text_input("Nombre de Usuario:")
                n_pass = st.text_input("Contraseña:", type="password")
                n_rol = st.selectbox("Asignar Rol:", ["Odontologo", "Asistente", "Admin"])
                if st.form_submit_button("Crear Cuenta"):
                    if n_user and n_pass:
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO usuarios (username, password, rol) VALUES (%s, %s, %s)", 
                                       (n_user, n_pass, n_rol))
                        conn.commit()
                        st.success(f"Usuario {n_user} creado con éxito.")
                        st.rerun()
                    else:
                        st.warning("Por favor rellena todos los campos.")

        with col2:
            st.write("### 🔑 Gestionar Contraseña")
            with st.form("reset_pass_form"):
                user_sel = st.selectbox("Seleccionar Usuario:", options=df_users['username'].tolist())
                new_pass = st.text_input("Nueva Contraseña:", type="password")
                if st.form_submit_button("Actualizar Clave"):
                    if new_pass:
                        cursor = conn.cursor()
                        cursor.execute("UPDATE usuarios SET password = %s WHERE username = %s", 
                                       (new_pass, user_sel))
                        conn.commit()
                        st.success(f"Clave de {user_sel} actualizada.")
                    else:
                        st.warning("Escribe una nueva contraseña.")
                        
    except Exception as e:
        st.error(f"Error en panel admin: {e}")
    finally:
        if conn:
            conn.close()
            

def obtener_pacientes():
    try:
        conn = conectar_db()  # Usa la conexión TLS obligatoria de TiDB
        query = "SELECT id_paciente, nombre FROM pacientes"
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Error al obtener pacientes de la nube: {e}")
        return pd.DataFrame()  # Devuelve un contenedor vacío seguro si falla


def verificar_disponibilidad(fecha, hora_inicio, hora_fin):
    try:
        conn = conectar_db()  # Conexión directa a TiDB
        cursor = conn.cursor()
        query = """
            SELECT * FROM citas 
            WHERE fecha = %s AND NOT (%s >= hora_fin OR %s <= hora_inicio)
        """
        cursor.execute(query, (fecha, hora_inicio, hora_fin))
        resultado = cursor.fetchone()
        cursor.close()
        conn.close()
        return resultado is None  # Devuelve True si el espacio está libre
    except Exception as e:
        st.error(f"Error al verificar disponibilidad: {e}")
        return False




# --- NAVEGACIÓN PRINCIPAL Y SEGURIDAD ---
st.title("🦷 DentCal: Gestión Odontológica")

# =========================================================
# 🏥 COMPONENTE ESTÁNDAR: IDENTIDAD DE LA CLÍNICA
# =========================================================
NOMBRE_CLINICA = "Clínica Dental 'Tu Sonrisa'"
SLOGAN_CLINICA = "Cuidando tu salud bucal con excelencia"
TELEFONO_CLINICA = "+505 8888-8888"
HORARIO_CLINICA = "Lun - Sáb: 7:00 AM - 5:00 PM"

URL_LOGO = "https://cdn-icons-png.flaticon.com/512/3467/3467749.png"

css_clinica = """
<style>
.sidebar-logo-container {
    text-align: center;
    padding: 15px 10px;
    background-color: #f8f9fa;
    border-radius: 8px;
    margin-bottom: 20px;
    border: 1px solid #e9ecef;
}
.sidebar-logo-img {
    max-width: 110px;
    height: auto;
    border-radius: 50%;
    margin-bottom: 10px;
    object-fit: cover;
    background-color: #ffffff;
    box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
}
.sidebar-clinica-name {
    font-size: 16px !important;
    font-weight: bold !important;
    color: #1E3A8A !important;
    margin-bottom: 4px !important;
    line-height: 1.2;
}
.sidebar-clinica-slogan {
    font-size: 11px !important;
    color: #6B7280 !important;
    font-style: italic !important;
    margin-bottom: 8px !important;
    line-height: 1.3;
}
.sidebar-clinica-info {
    font-size: 11px !important;
    color: #374151 !important;
    margin-bottom: 2px !important;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
}
</style>
"""
st.sidebar.markdown(css_clinica, unsafe_allow_html=True)

html_clinica = f"""
<div class="sidebar-logo-container">
    <img src="{URL_LOGO}" class="sidebar-logo-img" alt="Logo">
    <div class="sidebar-clinica-name">{NOMBRE_CLINICA}</div>
    <div class="sidebar-clinica-slogan">{SLOGAN_CLINICA}</div>
    <hr style="margin: 8px 0; border: 0; border-top: 1px solid #e9ecef;">
    <div class="sidebar-clinica-info">📞 {TELEFONO_CLINICA}</div>
    <div class="sidebar-clinica-info">🕒 {HORARIO_CLINICA}</div>
</div>
"""
st.sidebar.markdown(html_clinica, unsafe_allow_html=True)
# =========================================================



# 1. Recuperamos el rol del usuario desde el st.session_state
rol_actual = st.session_state.get('rol', 'Asistente')

# 2. Mostramos el perfil de manera limpia arriba de las opciones
st.sidebar.markdown(f"### 👤 Usuario: `{st.session_state.get('usuario', 'Personal')}`")
st.sidebar.markdown(f"🔑 **Rol:** `{rol_actual}`")
st.sidebar.divider()

# 3. Filtramos las opciones del menú de acuerdo al rol asignado
opciones_menu = ["Agenda Diaria Sillon", "Pacientes y Expedientes"]

if rol_actual in ["Admin", "Odontologo"]:
    # Solo roles médicos o de administración agendan citas formalmente
    opciones_menu.insert(1, "Agendar Cita Dental")

if rol_actual == "Admin":
    # La pestaña de configuración es estrictamente de uso interno del administrador
    opciones_menu.append("Configuración")

# 4. Renderizamos el radio con la lista protegida y dinámica
menu = st.sidebar.radio("Navegación del Sistema", opciones_menu)

# 5. BOTÓN DE CERRAR SESIÓN (Ubicado al final de la barra lateral)
st.sidebar.divider()
if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True, type="secondary"):
    # Destruimos todas las variables temporales del login
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.success("Cerrando sesión de forma segura...")
    t_sleep.sleep(0.6)
    st.rerun()

if menu == "Agenda Diaria Sillon":
    st.subheader("📋 Control de Citas y Búsqueda")
    
    # Separamos limpiamente en tres pestañas
    tab_agenda, tab_buscador, tab_auditoria, tab_facturacion = st.tabs([
        "🕒 Vista del Día", 
        "🔍 Buscar Cita por Nombre", 
        "📊 Auditoría e Historial",
    "💰 Facturación y Caja Chica"
    ])

    # ==========================================
    # PESTAÑA 1: VISTA DE LA AGENDA DIARIA
    # ==========================================
    with tab_agenda:
        st.subheader("📋 Control de Citas del Día")
        fecha_agenda = st.date_input("Ver día:", value=datetime.now(), key="agenda_fecha_diaria")
        
        # Formateamos la fecha como texto estable para evitar problemas de tipos con TiDB
        fecha_str = fecha_agenda.strftime("%Y-%m-%d")
        
        conn = conectar_db()
        query = """
            SELECT c.id_cita, c.hora_inicio, c.hora_fin, p.nombre, IFNULL(p.cedula, 'S/N') as cedula, c.estado 
            FROM citas c 
            JOIN pacientes p ON c.id_paciente = p.id_paciente 
            WHERE c.fecha = %s 
            ORDER BY c.hora_inicio ASC
        """
        try:
            # Pasamos la fecha usando tupla de parámetros seguros
            df_todas = pd.read_sql(query, conn, params=[fecha_str])
            
            # Inicializamos df_activas vacío por si df_todas no tiene registros
            df_activas = pd.DataFrame()
            if not df_todas.empty:
                df_activas = df_todas[df_todas['estado'] != 'Cancelada']
            
            # --- 🕒 LÓGICA DE OCUPACIÓN Y ESTADÍSTICAS ---
            horas_base = range(7, 18)  # De 7 AM a 5 PM
            
            # Contamos cuántas citas reales (únicas) hay hoy
            total_citas_hoy = len(df_activas) if not df_activas.empty else 0

            # --- MAPA DE DISPONIBILIDAD ENCAPSULADO POR HORA ---
            st.write("### 🕒 Ocupación Diaria")
            
            # Métrica de control rápida
            st.metric(label="📅 Citas programadas para hoy", value=f"{total_citas_hoy} paciente(s)")
            st.write("") 

            # 1. CSS dinámico para la nueva cuadrícula de horas completas
            css_bloques = """
            <style>
            .hour-container {
                display: grid !important;
                grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)) !important;
                gap: 12px !important;
                font-family: Arial, sans-serif;
                margin-bottom: 25px;
                width: 100%;
            }
            .hour-card {
                border: 1px solid #b5b5b5;
                padding: 14px 8px;
                text-align: center;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
                box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
                position: relative;
                color: #222222;
            }
            .top-indicator {
                display: block;
                font-size: 11px;
                font-weight: normal;
                color: #444444;
                margin-bottom: 4px;
                background: rgba(255,255,255,0.7);
                border-radius: 3px;
                padding: 1px 2px;
            }
            .time-label {
                font-size: 16px;
                display: block;
                margin-top: 2px;
            }
            </style>
            """
            st.markdown(css_bloques, unsafe_allow_html=True)
            html_grid = "<div class='hour-container'>"

            # 2. Iteramos únicamente por hora entera con la matemática de cuartos blindada
            for hora in horas_base:
                estados_cuartos = []
                ultimo_bloque_ocupado = None
                pacientes_de_la_hora = set()  # Usamos un set para almacenar nombres únicos en esta hora entera
                
                # Evaluamos de forma individual los 4 cuartos de esta hora
                for cuarto in [0, 15, 30, 45]:
                    bloque_inicio = time(hora, cuarto)
                    # Manejo seguro para el límite de las 24 horas si fuese necesario
                    bloque_fin = (datetime.combine(date.today(), bloque_inicio) + timedelta(minutes=15)).time()
                    
                    ocupado = False
                    if not df_activas.empty:
                        for _, r in df_activas.iterrows():
                            inicio_cita = (datetime.min + r['hora_inicio']).time() if isinstance(r['hora_inicio'], timedelta) else r['hora_inicio']
                            fin_cita = (datetime.min + r['hora_fin']).time() if isinstance(r['hora_fin'], timedelta) else r['hora_fin']
                            
                            if bloque_inicio < fin_cita and bloque_fin > inicio_cita:
                                ocupado = True
                                pacientes_de_la_hora.add(r['nombre'])  # Capturamos el nombre de quien ocupa este cuarto
                                break
                    
                    if ocupado:
                        estados_cuartos.append(1)
                        ultimo_bloque_ocupado = bloque_fin
                    else:
                        estados_cuartos.append(0)
                
                # --- CONSTRUCCIÓN DEL TEXTO INFORMATIVO ---
                cuartos_ocupados = sum(estados_cuartos)
                
                if cuartos_ocupados == 4:
                    texto_arriba = "Ocupado"
                elif cuartos_ocupados > 0 and ultimo_bloque_ocupado:
                    texto_arriba = f"Hasta las {ultimo_bloque_ocupado.strftime('%H:%M')}"
                else:
                    texto_arriba = "Disponible"
                
                # --- CONSTRUCCIÓN DEL TEXTO DEL HOVER (TOOLTIP NATIVO) ---
                if pacientes_de_la_hora:
                    tooltip_texto = f"Paciente(s): {', '.join(pacientes_de_la_hora)}"
                else:
                    tooltip_texto = "Horario Disponible"
                
                # --- MAQUILLAJE DE FONDOS CON CSS ---
                if cuartos_ocupados == 4:
                    estilo_fondo = "background-color: #FFD2D2; border-color: #D8000C; color: #D8000C;"
                elif cuartos_ocupados == 0:
                    estilo_fondo = "background-color: #DFF2BF; border-color: #4F8A10; color: #4F8A10;"
                else:
                    partes_css = []
                    for i, estado in enumerate(estados_cuartos):
                        color = "#FFD2D2" if estado == 1 else "#DFF2BF"
                        inicio_pct = i * 25
                        fin_pct = (i + 1) * 25
                        partes_css.append(f"{color} {inicio_pct}%, {color} {fin_pct}%")
                    
                    degradado_completo = ", ".join(partes_css)
                    estilo_fondo = f"background: linear-gradient(to right, {degradado_completo}); border-color: #cca4a4;"

                html_grid += f"<div class='hour-card' style='{estilo_fondo}' title='{tooltip_texto}'><span class='top-indicator'>📋 {texto_arriba}</span><span class='time-label'>{hora:02d}:00</span></div>"

            html_grid += "</div>"
            st.markdown(html_grid, unsafe_allow_html=True)
            st.divider()

        except Exception as e:
            st.error(f"Error en Agenda: {e}")
        finally:
            if conn:
                conn.close()

     
    # --- 3. DETALLE Y ASISTENCIA ---
    st.write("### 📝 Control de Asistencia y Reprogramación")
    if df_todas.empty:
        st.info("No hay pacientes agendados para esta fecha.")
    else:
        for _, row in df_todas.iterrows():
            h_i_obj = (datetime.min + row['hora_inicio']).time() if isinstance(row['hora_inicio'], timedelta) else row['hora_inicio']
            h_f_obj = (datetime.min + row['hora_fin']).time() if isinstance(row['hora_fin'], timedelta) else row['hora_fin']
            time_range = f"{h_i_obj.strftime('%H:%M')} - {h_f_obj.strftime('%H:%M')}"
            estado_actual = row['estado']
            
            with st.expander(f"⏰ {time_range} | 👤 {row['nombre']} ({estado_actual})"):
                st.write(f"**Cédula/ID:** {row['cedula']}")
                contenedor_mensaje = st.empty()
                lista_estados = ["Pendiente", "Asistió", "Ausente", "Cancelada"]
                
                # --- PARTE A: CONTROL DE ESTADOS CON CANDADO DE INMUTABILIDAD ---
                if estado_actual in ["Cancelada", "Ausente", "Liquidada"]:
                    if estado_actual == "Liquidada":
                        st.success("🔒 **Registro Cerrado:** Esta cita ya fue cobrada y asentada en caja. No admite cambios.")
                    elif estado_actual == "Ausente":
                        # Validamos si hubo retención de dinero en este registro cerrado
                        anticipo_ret = row.get('anticipo_retenido', 0.0)
                        if anticipo_ret > 0:
                            st.error(f"🔒 **Paciente Ausente:** Se penalizó al paciente reteniendo C$ {anticipo_ret:.2f} del anticipo en Caja Chica.")
                        else:
                            st.error("🔒 **Registro Cerrado:** Paciente marcado como Ausente. Sin anticipos que penalizar.")
                    elif estado_actual == "Cancelada":
                        st.warning("🔒 **Registro Cerrado:** Cita Cancelada. No se permite volver a editar.")
                    
                    st.selectbox("Estado del Turno:", [estado_actual], index=0, disabled=True, key=f"upd_{row['id_cita']}")
                    
                    if estado_actual == "Liquidada":
                        if st.button("🖨️ Ver Factura en Caja", key=f"liq_locked_{row['id_cita']}", use_container_width=True):
                            st.session_state['id_cita_facturar'] = row['id_cita']
                            st.session_state['id_paciente_facturar'] = row.get('id_paciente', None)
                            st.session_state['nombre_paciente_facturar'] = row['nombre']
                            st.rerun()
                else:
                    # --- FLUJO ACTIVO: PENDIENTE O ASISTIÓ ---
                    idx_actual = lista_estados.index(estado_actual) if estado_actual in lista_estados else 0
                    nuevo_estado = st.selectbox("Actualizar estado:", lista_estados, index=idx_actual, key=f"upd_{row['id_cita']}")
                    
                    # ENTRADA DE ANTICIPO: Se habilita únicamente si la cita aún está 'Pendiente'
                    anticipo_actual = float(row.get('anticipo', 0.0))
                    if estado_actual == "Pendiente":
                        nuevo_anticipo = st.number_input(
                            "Registrar Anticipo / Adelanto (C$):", 
                            min_value=0.0, 
                            value=anticipo_actual, 
                            step=50.0, 
                            key=f"anti_{row['id_cita']}"
                        )
                    else:
                        # Si ya está en 'Asistió', solo mostramos de forma informativa cuánto dejó
                        st.info(f"💰 Este paciente cuenta con un anticipo registrado de: C$ {anticipo_actual:.2f}")
                        nuevo_anticipo = anticipo_actual

                    # Si el usuario selecciona 'Ausente' y el paciente tenía dinero abonado, desplegamos la regla de penalización
                    porcentaje_retencion = 0
                    if nuevo_estado == "Ausente" and anticipo_actual > 0:
                        st.warning(f"⚠️ El paciente abonó C$ {anticipo_actual:.2f}. Aplica penalización por inasistencia:")
                        porcentaje_retencion = st.slider("Porcentaje a retener para la clínica (%):", 0, 100, 50, key=f"p_ret_{row['id_cita']}")
                        monto_a_retener = (anticipo_actual * porcentaje_retencion) / 100
                        st.info(f"Se ingresarán C$ {monto_a_retener:.2f} a Caja Chica y se deberán devolver C$ {anticipo_actual - monto_a_retener:.2f} al paciente.")

                    col_btn_guardar, col_btn_liquidar = st.columns(2)
                    
                    with col_btn_guardar:
                        if st.button("Guardar Cambio", key=f"btn_{row['id_cita']}", use_container_width=True):
                            ahora = datetime.now()
                            fecha_segura = fecha_agenda.date() if isinstance(fecha_agenda, datetime) else fecha_agenda
                            momento_exacto_cita = datetime.combine(fecha_segura, h_i_obj)
                            
                            if nuevo_estado == "Asistió" and ahora < momento_exacto_cita:
                                contenedor_mensaje.error(f"❌ **Restricción de tiempo:** No se puede marcar asistencia antes del inicio programado.")
                                t_sleep.sleep(2)
                                contenedor_mensaje.empty()
                            else:
                                conn_accion = None
                                try:
                                    conn_accion = conectar_db()
                                    cursor_accion = conn_accion.cursor()
                                    
                                    # Caso A: El usuario decide penalizar la ausencia en este momento
                                    if nuevo_estado == "Ausente" and anticipo_actual > 0:
                                        monto_penalizado = (anticipo_actual * porcentaje_retencion) / 100
                                        # Actualizamos la cita fijando lo retenido
                                        cursor_accion.execute(
                                            "UPDATE citas SET estado = %s, anticipo_retenido = %s WHERE id_cita = %s",
                                            (nuevo_estado, monto_penalizado, row['id_cita'])
                                        )
                                        # Opcional: Inyectar directamente a tu tabla contable de ingresos el dinero penalizado
                                        cursor_accion.execute(
                                            "INSERT INTO ingresos (id_cita, id_paciente, monto, concepto, fecha) VALUES (%s, %s, %s, 'Penalización por Ausencia', NOW())",
                                            (row['id_cita'], row.get('id_paciente'), monto_penalizado)
                                        )
                                    else:
                                        # Caso B: Actualización estándar de estado y/o registro de anticipo inicial
                                        cursor_accion.execute(
                                            "UPDATE citas SET estado = %s, anticipo = %s WHERE id_cita = %s",
                                            (nuevo_estado, nuevo_anticipo, row['id_cita'])
                                        )
                                        
                                    conn_accion.commit()
                                    cursor_accion.close()
                                    
                                    contenedor_mensaje.success("Datos guardados correctamente.")
                                    t_sleep.sleep(1)
                                    st.rerun()
                                except Exception as ex_db:
                                    st.error(f"Error al actualizar la cita: {ex_db}")
                                finally:
                                    if conn_accion: conn_accion.close()

    # ==========================================
    # PESTAÑA 2: BUSCADOR DE CITAS POR NOMBRE
    # ==========================================
    with tab_buscador:
        st.write("### 🔍 Localizador de Citas Olvidadas")
        nombre_buscar = st.text_input("Escribe el nombre del paciente a consultar:", placeholder="Ej. Josue Ferrey")
        
        if nombre_buscar:
            conn = conectar_db()
            # Modificada la consulta para extraer explícitamente c.id_paciente para el cobro desde aquí también
            query_buscar = """
                SELECT p.nombre, c.fecha, c.hora_inicio, c.hora_fin, c.estado, c.id_cita, c.id_paciente
                FROM citas c
                JOIN pacientes p ON c.id_paciente = p.id_paciente
                WHERE p.nombre LIKE %s
                ORDER BY c.fecha DESC, c.hora_inicio DESC
            """
            try:
                search_term = f"%{nombre_buscar}%"
                df_busqueda = pd.read_sql(query_buscar, conn, params=[search_term])
                
                if not df_busqueda.empty:
                    st.success(f"🎉 Se encontraron {len(df_busqueda)} registros:")
                    
                    # Renderizamos los expanders o botones en el buscador para cobrar directo desde aquí si gustas
                    df_visual = df_busqueda.copy()
                    df_visual['fecha'] = pd.to_datetime(df_visual['fecha']).dt.strftime('%d-%m-%Y')
                    
                    df_visual['hora_inicio'] = df_visual['hora_inicio'].apply(lambda x: (datetime.min + x).time().strftime('%H:%M') if isinstance(x, timedelta) else x.strftime('%H:%M'))
                    df_visual['hora_fin'] = df_visual['hora_fin'].apply(lambda x: (datetime.min + x).time().strftime('%H:%M') if isinstance(x, timedelta) else x.strftime('%H:%M'))
                    
                    # Seleccionamos solo las columnas visuales para el dataframe público
                    df_publico = df_visual[["nombre", "fecha", "hora_inicio", "hora_fin", "estado"]].copy()
                    df_publico.columns = ["Paciente", "Fecha Programada", "Hora Inicio", "Hora Fin", "Estado Actual"]
                    st.dataframe(df_publico, use_container_width=True)
                    
                    # Añadimos un selector rápido por si quieren liquidar desde los resultados de búsqueda
                    st.markdown("##### 💵 Cobro rápido desde el Buscador")
                    opciones_citas = {f"Cita #{r['id_cita']} - {r['nombre']} ({r['fecha']})": r for _, r in df_visual.iterrows()}
                    cita_seleccionada_busq = st.selectbox("Selecciona una cita encontrada para liquidar:", ["-- Seleccionar --"] + list(opciones_citas.keys()))
                    
                    if cita_seleccionada_busq != "-- Seleccionar --":
                        datos_cita = opciones_citas[cita_seleccionada_busq]
                        if st.button("🚀 Cargar Factura de esta Cita", use_container_width=True):
                            st.session_state['id_cita_facturar'] = datos_cita['id_cita']
                            st.session_state['id_paciente_facturar'] = datos_cita['id_paciente']
                            st.session_state['nombre_paciente_facturar'] = datos_cita['nombre']
                            st.toast("✅ Datos cargados. ¡Ve a la pestaña de Facturación!")
                            st.rerun()
                else:
                    st.warning(f"❌ No se encontró ninguna cita registrada para: '{nombre_buscar}'")
            except Exception as e:
                st.error(f"Error en la búsqueda: {e}")
            finally:
                if conn:
                    conn.close()
        else:
            st.info("💡 Escribe el nombre del paciente para ver qué día y a qué hora tiene citas asignadas en el sistema.")

    # ==========================================
    # PESTAÑA 3: AUDITORÍA E HISTORIAL
    # ==========================================
    with tab_auditoria:
        st.write("### 📊 Historial y Auditoría Global de Citas")
        st.write("Consulte y supervise el estado de todos los turnos históricos asentados en el sistema.")
        
        c1, c2, c3 = st.columns(3)
        fecha_inicio = c1.date_input("Desde:", value=date.today() - timedelta(days=7), key="audit_desde")
        fecha_fin = c2.date_input("Hasta:", value=date.today() + timedelta(days=15), key="audit_hasta")
        
        estados_seleccionados = c3.multiselect(
            "Filtrar por Estado:",
            options=["Pendiente", "Asistió", "Ausente", "Cancelada"],
            default=["Cancelada", "Ausente", "Asistió"],
            key="audit_estados"
        )

        if fecha_inicio > fecha_fin:
            st.error("❌ La fecha de inicio no puede ser mayor a la fecha de fin.")
        else:
            conn_audit = None
            df_auditoria = pd.DataFrame()
            try:
                conn_audit = conectar_db()
                cursor_audit = conn_audit.cursor()
                query_audit = """
                    SELECT c.id_cita, c.fecha, c.hora_inicio, c.hora_fin, p.nombre, 
                           IFNULL(p.cedula, 'S/N') as cedula, c.estado 
                    FROM citas c 
                    JOIN pacientes p ON c.id_paciente = p.id_paciente 
                    WHERE c.fecha BETWEEN %s AND %s
                    ORDER BY c.fecha DESC, c.hora_inicio ASC
                """
                cursor_audit.execute(query_audit, (fecha_inicio, fecha_fin))
                columnas = [desc[0] for desc in cursor_audit.description]
                df_auditoria = pd.DataFrame(cursor_audit.fetchall(), columns=columnas)
                cursor_audit.close()
            except Exception as e:
                st.error(f"Error al cargar la auditoría: {e}")
            finally:
                if conn_audit:
                    conn_audit.close()

            if not df_auditoria.empty and estados_seleccionados:
                df_auditoria = df_auditoria[df_auditoria['estado'].isin(estados_seleccionados)]

            st.write("---")
            st.write(f"#### 📋 Registros Encontrados ({len(df_auditoria)} cita/s)")

            if df_auditoria.empty:
                st.info("No se encontraron registros históricos para los filtros seleccionados.")
            else:
                st.write("### 📥 Exportar Reporte")
                col_xl, col_pdf = st.columns(2)

                # ---- EXCEL ----
                with col_xl:
                    buffer_excel = BytesIO()
                    df_exportar = df_auditoria.copy()
                    
                    for col_time in ['hora_inicio', 'hora_fin']:
                        df_exportar[col_time] = df_exportar[col_time].apply(
                            lambda x: (datetime.min + x).time().strftime('%H:%M') if isinstance(x, timedelta) else str(x)[:5]
                        )
                    df_exportar['fecha'] = df_exportar['fecha'].apply(
                        lambda x: x.strftime('%Y-%m-%d') if isinstance(x, (date, datetime)) else str(x)
                    )
                    
                    df_exportar.columns = ['ID Cita', 'Fecha', 'Hora Inicio', 'Hora Fin', 'Paciente', 'Cédula/ID', 'Estado']
                    with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
                        df_exportar.to_excel(writer, index=False, sheet_name='Auditoría de Citas')
                    
                    st.download_button(
                        label="🟢 Descargar Reporte en Excel",
                        data=buffer_excel.getvalue(),
                        file_name=f"Auditoria_DentCal_{fecha_inicio}_al_{fecha_fin}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="btn_download_excel"
                    )

                # ---- PDF (REPORTLAB) ----
                with col_pdf:
                    buffer_pdf = BytesIO()
                    doc = SimpleDocTemplate(
                        buffer_pdf, 
                        pagesize=letter,
                        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
                    )
                    
                    story = []
                    styles = getSampleStyleSheet()
                    
                    estilo_titulo = ParagraphStyle('TituloPDF', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor('#1f3864'), spaceAfter=10)
                    estilo_sub = ParagraphStyle('SubPDF', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#555555'), spaceAfter=20)
                    estilo_celda = ParagraphStyle('CeldaPDF', parent=styles['Normal'], fontSize=9, leading=11)
                    estilo_cabecera = ParagraphStyle('CabeceraPDF', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.white)

                    story.append(Paragraph("🦷 DentCal: Reporte de Auditoría Clínica", estilo_titulo))
                    story.append(Paragraph(f"Rango consultado: Desde {fecha_inicio.strftime('%d/%m/%Y')} hasta {fecha_fin.strftime('%d/%m/%Y')} | Generado el: {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilo_sub))
                    story.append(Spacer(1, 10))

                    tabla_datos = [[
                        Paragraph("Fecha", estilo_cabecera), 
                        Paragraph("Horario", estilo_cabecera), 
                        Paragraph("Paciente", estilo_cabecera), 
                        Paragraph("Cédula/ID", estilo_cabecera), 
                        Paragraph("Estado", estilo_cabecera)
                    ]]

                    for _, r in df_auditoria.iterrows():
                        f_txt = r['fecha'].strftime('%d/%m/%Y') if isinstance(r['fecha'], (date, datetime)) else str(r['fecha'])
                        h_i = (datetime.min + r['hora_inicio']).time().strftime('%H:%M') if isinstance(r['hora_inicio'], timedelta) else str(r['hora_inicio'])[:5]
                        h_f = (datetime.min + r['hora_fin']).time().strftime('%H:%M') if isinstance(r['hora_fin'], timedelta) else str(r['hora_fin'])[:5]
                        
                        tabla_datos.append([
                            Paragraph(f_txt, estilo_celda),
                            Paragraph(f"{h_i} - {h_f}", estilo_celda),
                            Paragraph(r['nombre'], estilo_celda),
                            Paragraph(r['cedula'], estilo_celda),
                            Paragraph(r['estado'], estilo_celda)
                        ])

                    tabla_pdf = Table(tabla_datos, colWidths=[70, 85, 180, 100, 80])
                    tabla_pdf.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1f3864')),
                        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                        ('BOTTOMPADDING', (0,0), (-1,0), 8),
                        ('TOPPADDING', (0,0), (-1,0), 8),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e0e0e0')),
                        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f9fbfd')])
                    ]))
                    
                    story.append(tabla_pdf)
                    doc.build(story)
                    
                    st.download_button(
                        label="🔴 Descargar Reporte en PDF",
                        data=buffer_pdf.getvalue(),
                        file_name=f"Reporte_DentCal_{fecha_inicio}_al_{fecha_fin}.pdf",
                        mime="application/pdf",
                        key="btn_download_pdf"
                    )
                
                st.write("---")

                # --- RENDERIZADO VISUAL EN LA INTERFAZ ---
                for fecha_grupo, df_dia in df_auditoria.groupby('fecha', sort=False):
                    fecha_bonita = fecha_grupo.strftime('%A, %d de %B de %Y') if isinstance(fecha_grupo, (date, datetime)) else str(fecha_grupo)
                    st.markdown(f"##### 📅 {fecha_bonita}")
                    
                    html_cards = "<div style='display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 15px;'>"
                    for _, row_card in df_dia.iterrows():
                        h_i_txt = (datetime.min + row_card['hora_inicio']).time().strftime('%H:%M') if isinstance(row_card['hora_inicio'], timedelta) else str(row_card['hora_inicio'])[:5]
                        
                        if row_card['estado'] == "Ausente":
                            style_bg = "background-color: #ffcccc; border-left: 5px solid #ff0000; color: #a00;"
                        elif row_card['estado'] == "Cancelada":
                            style_bg = "background-color: #e2f0d9; border-left: 5px solid #70ad47; color: #385723;"
                        elif row_card['estado'] == "Asistió":
                            style_bg = "background-color: #d9e1f2; border-left: 5px solid #4472c4; color: #1f3864;"
                        else:
                            style_bg = "background-color: #fff2cc; border-left: 5px solid #ffc000; color: #7f6000;"
                        
                        html_cards += f"""
                        <div style='padding: 8px 12px; border-radius: 6px; min-width: 130px; text-align: center; font-size: 12px; font-weight: bold; {style_bg}'>
                            <span>{row_card['estado']}</span><br>
                            <span style='font-size: 11px; font-weight: normal; color: #333;'>{row_card['nombre'].split()[0]}</span><br>
                            <span style='font-size: 14px;'>{h_i_txt}</span>
                        </div>
                        """
                    html_cards += "</div>"
                    st.markdown(html_cards, unsafe_allow_html=True)
                    
                    for _, row in df_dia.iterrows():
                        h_i_obj = (datetime.min + row['hora_inicio']).time() if isinstance(row['hora_inicio'], timedelta) else row['hora_inicio']
                        h_f_obj = (datetime.min + row['hora_fin']).time() if isinstance(row['hora_fin'], timedelta) else row['hora_fin']
                        time_range = f"{h_i_obj.strftime('%H:%M')} - {h_f_obj.strftime('%H:%M')}"
                        
                        emoji_estado = "⚪" if row['estado'] == "Cancelada" else "❌" if row['estado'] == "Ausente" else "✅" if row['estado'] == "Asistió" else "⏰"
                        
                        with st.expander(f"{emoji_estado} {time_range} | 👤 {row['nombre']} ({row['estado']})"):
                            st.write(f"**Cédula/ID:** {row['cedula']}")
                            st.write(f"**Horario del bloque:** {time_range}")
                            st.info(f"🔒 **Control de Historial:** Este registro se mantiene preservado como auditoría clínica.")
                    st.write("")
    
    
# --- PESTAÑA 4: MÓDULO DE FACTURACIÓN Y LIQUIDACIÓN ---

    with tab_facturacion:
    # 0. ASEGURAR EXISTENCIA DE LA TABLA INGRESOS (CON COLUMNA CONCEPTO)
        try:
            conn_init = conectar_db()
            with conn_init.cursor() as cursor_init:
                cursor_init.execute("""
                    CREATE TABLE IF NOT EXISTS ingresos (
                        id_ingreso INT AUTO_INCREMENT PRIMARY KEY,
                        id_cita INT NOT NULL,
                        id_paciente INT NOT NULL,
                        monto DECIMAL(10,2) NOT NULL,
                        concepto VARCHAR(100) DEFAULT 'Saldo Liquidación Cita',
                        fecha DATETIME NOT NULL
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
                """)
            conn_init.commit()
        except Exception as e_init:
            st.caption(f"Verificación de base de datos activa: {e_init}")
        finally:
            if 'conn_init' in locals() and conn_init:
                conn_init.close()

        # 1. Recuperamos los datos de la sesión del paciente seleccionado
        id_cita_sel = st.session_state.get('id_cita_facturar')
        id_paciente_sel = st.session_state.get('id_paciente_facturar')
        nombre_paciente = st.session_state.get('nombre_paciente_facturar')

        if id_cita_sel:
            col_info_pago, col_limpiar = st.columns([0.8, 0.2])
            with col_info_pago:
                st.success(f"🛒 **Cuenta Activa:** Facturando a **{nombre_paciente}** (Cita #{id_cita_sel})")
            with col_limpiar:
                if st.button("❌ Cancelar Cobro", use_container_width=True):
                    del st.session_state['id_cita_facturar']
                    del st.session_state['id_paciente_facturar']
                    del st.session_state['nombre_paciente_facturar']
                    if 'pago_exitoso' in st.session_state: del st.session_state['pago_exitoso']
                    st.rerun()
            
            st.write("---")
            
            # Rescate de ID de paciente por seguridad
            id_p_seguro = id_paciente_sel if id_paciente_sel is not None else 1
            
            # Mostramos tu interfaz maestra (Clasificación Contable, Abonos, Totales)
            mostrar_modulo_facturacion(id_cita_sel, id_p_seguro, nombre_paciente)
            
            st.write("---")
            st.markdown("### 🖨️ Finalizar Transacción y Emitir Comprobante")
            
            # --- 2. LEER EL ANTICIPO DESDE LA BASE DE DATOS EN TIEMPO REAL ---
            anticipo_abonado = 0.0
            try:
                conn_f = conectar_db()
                with conn_f.cursor() as cur_f:
                    cur_f.execute("SELECT anticipo FROM citas WHERE id_cita = %s", (id_cita_sel,))
                    res_f = cur_f.fetchone()
                    if res_f:
                        anticipo_abonado = float(res_f[0])
            except Exception:
                pass
            finally:
                if 'conn_f' in locals() and conn_f: conn_f.close()

            # Leemos el monto bruto calculado final de tu balance contable
            monto_base = st.session_state.get('monto_calculado_neto', 305.00)
            
            # Aplicamos el descuento contable si existe anticipo previo
            if anticipo_abonado > 0:
                st.warning(f"📉 **Descuento por Anticipo Aplicado:** - C$ {anticipo_abonado:.2f}")
                monto_a_cobrar = max(0.0, monto_base - anticipo_abonado)
            else:
                monto_a_cobrar = monto_base

            st.markdown(f"#### **Total Neto a Liquidar hoy en Caja:** C$ {monto_a_cobrar:.2f}")
            
            # Si no se ha asentado el pago, mostramos el botón de acción principal
            if not st.session_state.get('pago_exitoso'):
                if st.button("🔒 Confirmar Pago y Asentar en Libros", type="primary", use_container_width=True):
                    try:
                        conn = conectar_db()
                        with conn.cursor() as cursor:
                            # Insertamos el dinero real ingresado con su respectivo concepto
                            sql_insert = """
                                INSERT INTO ingresos (id_cita, id_paciente, monto, concepto, fecha) 
                                VALUES (%s, %s, %s, 'Saldo Liquidación Cita', NOW())
                            """
                            cursor.execute(sql_insert, (id_cita_sel, id_p_seguro, monto_a_cobrar))
                            
                            # CAMBIO CLAVE: El estado pasa a 'Liquidada' para congelar el turno de por vida
                            cursor.execute("UPDATE citas SET estado = 'Liquidada' WHERE id_cita = %s", (id_cita_sel,))
                        conn.commit()
                        
                        st.session_state['pago_exitoso'] = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al registrar en la base de datos: {e}")
                    finally:
                        if 'conn' in locals() and conn: conn.close()
            
            # Si el pago ya fue asentado con éxito, liberamos las opciones de exportación
            if st.session_state.get('pago_exitoso'):
                st.info("🎉 ¡El pago ha sido registrado con éxito en el sistema!")
                
                c_down, c_wa, c_em = st.columns(3)
                with c_down:
                    import base64
                    from reportlab.lib.pagesizes import letter
                    from reportlab.platypus import SimpleDocTemplate, Paragraph
                    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                    from reportlab.lib import colors
                    import io

                    try:
                        buffer = io.BytesIO()
                        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
                        story = []
                        styles = getSampleStyleSheet()
                        
                        title_style = ParagraphStyle('TStyle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor("#1E3A8A"), spaceAfter=12)
                        normal_style = ParagraphStyle('NStyle', parent=styles['Normal'], fontSize=11, spaceAfter=6)
                        
                        story.append(Paragraph("🦷 DENTCAL - CONTROL PROFESIONAL", title_style))
                        story.append(Paragraph(f"<b>Recibo de Pago - Cita #{id_cita_sel}</b>", normal_style))
                        story.append(Paragraph(f"<b>Paciente:</b> {nombre_paciente}", normal_style))
                        story.append(Paragraph(f"<b>Monto Neto Recaudado:</b> C$ {monto_a_cobrar:,.2f}", normal_style))
                        if anticipo_abonado > 0:
                            story.append(Paragraph(f"<b>Anticipo Aplicado:</b> C$ {anticipo_abonado:,.2f}", normal_style))
                        story.append(Paragraph(f"<b>Fecha de Emisión:</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}", normal_style))
                        
                        doc.build(story)
                        pdf_bytes = buffer.getvalue()
                        
                        b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                        nombre_archivo = f"Recibo_Cita_{id_cita_sel}.pdf"
                        
                        html_boton_descarga = f'''
                            <a href="data:application/pdf;base64,{b64_pdf}" download="{nombre_archivo}" style="text-decoration: none;">
                                <button style="width:100%; height:38px; background-color:#1E3A8A; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">
                                    📥 Descargar PDF Comercial
                                </button>
                            </a>
                        '''
                        st.markdown(html_boton_descarga, unsafe_allow_html=True)
                    except Exception as e_pdf:
                        st.caption("Preparando visor de impresión...")
                
                with c_wa:
                    import urllib.parse
                    texto_wa = f"Hola {nombre_paciente}, confirmamos el pago de tu consulta por C$ {monto_a_cobrar:,.2f}. ¡Muchas gracias!"
                    url_wa = f"https://wa.me/?text={urllib.parse.quote(texto_wa)}"
                    st.markdown(f'<a href="{url_wa}" target="_blank"><button style="width:100%; height:38px; background-color:#25D366; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">💬 Enviar WhatsApp</button></a>', unsafe_allow_html=True)
                    
                with c_em:
                    import urllib.parse
                    asunto_m = f"Comprobante DentCal - Cita #{id_cita_sel}"
                    cuerpo_m = f"Estimado/a {nombre_paciente},\n\nConfirmamos su pago de C$ {monto_a_cobrar:,.2f}.\n\nSaludos."
                    url_m = f"mailto:?subject={urllib.parse.quote(asunto_m)}&body={urllib.parse.quote(cuerpo_m)}"
                    st.markdown(f'<a href="{url_m}"><button style="width:100%; height:38px; background-color:#EA4335; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">✉️ Enviar Correo</button></a>', unsafe_allow_html=True)
                
                st.write(" ")
                if st.button("🔄 Concluir Atención y Limpiar Caja", use_container_width=True):
                    del st.session_state['id_cita_facturar']
                    del st.session_state['id_paciente_facturar']
                    del st.session_state['nombre_paciente_facturar']
                    if 'pago_exitoso' in st.session_state: del st.session_state['pago_exitoso']
                    st.rerun()

        else:
            st.info("💡 **Sin transacciones activas:** Ve a la pestaña 'Vista del Día' o 'Buscar Cita por Nombre' y presiona el botón '💵 Cobrar / Liquidar' en el paciente correspondiente para cargar la caja.")

        # =====================================================================
        # 📊 AUDITORÍA GENERAL DE INGRESOS DIARIOS (CAJA DEL DÍA)
        # =====================================================================
        st.write("---")
        st.markdown("### 📈 Historial de Recaudación y Caja Chica (Hoy)")
        
        conn_historial = None
        try:
            conn_historial = conectar_db()
            # SELECT modificado para extraer la nueva columna de conceptos
            query_ingresos = """
                SELECT i.id_ingreso, p.nombre AS paciente, i.monto, i.concepto, i.fecha 
                FROM ingresos i
                JOIN pacientes p ON i.id_paciente = p.id_paciente
                WHERE DATE(i.fecha) = CURDATE()
                ORDER BY i.fecha DESC
            """
            df_ingresos = pd.read_sql(query_ingresos, conn_historial)
            
            if not df_ingresos.empty:
                df_ingresos['monto'] = df_ingresos['monto'].apply(lambda x: f"C$ {x:,.2f}")
                df_ingresos['fecha'] = pd.to_datetime(df_ingresos['fecha']).dt.strftime('%H:%M:%S')
                # Mapeo de columnas ajustado incluyendo el campo "Concepto"
                df_ingresos.columns = ["ID Ingreso", "Paciente", "Monto Recaudado", "Concepto", "Hora de Pago"]
                
                with conn_historial.cursor() as cur_t:
                    cur_t.execute("SELECT SUM(monto) FROM ingresos WHERE DATE(fecha) = CURDATE()")
                    total_dia = cur_t.fetchone()[0] or 0.0
                
                st.metric(label="💰 Total Recaudado en Caja Hoy", value=f"C$ {total_dia:,.2f}")
                st.dataframe(df_ingresos, use_container_width=True)
            else:
                st.warning("📭 Aún no se han registrado cobros ni entradas de dinero el día de hoy.")
                
        except Exception as e_hist:
            st.caption("Historial en espera de transacciones.")
        finally:
            if conn_historial: 
                conn_historial.close()
        
# --- MÓDULO 2: AGENDAR CITA ---
elif menu == "Agendar Cita Dental":
    st.subheader("📅 Programar Tratamiento / Consulta")
    
    # =====================================================================
    # 🛠️ PARCHE DE COMPATIBILIDAD PARA TiDB (TABLA INGRESOS -> CONCEPTO)
    # =====================================================================
    try:
        conn_migra = conectar_db()
        with conn_migra.cursor() as cur_migra:
            # Forzamos la creación de la columna 'concepto' en la tabla ingresos si falta
            cur_migra.execute("ALTER TABLE ingresos ADD COLUMN concepto VARCHAR(100) DEFAULT 'Saldo Liquidación Cita';")
            conn_migra.commit()
    except Exception:
        # Si la columna ya existe, TiDB lanzará un error que capturamos aquí en silencio
        pass
    finally:
        if 'conn_migra' in locals() and conn_migra:
            conn_migra.close()
    # =====================================================================

    df_p = obtener_pacientes()
    if df_p.empty: 
        st.warning("Debe registrar un paciente primero.")
    else:
        # --- VISUALIZADOR RÁPIDO DE HORAS LIBRES INCORPORADO ---
        st.write("### 🔍 Consultar Disponibilidad de Horarios")
        fecha_consulta = st.date_input("Selecciona una fecha para ver espacios libres:", value=datetime.now(), key="fecha_consulta_rapida")
        
        fecha_consulta_str = fecha_consulta.strftime("%Y-%m-%d")
        conn_ver = conectar_db()
        df_ver_activas = pd.DataFrame()
        try:
            query_ver = """
                SELECT hora_inicio, hora_fin FROM citas 
                WHERE fecha = %s AND estado != 'Cancelada'
            """
            df_ver_activas = pd.read_sql(query_ver, conn_ver, params=[fecha_consulta_str])
        except Exception as e:
            st.error(f"Error al verificar agenda: {e}")
        finally:
            if conn_ver:
                conn_ver.close()

        with st.expander(f"📋 Ver Agenda y Espacios del día: {fecha_consulta.strftime('%d-%m-%Y')}", expanded=False):
            horas_base = range(7, 18)
            st.write("**Resumen de las horas del día:**")
            
            sub_cols = st.columns(4)
            for idx_h, hora in enumerate(horas_base):
                estados_cuartos = []
                for cuarto in [0, 15, 30, 45]:
                    bloque_inicio = datetime.combine(datetime.min, time(hora, cuarto)).time()
                    bloque_fin = (datetime.combine(datetime.min, time(hora, cuarto)) + timedelta(minutes=15)).time()
                    
                    ocupado = False
                    if not df_ver_activas.empty:
                        for _, r in df_ver_activas.iterrows():
                            inicio_cita = (datetime.min + r['hora_inicio']).time() if isinstance(r['hora_inicio'], timedelta) else r['hora_inicio']
                            fin_cita = (datetime.min + r['hora_fin']).time() if isinstance(r['hora_fin'], timedelta) else r['hora_fin']
                            if bloque_inicio < fin_cita and bloque_fin > inicio_cita:
                                ocupado = True
                                break
                    estados_cuartos.append(1 if ocupado else 0)
                
                cuartos_ocupados = sum(estados_cuartos)
                if cuartos_ocupados == 4:
                    txt_status = "🔴 Ocupado"
                elif cuartos_ocupados == 0:
                    txt_status = "🟢 Libre"
                else:
                    txt_status = "🟡 Parcial"
                
                with sub_cols[idx_h % 4]:
                    st.caption(f"**{hora:02d}:00** -> {txt_status}")

        st.divider()

        # --- FORMULARIO DE REGISTRO ---
        st.write("### 📝 Datos de la Nueva Cita")
        with st.form("form_agendar", clear_on_submit=True):
            p_id = st.selectbox("Paciente", options=df_p['id_paciente'].tolist(),
                               format_func=lambda x: f"{df_p[df_p['id_paciente']==x]['nombre'].values[0]}")
            
            c1, c2, c3, c4 = st.columns(4)
            fecha = c1.date_input("Fecha de la Cita", value=fecha_consulta)
            h_i = c2.time_input("Hora Inicio", value=time(8,0))
            h_f = c3.time_input("Hora Fin", value=time(8,30))
            
            # Campo de entrada para el dinero del adelanto
            anticipo_ini = c4.number_input("Anticipo (C$)", min_value=0.0, value=0.0, step=50.0, 
                                           help="Registra si el paciente deja un abono previo para apartar el espacio.")
            
            if st.form_submit_button("Confirmar Espacio"):
                if h_i >= h_f:
                    st.error("La hora de fin debe ser posterior a la de inicio.")
                else:
                    esta_disponible = verificar_disponibilidad(fecha, h_i, h_f)
                    
                    if not esta_disponible:
                        st.error("❌ El horario seleccionado ya se encuentra ocupado. Por favor, elige otra hora.")
                    else:
                        try:
                            conn = conectar_db()
                            with conn.cursor() as cursor:
                                
                                # 1. Guardamos la cita (Sin meter 'anticipo' aquí si da problemas, se asienta directo en ingresos)
                                sql_cita = """
                                    INSERT INTO citas (id_paciente, fecha, hora_inicio, hora_fin) 
                                    VALUES (%s, %s, %s, %s)
                                """
                                cursor.execute(sql_cita, (p_id, fecha, h_i, h_f))
                                id_cita_nueva = cursor.lastrowid
                                
                                # 2. Si el usuario de verdad ingresó dinero, lo inyectamos en la tabla ingresos
                                if anticipo_ini > 0:
                                    sql_ingreso = """
                                        INSERT INTO ingresos (id_cita, id_paciente, monto, concepto, fecha)
                                        VALUES (%s, %s, %s, 'Anticipo/Abono de Cita Programada', NOW())
                                    """
                                    cursor.execute(sql_ingreso, (id_cita_nueva, p_id, anticipo_ini))
                                
                                conn.commit()
                            
                            msg_exito = f"⚖ **Registro Exitoso:** Cita agendada de forma permanente para el {fecha.strftime('%d-%m-%Y')}."
                            if anticipo_ini > 0:
                                msg_exito += f" Se ingresó un anticipo de C$ {anticipo_ini:,.2f} a caja chica."
                                
                            st.success(msg_exito)
                            t_sleep.sleep(2.0)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error al guardar la cita en la nube: {e}")

# --- MÓDULO 3: PACIENTES Y EXPEDIENTES ---
elif menu == "Pacientes y Expedientes":
    st.subheader("🏥 Historial Clínico Dental")
    tab1, tab2, tab3, tab4 = st.tabs(["Registrar Paciente", "Historial de Tratamientos", "Nueva Evolución Clínica", "🗂️ Historial Unificado"])

    with tab1:
        # Usamos clear_on_submit=True para que los campos se vacíen automáticamente al dar clic en guardar
        with st.form("reg_p", clear_on_submit=True):
            c1, c2 = st.columns(2)
            n = c1.text_input("Nombre Completo del Paciente")
            id_c = c2.text_input("Cédula / Pasaporte")
            t = c1.text_input("Teléfono de Contacto")
            m = c2.text_input("Correo Electrónico")
            r = st.text_area("Alergías, Enfermedades Sistémicas o Antecedentes Médicos relevantes")
            
            # El botón de abajo lleva exactamente 12 espacios hacia la derecha 
            # para quedar alineado perfectamente con los inputs de arriba
            if st.form_submit_button("Guardar Ficha Paciente"):
                if n.strip() == "":
                    st.error("❌ El nombre completo del paciente es obligatorio.")
                else:
                    try:
                        conn = conectar_db()
                        cursor = conn.cursor()
                        
                        sql = """
                            INSERT INTO pacientes (nombre, cedula, telefono, correo, referencia) 
                            VALUES (%s, %s, %s, %s, %s)
                        """
                        
                        cursor.execute(sql, (n, id_c if id_c else None, t, m, r))
                        
                        # --- MODIFICACIÓN AQUÍ: Aseguramos que los datos se guarden en TiDB Cloud ---
                        conn.commit() 
                        
                        cursor.close()
                        
                        st.success(f"🎉 ¡Paciente '{n}' registrado con éxito!")
                        
                        # --- CAMBIO AQUÍ PARA EVITAR EL ERROR ---
                        st.toast("Actualizando lista de pacientes...", icon="🔄")
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
                    finally:
                        if 'conn' in locals() and conn:
                            conn.close()

    with tab2:
        st.write("### 📜 Registro Histórico de Evoluciones Dentales")
        try:
            conn_tab2 = conectar_db()
            df_p = pd.read_sql("SELECT id_paciente, nombre, cedula, telefono, correo, referencia FROM pacientes", conn_tab2)
            conn_tab2.close()
        except Exception as e:
            st.error(f"Error al conectar base de datos en pestaña 2: {e}")
            df_p = pd.DataFrame()
        
        # Selector de pacientes con opción vacía inicial
        p_id_hist = st.selectbox(
            "Seleccionar Paciente:", 
            options=[None] + df_p['id_paciente'].tolist(),
            format_func=lambda x: "Elige un paciente..." if x is None else f"{df_p[df_p['id_paciente']==x]['nombre'].values[0]}",
            key="hist_dent"
        )

        # Validamos si realmente se seleccionó un paciente
        if p_id_hist is not None:
            # Extraemos la fila del paciente seleccionado en un diccionario para trabajar fácil
            info_paciente = df_p[df_p['id_paciente'] == p_id_hist].iloc[0].to_dict()
            
            # --- 🌟 PLUS: FICHA DE DATOS PERSONALES Y EDICIÓN 🌟 ---
            # Formateamos la fecha de registro para mostrarla limpia
            f_reg_str = "No disponible (Nube)"

            with st.expander(f"👤 Ficha de Contacto: {info_paciente['nombre']} (Registrado el: {f_reg_str})", expanded=True):
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.markdown(f"**🪪 Identificación/Cédula:** {info_paciente['cedula'] if info_paciente['cedula'] else 'S/N'}")
                    st.markdown(f"**📞 Teléfono:** {info_paciente['telefono'] if info_paciente['telefono'] else 'No asignado'}")
                with col_info2:
                    st.markdown(f"**📧 Correo Electrónico:** {info_paciente['correo'] if info_paciente['correo'] else 'No asignado'}")
                    st.markdown(f"**📋 Antecedentes Clínicos:** {info_paciente['referencia'] if info_paciente['referencia'] else 'Ninguno'}")
                
                # Formulario modal/desplegable para corregir datos mal escritos
                if st.checkbox("✏️ Corregir o Actualizar datos de este cliente", key=f"edit_check_{p_id_hist}"):
                    with st.form(f"form_editar_p_{p_id_hist}"):
                        st.write("##### Modificar Datos de Contacto")
                        new_nom = st.text_input("Nombre Completo:", value=info_paciente['nombre'])
                        new_ced = st.text_input("Cédula / Pasaporte:", value=info_paciente['cedula'])
                        new_tel = st.text_input("Número Telefónico:", value=info_paciente['telefono'])
                        new_cor = st.text_input("Correo:", value=info_paciente['correo'])
                        new_ref = st.text_area("Antecedentes Médicos:", value=info_paciente['referencia'])
                        
                        if st.form_submit_button("Guardar Cambios en Ficha"):
                            if new_nom:
                                try:
                                    conn_edit = conectar_db()
                                    cursor_edit = conn_edit.cursor()
                                    sql_update = """
                                        UPDATE pacientes 
                                        SET nombre=%s, cedula=%s, telefono=%s, correo=%s, referencia=%s 
                                        WHERE id_paciente=%s
                                    """
                                    cursor_edit.execute(sql_update, (new_nom, new_ced if new_ced else None, new_tel, new_cor, new_ref, p_id_hist))
                                    conn_edit.commit()
                                    conn_edit.close()
                                    st.success("✅ Ficha de cliente actualizada con éxito.")
                                    t_sleep.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error al actualizar: {e}")
                            else:
                                st.error("El nombre del paciente no puede quedar vacío.")

            st.divider()
            
            # --- CONTINUACIÓN DEL HISTORIAL CLÍNICO ---
            conn = conectar_db()
            query_h = """
                SELECT fecha, higiene_bucal, nivel_dolor, tipo_tratamiento, urgencia, 
                       piezas_afectadas, observaciones_clinicas, procedimiento_realizado, indicaciones_post 
                FROM historiales_dentales 
                WHERE id_paciente = %s 
                ORDER BY fecha DESC
            """
            
            try:
                df_h = pd.read_sql(query_h, conn, params=(p_id_hist,))
                
                if df_h.empty:
                    st.info("El paciente no registra ninguna intervención previa.")
                else:
                    for _, row in df_h.iterrows():
                        with st.expander(f"📅 Consulta: {row['fecha']} | Tratamiento: {row['tipo_tratamiento']}"):
                            # --- INDICADORES RÁPIDOS ---
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("Higiene", row['higiene_bucal'])
                            c2.metric("Dolor/Molestia", row['nivel_dolor'])
                            c3.metric("Tratamiento", row['tipo_tratamiento'])
                            
                            if row['urgencia'] in ['Alta', 'Crítica']:
                                c4.error(f"🚨 Urgencia: {row['urgencia']}")
                            else:
                                c4.success(f"Urgencia: {row['urgencia']}")

                            st.divider()

                            # --- DETALLES DE LA INTERVENCIÓN ---
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.markdown(f"**🦷 Piezas Dentales Tratadas:**\n{row['piezas_afectadas']}")
                                st.markdown(f"**👁️ Observaciones Clínicas Iniciales:**\n{row['observaciones_clinicas']}")
                            
                            with col_b:
                                segregation_b = f"**🛠️ Procedimiento / Intervención Realizada:**\n{row['procedimiento_realizado']}"
                                st.markdown(segregation_b)
                                st.markdown(f"**📝 Cuidados y Receta Post-operatoria:**\n{row['indicaciones_post']}")
                                
            except Exception as e:
                st.error(f"Error al cargar el historial dental: {e}")
            finally:
                conn.close()
        else:
            st.info("💡 Por favor, selecciona un paciente de la lista para desplegar su información y evoluciones.")

    with tab3:
        if st.session_state.get('rol') in ['Admin', 'Odontologo']:
            

            st.write("### 🦷 Registro de Evolución Odontológica")
            df_p = obtener_pacientes()

            if df_p.empty:
                st.warning("No hay pacientes registrados en la base de datos.")
            else:
                p_id = st.selectbox(
                    "Paciente:", 
                    options=df_p['id_paciente'].tolist(),
                    format_func=lambda x: f"{df_p[df_p['id_paciente']==x]['nombre'].values[0]}", 
                    key="cons_dent"
                )
                
                conn = conectar_db()
                query_citas = f"""
                    SELECT id_cita, fecha 
                    FROM citas 
                    WHERE id_paciente={p_id} AND estado='Asistió' 
                    AND id_cita NOT IN (SELECT id_cita FROM historiales_dentales)
                """
                
                try:
                    c_libres = pd.read_sql(query_citas, conn)
                    
                    if c_libres.empty:
                        st.info("ℹ️ No hay citas marcadas como 'Asistió' pendientes de reporte clínico para este paciente.")
                    else:
                        with st.form("f_dentcal_completo"):
                            cita_sel = st.selectbox(
                                "Seleccionar Sesión Dental:", 
                                options=c_libres['id_cita'].tolist(),
                                format_func=lambda x: f"Fecha: {c_libres[c_libres['id_cita']==x]['fecha'].values[0]}"
                            )
                            
                            # --- FILA 1: EXAMEN BUCAL RÁPIDO ---
                            st.markdown("#### 📊 Indicadores Iniciales de Diagnóstico")
                            col1, col2, col3, col4 = st.columns(4)
                            higiene = col1.selectbox("Higiene Bucal", ["Buena", "Regular", "Deficiente"])
                            dolor = col2.selectbox("Nivel de Dolor", ["Inexistente", "Leve", "Moderado", "Severo"])
                            tratamiento = col3.selectbox("Categoría", ["Diagnóstico", "Limpieza/Profilaxis", "Operatoria (Calzas)", "Endodoncia", "Cirugía/Extracción", "Ortodoncia"])
                            urgencia = col4.selectbox("Urgencia Clinica", ["Baja", "Moderada", "Alta", "Crítica"])
                            
                            # --- FILA 2: SECCIÓN CLÍNICA TEXTUAL ---
                            st.markdown("---")
                            piezas = st.text_input("Número de Pieza(s) Dental(es) a intervenir", placeholder="Ej: 11, 12, 46 u Odontograma completo")
                            observaciones = st.text_area("Observaciones Clínicas / Diagnóstico Visual", placeholder="Estado de las encías, presencia de sarro, caries detectadas, etc.")
                            procedimiento = st.text_area("Procedimiento Realizado en Sillón", placeholder="Materiales utilizados, anestesia aplicada, técnica ejecutada...")
                            indicaciones = st.text_area("Indicaciones Post-Tratamiento y Receta", placeholder="Medicamentos (analgésicos/antibióticos), reposo, alimentación...")
                            
                            # Guardado de la evolución dental
                            if st.form_submit_button("Guardar Registro Clínico en DentCal"):
                                fecha_c = str(c_libres[c_libres['id_cita']==cita_sel]['fecha'].values[0])
                                cursor = conn.cursor()
                                
                                sql = """INSERT INTO historiales_dentales 
                                        (id_paciente, id_cita, fecha, higiene_bucal, nivel_dolor, tipo_tratamiento, 
                                        urgencia, piezas_afectadas, observaciones_clinicas, procedimiento_realizado, indicaciones_post) 
                                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
                                
                                valores = (p_id, cita_sel, fecha_c, higiene, dolor, tratamiento, urgencia, piezas, observaciones, procedimiento, indicaciones)
                                
                                cursor.execute(sql, valores)
                                conn.commit()
                                st.success("✅ Registro dental almacenado exitosamente en el expediente.")
                                t_sleep.sleep(1.5)
                                st.rerun()

                except Exception as e:
                    st.error(f"Error en formulario dental: {e}")
                finally:
                    conn.close()
        else:
            st.write("### 🔒 Módulo Restringido")
            st.warning("⚠️ Permisos insuficientes. El registro de evoluciones clínicas está reservado para Odontólogos.") 

    with tab4:
        st.write("### 🗂️ Ficha Médica e Historial Clínico Unificado")
        
        # --- CORRECCIÓN AQUÍ: Traemos los datos completos directo de la nube ---
        try:
            conn_all = conectar_db()
            df_p_all = pd.read_sql("SELECT id_paciente, nombre, cedula, telefono, correo, referencia FROM pacientes", conn_all)
            conn_all.close()
        except Exception as e:
            st.error(f"Error al conectar con el historial unificado: {e}")
            df_p_all = pd.DataFrame()

        if df_p_all.empty:
            st.warning("No hay pacientes registrados en el sistema.")
        else:
            # 1. Buscador centralizado de paciente (Corregido y optimizado para evitar KeyError)
            paciente_master_id = st.selectbox(
                "Seleccione el paciente para abrir su Expediente Único:",
                options=df_p_all['id_paciente'].tolist(),
                format_func=lambda x: f"{df_p_all[df_p_all['id_paciente']==x]['nombre'].values[0]} | Cédula: {df_p_all[df_p_all['id_paciente']==x]['cedula'].values[0] if df_p_all[df_p_all['id_paciente']==x]['cedula'].values[0] else 'S/N'}",
                key="sb_master_history"
            )
            
            if paciente_master_id:
                # Filtrar los datos del paciente seleccionado
                info_paciente = df_p_all[df_p_all['id_paciente'] == paciente_master_id].iloc[0]
                
                st.divider()
                
                # 2. PANEL GENERAL DEL PACIENTE (Datos Personales y Alergias)
                st.markdown("#### 👤 Datos de la Ficha General")
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Nombre:** {info_paciente['nombre']}")
                c2.markdown(f"**Cédula / Pasaporte:** `{info_paciente['cedula']}`")
                c3.markdown(f"**Contacto:** {info_paciente['telefono']} | {info_paciente['correo']}")
                
                # Alertas médicas destacadas (Enfermedades o Alergias)
                alergias_texto = info_paciente['referencia'] if info_paciente['referencia'] else "Ninguna registrada."
                st.info(f"⚠️ **Antecedentes Médicos y Alergias:** {alergias_texto}")
                
                st.divider()
                
                # 3. LÍNEA DE TIEMPO DE CONSULTAS Y EVOLUCIONES
                st.markdown("#### ⏳ Línea de Tiempo de Evolución Clínica")
                
                conn = conectar_db()
                query_timeline = """
                    SELECT fecha, higiene_bucal, nivel_dolor, tipo_tratamiento, urgencia, 
                           piezas_afectadas, observaciones_clinicas, procedimiento_realizado, indicaciones_post
                    FROM historiales_dentales
                    WHERE id_paciente = %s
                    ORDER BY fecha DESC
                """
                
                try:
                    df_timeline = pd.read_sql(query_timeline, conn, params=(paciente_master_id,))
                    
                    if df_timeline.empty:
                        st.info("ℹ️ El paciente tiene ficha de registro pero aún no cuenta con evoluciones clínicas archivadas.")
                    else:
                        st.caption(f"Se encontraron {len(df_timeline)} intervenciones registradas en el historial.")
                        
                        # Iteramos sobre cada consulta histórica y la mostramos en un contenedor colapsable (Expander)
                        for _, row in df_timeline.iterrows():
                            # El título del expander muestra la fecha y el tratamiento principal de forma limpia
                            fecha_formateada = str(row['fecha'])
                            with st.expander(f"📅 Consulta: {fecha_formateada} — Módulo: **{row['tipo_tratamiento']}**"):
                                
                                # Indicadores rápidos en columnas métricas
                                m1, m2, m3 = st.columns(3)
                                m1.metric("Dolor Reportado", row['nivel_dolor'])
                                m2.metric("Higiene Bucal", row['higiene_bucal'])
                                
                                # Color dinámico según la urgencia de esa consulta
                                if row['urgencia'] in ['Alta', 'Crítica']:
                                    m3.error(f"🚨 Urgencia: {row['urgencia']}")
                                else:
                                    m3.success(f"🟢 Urgencia: {row['urgencia']}")
                                
                                # Detalles de la intervención en cajas de texto o markdown limpio
                                st.markdown(f"**🦷 Pieza(s) Intervenida(s):** `{row['piezas_afectadas'] if row['piezas_afectadas'] else 'N/A'}`")
                                
                                st.markdown("**🔍 Diagnóstico / Observaciones:**")
                                st.write(row['observaciones_clinicas'])
                                
                                st.markdown("**🛠️ Procedimiento Clínico Efectuado:**")
                                st.write(row['procedimiento_realizado'])
                                
                                st.markdown("**💊 Receta e Indicaciones Post-Tratamiento:**")
                                st.info(row['indicaciones_post'] if row['indicaciones_post'] else "Sin indicaciones particulares.")
                                
                except Exception as e:
                    st.error(f"Error al estructurar la línea de tiempo médica: {e}")
                finally:
                    conn.close()           

        # --- MÓDULO 4: CONFIGURACIÓN DEL SISTEMA ---
elif menu == "Configuración":
    st.subheader("⚙️ Panel de Configuración General")
    
    # Validamos el rol de seguridad antes de mostrar nada
    if st.session_state.get('rol') == 'Admin':
        
        # Organizamos por pestañas dentro del módulo oculto
        tab_usuarios, tab_info = st.tabs(["👥 Control de Usuarios", "ℹ️ Información del Sistema"])
        
        with tab_usuarios:
            # Reutilizamos de inmediato tu función maestra existente para no reescribir lógica de MySQL
            modulo_admin_usuarios()
            
        with tab_info:
            st.markdown("### 💻 Estado de DentCal")
            
            # Intentamos una conexión rápida de prueba para verificar el estado real en la nube
            try:
                test_conn = conectar_db()
                cursor_test = test_conn.cursor()
                # Le pedimos al servidor en la nube que nos diga su versión actual
                cursor_test.execute("SELECT VERSION()")
                version_mysql = cursor_test.fetchone()[0]
                cursor_test.close()
                test_conn.close()
                
                # Extramos los datos dinámicamente de tus secretos cargados en Streamlit Cloud
                host_actual = st.secrets["db_host"]
                db_actual = st.secrets["db_name"]
                
                # Si todo sale bien, muestra el éxito con datos reales del servidor TiDB Cloud
                st.success(f"🟢 **Conexión Exitosa:** El sistema está conectado a la base de datos en la nube (TiDB v{version_mysql}).")
                st.markdown(f"📍 **Host:** `{host_actual}` | **Base de Datos:** `{db_actual}`")
                
            except Exception as e:
                # Si el internet falla o las credenciales cambian, saltará este aviso de inmediato
                st.error(f"🔴 **Servidor Desconectado:** No se pudo establecer comunicación con TiDB Cloud.")
                st.warning(f"Detalle del error: {e}")
                st.info("💡 Asegúrate de que las variables en los 'Secrets' de Streamlit Cloud correspondan con los accesos TLS de tu clúster.")
            
    else:
        st.warning("⚠️ Acceso denegado. Este módulo está reservado exclusivamente para cuentas con rol de Administrador.")

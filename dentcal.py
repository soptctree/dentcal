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

# --- MÓDULO 1: AGENDA DIARIA ---
if menu == "Agenda Diaria Sillon":
    st.subheader("📋 Control de Citas y Búsqueda")
    
    # Separamos limpiamente en dos pestañas
    tab_agenda, tab_buscador, tab_auditoria = st.tabs(["🕒 Vista del Día", "🔍 Buscar Cita por Nombre", "📊 Auditoría e Historial"])

    # ==========================================
    # PESTAÑA 1: VISTA DE LA AGENDA DIARIA
    # ==========================================
    with tab_agenda:
        # --- MÓDULO 1: AGENDA DIARIA ---
        if menu == "Agenda Diaria Sillon":
            st.subheader("📋 Control de Citas del Día")
            fecha_agenda = st.date_input("Ver día:", value=datetime.now())
            
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
                        bloque_inicio = datetime.combine(datetime.min, time(hora, cuarto)).time()
                        bloque_fin = (datetime.combine(datetime.min, time(hora, cuarto)) + timedelta(minutes=15)).time()
                        
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
                            ultimo_bloque_ocupado = (datetime.combine(datetime.min, time(hora, cuarto)) + timedelta(minutes=15)).time()
                        else:
                            estados_cuartos.append(0)
                    
                    # --- CONSTRUCCIÓN DEL TEXTO INFORMATIVO ---
                    cuartos_ocupados = sum(estados_cuartos)
                    
                    if cuartos_ocupados == 4:
                        texto_arriba = "Ocupado"
                    elif cuartos_ocupados > 0 and ultimo_bloque_ocupado:
                        # El .strftime('%H:%M') convierte automáticamente los 60 minutos en la siguiente hora en punto
                        texto_arriba = f"Hasta las {ultimo_bloque_ocupado.strftime('%H:%M')}"
                    else:
                        texto_arriba = "Disponible"
                    
                    # --- CONSTRUCCIÓN DEL TEXTO DEL HOVER (TOOLTIP NATIVO) ---
                    if pacientes_de_la_hora:
                        # Si hay más de un paciente en fracciones de la misma hora, los une con comas
                        tooltip_texto = f"Paciente(s): {', '.join(pacientes_de_la_hora)}"
                    else:
                        tooltip_texto = "Horario Disponible"
                    
                    # --- MAQUILLAJE DE FONDOS CON CSS (Pintado exacto por cuartos individuales) ---
                    if cuartos_ocupados == 4:
                        estilo_fondo = "background-color: #FFD2D2; border-color: #D8000C; color: #D8000C;"
                    elif cuartos_ocupados == 0:
                        estilo_fondo = "background-color: #DFF2BF; border-color: #4F8A10; color: #4F8A10;"
                    else:
                        # Creamos un degradado fragmentado de 4 segmentos (25% cada uno)
                        partes_css = []
                        for i, estado in enumerate(estados_cuartos):
                            color = "#FFD2D2" if estado == 1 else "#DFF2BF"
                            inicio_pct = i * 25
                            fin_pct = (i + 1) * 25
                            partes_css.append(f"{color} {inicio_pct}%, {color} {fin_pct}%")
                        
                        degradado_completo = ", ".join(partes_css)
                        estilo_fondo = f"background: linear-gradient(to right, {degradado_completo}); border-color: #cca4a4;"

                    # LÍNEA TOTALMENTE PLANA CON EL ATRIBUTO title ENCARGADO DEL HOVER DEL PUNTERO
                    html_grid += f"<div class='hour-card' style='{estilo_fondo}' title='{tooltip_texto}'><span class='top-indicator'>📋 {texto_arriba}</span><span class='time-label'>{hora:02d}:00</span></div>"

                html_grid += "</div>"
                
                # 4. Renderizado final de la cuadrícula
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
                        
                        # --- PARTE A: CONTROL DE ESTADOS (BLOQUEADO SI ESTÁ CANCELADA) ---
                        if estado_actual == "Cancelada":
                            st.selectbox("Actualizar estado:", ["Cancelada"], index=0, disabled=True, key=f"upd_{row['id_cita']}")
                        else:
                            idx_actual = lista_estados.index(estado_actual) if estado_actual in lista_estados else 0
                            nuevo_estado = st.selectbox("Actualizar estado:", lista_estados, index=idx_actual, key=f"upd_{row['id_cita']}")
                            
                            if st.button("Guardar Cambio", key=f"btn_{row['id_cita']}"):
                                ahora = datetime.now()
                                
                                if isinstance(fecha_agenda, datetime):
                                    fecha_segura = fecha_agenda.date()
                                else:
                                    fecha_segura = fecha_agenda
                                
                                momento_exacto_cita = datetime.combine(fecha_segura, h_i_obj)
                                
                                if nuevo_estado == "Asistió" and ahora < momento_exacto_cita:
                                    contenedor_mensaje.error(f"❌ **Restricción de tiempo:** No se puede marcar asistencia antes del inicio programado. El turno comienza el {fecha_segura.strftime('%d-%m-%Y')} a las {h_i_obj.strftime('%H:%M')}.")
                                    t_sleep.sleep(3)
                                    contenedor_mensaje.empty()
                                else:
                                    # SOLUCIÓN DE CONEXIÓN: Abrimos una conexión fresca y dedicada para la actualización
                                    conn_accion = None
                                    try:
                                        conn_accion = conectar_db()
                                        cursor_accion = conn_accion.cursor()
                                        cursor_accion.execute("UPDATE citas SET estado = %s WHERE id_cita = %s", (nuevo_estado, row['id_cita']))
                                        conn_accion.commit()
                                        cursor_accion.close()
                                        
                                        contenedor_mensaje.success(f"Estado de {row['nombre']} actualizado a {nuevo_estado}")
                                        t_sleep.sleep(1)
                                        st.rerun()
                                    except Exception as ex_db:
                                        st.error(f"Error al actualizar el estado: {ex_db}")
                                    finally:
                                        if conn_accion:
                                            conn_accion.close()
                        
                        # --- PARTE B: HERRAMIENTA DE REPROGRAMACIÓN / TRASLADO DE HORA ---
                        if estado_actual in ["Cancelada", "Ausente", "Pendiente"]:
                            st.write("---")
                            tipo_accion = "🔄 Reprogramar Cita (Cancelada)" if estado_actual == "Cancelada" else "🕒 Trasladar Hora (Retraso/Ausente)"
                            st.write(f"**{tipo_accion}**")
                            
                            c1, c2, c3 = st.columns(3)
                            nueva_fecha = c1.date_input("Nueva Fecha", value=fecha_agenda, key=f"f_rep_{row['id_cita']}")
                            nueva_h_i = c2.time_input("Nueva Hora Inicio", value=h_i_obj, key=f"hi_rep_{row['id_cita']}")
                            nueva_h_f = c3.time_input("Nueva Hora Fin", value=h_f_obj, key=f"hf_rep_{row['id_cita']}")
                            
                            if st.button("Aplicar Reubicación Horaria", key=f"btn_rep_{row['id_cita']}"):
                                if nueva_h_i >= nueva_h_f:
                                    contenedor_mensaje.error("❌ La hora de fin debe ser posterior a la de inicio.")
                                else:
                                    esta_disponible = verificar_disponibilidad(nueva_fecha, nueva_h_i, nueva_h_f)
                                    
                                    if not esta_disponible:
                                        contenedor_mensaje.error("❌ El horario destino seleccionado ya se encuentra ocupado por otra cita activa.")
                                        t_sleep.sleep(3)
                                        contenedor_mensaje.empty()
                                    else:
                                        # SOLUCIÓN DE CONEXIÓN: Conexión dedicada para la reprogramación
                                        conn_rep = None
                                        try:
                                            conn_rep = conectar_db()
                                            cursor_rep = conn_rep.cursor()
                                            sql_update = """
                                                UPDATE citas 
                                                SET fecha = %s, hora_inicio = %s, hora_fin = %s, estado = 'Pendiente' 
                                                WHERE id_cita = %s
                                            """
                                            cursor_rep.execute(sql_update, (nueva_fecha, nueva_h_i, nueva_h_f, row['id_cita']))
                                            conn_rep.commit()
                                            cursor_rep.close()
                                            
                                            contenedor_mensaje.success(f"✅ Cita de {row['nombre']} reubicada con éxito a las {nueva_h_i.strftime('%H:%M')}.")
                                            t_sleep.sleep(1.5)
                                            st.rerun()
                                        except Exception as ex_rep:
                                            st.error(f"Error al trasladar la cita: {ex_rep}")
                                        finally:
                                            if conn_rep:
                                                conn_rep.close()       

    # ==========================================
    # PESTAÑA 2: BUSCADOR DE CITAS POR NOMBRE (SIN GRÁFICAS)
    # ==========================================
    with tab_buscador:
        st.write("### 🔍 Localizador de Citas Olvidadas")
        nombre_buscar = st.text_input("Escribe el nombre del paciente a consultar:", placeholder="Ej. Josue Ferrey")
        
        if nombre_buscar:
            conn = conectar_db()
            query_buscar = """
                SELECT p.nombre, c.fecha, c.hora_inicio, c.hora_fin, c.estado
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
                    
                    df_visual = df_busqueda.copy()
                    df_visual['fecha'] = pd.to_datetime(df_visual['fecha']).dt.strftime('%d-%m-%Y')
                    
                    df_visual['hora_inicio'] = df_visual['hora_inicio'].apply(lambda x: (datetime.min + x).time().strftime('%H:%M') if isinstance(x, timedelta) else x.strftime('%H:%M'))
                    df_visual['hora_fin'] = df_visual['hora_fin'].apply(lambda x: (datetime.min + x).time().strftime('%H:%M') if isinstance(x, timedelta) else x.strftime('%H:%M'))
                    
                    df_visual.columns = ["Paciente", "Fecha Programada", "Hora Inicio", "Hora Fin", "Estado Actual"]
                    
                    st.dataframe(df_visual, use_container_width=True)
                else:
                    st.warning(f"❌ No se encontró ninguna cita registrada para: '{nombre_buscar}'")
            except Exception as e:
                st.error(f"Error en la búsqueda: {e}")
            finally:
                if conn:
                    conn.close()
        else:
            st.info("💡 Escribe el nombre del paciente para ver qué día y a qué hora tiene citas asignadas en el sistema.")

    with tab_auditoria:
        st.write("### 📊 Historial y Auditoría Global de Citas")
        st.write("Consulte y supervise el estado de todos los turnos históricos asentados en el sistema.")
        
        # --- FILTROS DE BÚSQUEDA ---
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
            # --- CONSULTA SEGURA A LA BASE DE DATOS ---
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

            # Filtrado local en Pandas
            if not df_auditoria.empty and estados_seleccionados:
                df_auditoria = df_auditoria[df_auditoria['estado'].isin(estados_seleccionados)]

            st.write("---")
            st.write(f"#### 📋 Registros Encontrados ({len(df_auditoria)} cita/s)")

            if df_auditoria.empty:
                st.info("No se encontraron registros históricos para los filtros seleccionados.")
            else:
                # --- SECCIÓN DE EXPORTACIÓN (EXCEL Y PDF) ---
                st.write("### 📥 Exportar Reporte")
                col_xl, col_pdf = st.columns(2)

                # ---- LÓGICA DE EXPORTACIÓN A EXCEL ----
                with col_xl:
                    buffer_excel = BytesIO()
                    df_exportar = df_auditoria.copy()
                    
                    # Formateo de tiempos seguro para evitar conflictos de tipo de datos en Excel
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

                # ---- LÓGICA DE EXPORTACIÓN A PDF (REPORTLAB) ----
                with col_pdf:
                    buffer_pdf = BytesIO()
                    doc = SimpleDocTemplate(
                        buffer_pdf, 
                        pagesize=letter,
                        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
                    )
                    
                    story = []
                    styles = getSampleStyleSheet()
                    
                    estilo_titulo = ParagraphStyle(
                        'TituloPDF', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor('#1f3864'), spaceAfter=10
                    )
                    estilo_sub = ParagraphStyle(
                        'SubPDF', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#555555'), spaceAfter=20
                    )
                    estilo_celda = ParagraphStyle(
                        'CeldaPDF', parent=styles['Normal'], fontSize=9, leading=11
                    )
                    estilo_cabecera = ParagraphStyle(
                        'CabeceraPDF', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold', textColor=colors.white
                    )

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

                # --- RENDERIZADO VISUAL EN LA INTERFAZ DE TARJETAS Y ACORDEONES ---
                # Agrupamos por la columna 'fecha' sin reordenar para respetar el DESC de la consulta
                for fecha_grupo, df_dia in df_auditoria.groupby('fecha', sort=False):
                    fecha_bonita = fecha_grupo.strftime('%A, %d de %B de %Y') if isinstance(fecha_grupo, (date, datetime)) else str(fecha_grupo)
                    st.markdown(f"##### 📅 {fecha_bonita}")
                    
                    # Tarjetas horizontales de estados
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
                    
                    # Desglose en acordeones (expanders)
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

# --- MÓDULO 2: AGENDAR CITA ---
elif menu == "Agendar Cita Dental":
    st.subheader("📅 Programar Tratamiento / Consulta")
    df_p = obtener_pacientes()
    if df_p.empty: 
        st.warning("Debe registrar un paciente primero.")
    else:
        # --- VISUALIZADOR RÁPIDO DE HORAS LIBRES INCORPORADO ---
        # Colocamos un selector de fecha fuera del formulario para que actualice dinámicamente la disponibilidad
        st.write("### 🔍 Consultar Disponibilidad de Horarios")
        fecha_consulta = st.date_input("Selecciona una fecha para ver espacios libres:", value=datetime.now(), key="fecha_consulta_rapida")
        
        # Consultamos las citas activas para esa fecha de forma síncrona
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

        # Construimos el acordeón desplegable con el estado de las horas
        with st.expander(f"📋 Ver Agenda y Espacios del día: {fecha_consulta.strftime('%d-%m-%Y')}", expanded=False):
            horas_base = range(7, 18)  # De 7 AM a 5 PM
            
            # Formateamos una lista limpia de estados en texto legible
            st.write("**Resumen de las horas del día:**")
            
            # Generamos columnas compactas internas para no ocupar mucho espacio vertical
            sub_cols = st.columns(4)
            for idx_h, hora in enumerate(horas_base):
                estados_cuartos = []
                ultimo_bloque_ocupado = None
                
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
            
            c1, c2, c3 = st.columns(3)
            # Enlazamos el input del formulario con la fecha seleccionada arriba para mantener concordancia
            fecha = c1.date_input("Fecha de la Cita", value=fecha_consulta)
            h_i = c2.time_input("Hora Inicio", value=time(8,0))
            h_f = c3.time_input("Hora Fin", value=time(8,30))
            
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
                            cursor = conn.cursor()
                            
                            sql = """
                                INSERT INTO citas (id_paciente, fecha, hora_inicio, hora_fin) 
                                VALUES (%s, %s, %s, %s)
                            """
                            cursor.execute(sql, (p_id, fecha, h_i, h_f))
                            cursor.close()
                            # Guardamos cambios reales en la base de datos
                            conn.commit()
                            conn.close()
                            
                            # MENSAJE DE CONFIRMACIÓN CLÍNICO (Sin animaciones infantiles)
                            st.success(f"⚖ **Registro Exitoso:** La cita para el paciente ha sido asentada de forma permanente en la nube el día {fecha.strftime('%d-%m-%Y')} de {h_i.strftime('%H:%M')} a {h_f.strftime('%H:%M')}.")
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

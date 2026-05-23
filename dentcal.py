import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
import time as t_sleep
import pymysql  # Usamos pymysql directamente para mayor estabilidad en la nube


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
        cuartos = [0, 15, 30, 45]
        
        # Contamos cuántas citas reales (únicas) hay hoy
        total_citas_hoy = len(df_activas) if not df_activas.empty else 0

        # --- MAPA DE DISPONIBILIDAD HORARIA RESPONSIVO ---
        st.write("### 🕒 Ocupación del Sillón Dental")
        
        # Una sola tarjeta directa y fácil de entender
        st.metric(label="📅 Citas programadas para hoy", value=f"{total_citas_hoy} paciente(s)")
            
        st.write("") # Espacio estético
        
        # 1. Declaramos el CSS y una función JavaScript limpia (Evita problemas de comillas en celulares)
        css_y_js = """
        <script>
        function mostrarCita(hora, paciente) {
            if (paciente) {
                alert("⏰ Hora: " + hora + "\\n👤 Paciente: " + paciente);
            } else {
                alert("🟢 Hora: " + hora + "\\n✨ Espacio Disponible");
            }
        }
        </script>
        <style>
        .grid-container {
            display: grid !important;
            grid-template-columns: repeat(4, minmax(75px, 1fr)) !important;
            gap: 8px !important;
            font-family: Arial, sans-serif;
            margin-bottom: 25px;
            width: 100%;
        }
        .grid-slot-libre {
            background-color: #DFF2BF;
            color: #4F8A10;
            border: 1px solid #4F8A10;
            padding: 12px 5px;
            text-align: center;
            font-size: 12px;
            border-radius: 4px;
            font-weight: 500;
            transition: transform 0.1s ease;
            cursor: pointer;
        }
        .grid-slot-libre:hover {
            transform: scale(1.02);
        }
        .grid-slot-ocupado {
            background-color: #FFD2D2;
            color: #D8000C;
            border: 1px solid #D8000C;
            padding: 12px 5px;
            text-align: center;
            font-weight: bold;
            font-size: 12px;
            border-radius: 4px;
            transition: transform 0.1s ease;
            cursor: pointer;
        }
        .grid-slot-ocupado:hover {
            background-color: #ffb6b6;
            transform: scale(1.02);
        }
        .slot-range {
            display: block;
            font-size: 11px;
            opacity: 0.8;
            margin-bottom: 3px;
            font-weight: normal;
        }
        </style>
        """
        st.markdown(css_y_js, unsafe_allow_html=True)
        
        # 2. Empezamos la estructura de la grilla HTML
        html_grid = "<div class='grid-container'>"
        
        # 3. Ciclo para generar las filas de horas
        for hora in horas_base:
            for cuarto in cuartos:
                h = time(hora, cuarto)
                
                dt_bloque_inicio = datetime.combine(datetime.min, h)
                dt_bloque_fin = dt_bloque_inicio + timedelta(minutes=15)
                
                bloque_inicio_time = dt_bloque_inicio.time()
                bloque_fin_time = dt_bloque_fin.time()
                
                rango_texto = f"{bloque_inicio_time.strftime('%H:%M')}-{bloque_fin_time.strftime('%H:%M')}"
                
                ocupado = False
                paciente_ocupando = ""
                
                if not df_activas.empty:
                    for _, r in df_activas.iterrows():
                        inicio_cita = (datetime.min + r['hora_inicio']).time() if isinstance(r['hora_inicio'], timedelta) else r['hora_inicio']
                        fin_cita = (datetime.min + r['hora_fin']).time() if isinstance(r['hora_fin'], timedelta) else r['hora_fin']
                        
                        if bloque_inicio_time < fin_cita and bloque_fin_time > inicio_cita:
                            ocupado = True
                            paciente_ocupando = r['nombre']
                            break
                
                # Al usar comillas simples fijas y pasar los datos limpitos a la función script, el celular no se pierde
                hora_str = bloque_inicio_time.strftime('%H:%M')
                if ocupado:
                    # Reemplazamos posibles comillas en el nombre para que no rompan la función
                    p_seguro = paciente_ocupando.replace("'", "\\'")
                    html_grid += f"<div class='grid-slot-ocupado' onclick=\"mostrarCita('{hora_str}', '{p_seguro}');\" title='Paciente: {paciente_ocupando}'><span class='slot-range'>❌ {hora_str}</span> Ocupado</div>"
                else:
                    html_grid += f"<div class='grid-slot-libre' onclick=\"mostrarCita('{hora_str}', '');\" title='Espacio Disponible'><span class='slot-range'>{hora_str}</span> Libre</div>"
                    
        html_grid += "</div>"
        
        # 4. Renderizado final de la cuadrícula
        st.markdown(html_grid, unsafe_allow_html=True)
        st.divider()

        # --- 3. DETALLE Y ASISTENCIA ---
        st.write("### 📝 Control de Asistencia")
        if df_todas.empty:
            st.info("No hay pacientes agendados para esta fecha.")
        else:
            for _, row in df_todas.iterrows():
                h_i_obj = (datetime.min + row['hora_inicio']).time() if isinstance(row['hora_inicio'], timedelta) else row['hora_inicio']
                h_f_obj = (datetime.min + row['hora_fin']).time() if isinstance(row['hora_fin'], timedelta) else row['hora_fin']
                time_range = f"{h_i_obj.strftime('%H:%M')} - {h_f_obj.strftime('%H:%M')}"
                
                with st.expander(f"⏰ {time_range} | 👤 {row['nombre']} ({row['estado']})"):
                    st.write(f"**Cédula/ID:** {row['cedula']}")
                    
                    lista_estados = ["Pendiente", "Asistió", "Ausente", "Cancelada"]
                    idx_actual = lista_estados.index(row['estado']) if row['estado'] in lista_estados else 0
                    
                    nuevo_estado = st.selectbox("Actualizar estado:", lista_estados, index=idx_actual, key=f"upd_{row['id_cita']}")
                    
                    if st.button("Guardar Cambio", key=f"btn_{row['id_cita']}"):
                        cursor = conn.cursor()
                        cursor.execute("UPDATE citas SET estado = %s WHERE id_cita = %s", (nuevo_estado, row['id_cita']))
                        conn.commit()
                        st.success(f"Estado de {row['nombre']} actualizado a {nuevo_estado}")
                        t_sleep.sleep(1)
                        st.rerun()

    except Exception as e:
        st.error(f"Error en Agenda: {e}")
    finally:
        conn.close()

# --- MÓDULO 2: AGENDAR CITA ---
elif menu == "Agendar Cita Dental":
    st.subheader("📅 Programar Tratamiento / Consulta")
    df_p = obtener_pacientes()
    if df_p.empty: 
        st.warning("Debe registrar un paciente primero.")
    else:
        with st.form("form_agendar", clear_on_submit=True):
            p_id = st.selectbox("Paciente", options=df_p['id_paciente'].tolist(),
                               format_func=lambda x: f"{df_p[df_p['id_paciente']==x]['nombre'].values[0]}")
            c1, c2, c3 = st.columns(3)
            fecha = c1.date_input("Fecha de la Cita")
            h_i = c2.time_input("Hora Inicio", value=time(8,0))
            h_f = c3.time_input("Hora Fin", value=time(8,30))
            
            if st.form_submit_button("Confirmar Espacio"):
                if h_i >= h_f:
                    st.error("La hora de fin debe ser posterior a la de inicio.")
                else:
                    # Asumiendo que verificar_disponibilidad devuelve True si está LIBRE
                    # Si devuelve True si está OCUPADO, cambia a: if not verificar_disponibilidad(fecha, h_i, h_f):
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
                            conn.close()
                            
                            st.success("✅ ¡Cita dental reservada correctamente!")
                            st.balloons()
                            t_sleep.sleep(1.5)
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
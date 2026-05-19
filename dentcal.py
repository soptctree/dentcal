import streamlit as st
import pandas as pd
from datetime import datetime, time, timedelta
import time as t_sleep
import pymysql  # Usamos pymysql directamente para mayor estabilidad en la nube


def conectar_db():
    return pymysql.connect(
        host="localhost",      # Apunta a tu laptop
        port=3306,             # Puerto estándar de MySQL/XAMPP
        user="root",           # Usuario por defecto en entornos locales
        password="",           # Por defecto XAMPP viene vacío (si pusiste clave, agrégala aquí)
        database="dentcal_db", 
        autocommit=True
        # Quitamos la línea de SSL porque localmente no la necesitas
    )
    

def validar_login(usuario, clave):
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        sql = "SELECT rol FROM usuarios WHERE username = %s AND password = %s"
        cursor.execute(sql, (usuario, clave))
        resultado = cursor.fetchone()
        
        if resultado:
            return resultado[0]  # Retornamos el rol (Admin, Odontologo, etc.)
        return None
    except Exception as e:
        st.error(f"Error en login: {e}")
        return None
    finally:
        if 'conn' in locals() and conn:
            conn.close()
            
if "rol" not in st.session_state:
    st.session_state.rol = None

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
        conn = conectar_db()
        # Traemos todos los campos necesarios para poder editarlos luego
        df = pd.read_sql("SELECT id_paciente, nombre, IFNULL(cedula, '') as cedula, IFNULL(telefono, '') as telefono, IFNULL(correo, '') as correo, IFNULL(referencia, '') as referencia, fecha_registro FROM pacientes", conn)
        conn.close()
        return df
    except:
        return pd.DataFrame(columns=['id_paciente', 'nombre', 'cedula', 'telefono', 'correo', 'referencia', 'fecha_registro'])


def verificar_disponibilidad(fecha, h_inicio, h_fin):
    conn = conectar_db()
    query = f"""
    SELECT id_cita FROM citas WHERE fecha = '{fecha}' AND estado != 'Cancelada'
    AND (('{h_inicio}' >= hora_inicio AND '{h_inicio}' < hora_fin) OR
         ('{h_fin}' > hora_inicio AND '{h_fin}' <= hora_fin) OR
         (hora_inicio >= '{h_inicio}' AND hora_inicio < '{h_fin}'))
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df.empty




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
    
    conn = conectar_db()
    query = f"""
        SELECT c.id_cita, c.hora_inicio, c.hora_fin, p.nombre, IFNULL(p.cedula, 'S/N') as cedula, c.estado 
        FROM citas c JOIN pacientes p ON c.id_paciente = p.id_paciente 
        WHERE c.fecha = '{fecha_agenda}' ORDER BY c.hora_inicio ASC
    """
    try:
        df_todas = pd.read_sql(query, conn)
        df_activas = df_todas[df_todas['estado'] != 'Cancelada']
        
        # --- MAPA DE DISPONIBILIDAD HORARIA ---
        st.write("### 🕒 Ocupación del Sillón Dental")
        horas_dia = pd.date_range(start="07:00", end="17:00", freq="30min").time
        
        num_cols = 5
        cols = st.columns(num_cols)
        
        for i, h in enumerate(horas_dia):
            ocupado = False
            if not df_activas.empty:
                for _, r in df_activas.iterrows():
                    inicio = (datetime.min + r['hora_inicio']).time() if isinstance(r['hora_inicio'], timedelta) else r['hora_inicio']
                    fin = (datetime.min + r['hora_fin']).time() if isinstance(r['hora_fin'], timedelta) else r['hora_fin']
                    if h >= inicio and h < fin:
                        ocupado = True
                        break
            
            with cols[i % num_cols]:
                if ocupado: 
                    st.error(f"{h.strftime('%H:%M')}")
                else: 
                    st.success(f"{h.strftime('%H:%M')}")

        st.divider()
        
        # --- 2. RANGOS OCUPADOS ---
        if not df_activas.empty:
            st.write("### ⏳ Horarios Reservados")
            for _, row in df_activas.iterrows():
                h_i_obj = (datetime.min + row['hora_inicio']).time() if isinstance(row['hora_inicio'], timedelta) else row['hora_inicio']
                h_f_obj = (datetime.min + row['hora_fin']).time() if isinstance(row['hora_fin'], timedelta) else row['hora_fin']
                h_i, h_f = h_i_obj.strftime('%H:%M'), h_f_obj.strftime('%H:%M')
                
                st.warning(f"**Ocupado de {h_i} a {h_f}** | Paciente: {row['nombre']} (ID: {row['cedula']})")
        else:
            st.info("🎉 Sillón libre. No hay citas programadas para este día.")

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
                elif verificar_disponibilidad(fecha, h_i, h_f):
                    conn = conectar_db()
                    cursor = conn.cursor()
                    cursor.execute("INSERT INTO citas (id_paciente, fecha, hora_inicio, hora_fin) VALUES (%s,%s,%s,%s)", (p_id, fecha, h_i, h_f))
                    conn.commit()
                    conn.close()
                    st.success("✅ ¡Cita dental reservada correctamente!")
                    st.balloons()
                    t_sleep.sleep(1.5)
                    st.rerun()
                else: 
                    st.error("❌ El sillón dental se encuentra ocupado en ese rango de tiempo.")

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
            
            if st.form_submit_button("Guardar Ficha Paciente"):
                if n.strip() == "":
                    st.error("❌ El nombre completo del paciente es obligatorio.")
                else:
                    try:
                        conn = conectar_db()
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO pacientes (nombre, cedula, telefono, correo, referencia) VALUES (%s,%s,%s,%s,%s)", 
                            (n, id_c if id_c else None, t, m, r)
                        )
                        conn.commit()
                        st.success(f"🎉 ¡Paciente '{n}' registrado con éxito!")
                        
                        # Pausa de 1 segundo para que veas el mensaje verde y recarga limpia
                        t_sleep.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar: {e}")
                    finally:
                        if 'conn' in locals() and conn:
                            conn.close()

    with tab2:
        st.write("### 📜 Registro Histórico de Evoluciones Dentales")
        df_p = obtener_pacientes()
        
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
            f_reg = info_paciente['fecha_registro']
            f_reg_str = f_reg.strftime('%d/%m/%Y') if hasattr(f_reg, 'strftime') else "No registrada"

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
        
        df_p_all = obtener_pacientes()
        
        if df_p_all.empty:
            st.warning("No hay pacientes registrados en el sistema.")
        else:
            # 1. Buscador centralizado de paciente
            paciente_master_id = st.selectbox(
                "Seleccione el paciente para abrir su Expediente Único:",
                options=df_p_all['id_paciente'].tolist(),
                format_func=lambda x: f"{df_p_all[df_p_all['id_paciente']==x]['nombre'].values[0]} | Cédula: {df_p_all[df_p_all['id_paciente']==x]['cedula'].values[0]}",
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
            
            # Intentamos una conexión rápida de prueba para verificar el estado real
            try:
                test_conn = conectar_db()
                cursor_test = test_conn.cursor()
                # Le pedimos al servidor MySQL que nos diga su versión actual
                cursor_test.execute("SELECT VERSION()")
                version_mysql = cursor_test.fetchone()[0]
                test_conn.close()
                
                # Si todo sale bien, muestra el éxito con datos reales del servidor
                st.success(f"🟢 **Conexión Exitosa:** El sistema está conectado a la base de datos local corriendo en XAMPP (MySQL v{version_mysql}).")
                st.caption("📍 Host: `localhost` | Puerto: `3306` | Base de Datos: `dentcal_db`")
                
            except Exception as e:
                # Si XAMPP está apagado o el puerto bloqueado, saltará este aviso en rojo de inmediato
                st.error(f"🔴 **Servidor Desconectado:** No se pudo establecer comunicación con XAMPP/MySQL.")
                st.warning(f"Detalle del error: {e}")
                st.info("💡 Asegúrate de abrir el Panel de Control de XAMPP y verificar que el servicio 'MySQL' esté iniciado (en verde).")
            
    else:
        st.warning("⚠️ Acceso denegado. Este módulo está reservado exclusivamente para cuentas con rol de Administrador.")
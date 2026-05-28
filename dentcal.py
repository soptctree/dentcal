# --- PESTAÑA 4: MÓDULO DE FACTURACIÓN Y LIQUIDACIÓN ---
# ==============================================================================
with tab_facturacion:
    # 0. ASEGURAR EXISTENCIA DE LA TABLA INGRESOS
    try:
        conn_init = conectar_db()
        with conn_init.cursor() as cursor_init:
            cursor_init.execute("""
                CREATE TABLE IF NOT EXISTS ingresos (
                    id_ingreso INT AUTO_INCREMENT PRIMARY KEY,
                    id_cita INT NOT NULL,
                    id_paciente INT NOT NULL,
                    monto DECIMAL(10,2) NOT NULL,
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
        
        # Leemos el monto calculado final de tu balance contable
        monto_a_cobrar = st.session_state.get('monto_calculado_neto', 305.00)
        
        # Si no se ha asentado el pago, mostramos el botón de acción principal
        if not st.session_state.get('pago_exitoso'):
            if st.button("🔒 Confirmar Pago y Asentar en Libros", type="primary", use_container_width=True):
                try:
                    conn = conectar_db()
                    with conn.cursor() as cursor:
                        # Guardamos el registro en la tabla de ingresos de TiDB Cloud
                        sql_insert = """
                            INSERT INTO ingresos (id_cita, id_paciente, monto, fecha) 
                            VALUES (%s, %s, %s, NOW())
                        """
                        cursor.execute(sql_insert, (id_cita_sel, id_p_seguro, monto_a_cobrar))
                        # Cambiamos el estado de la cita
                        cursor.execute("UPDATE citas SET estado = 'Asistió' WHERE id_cita = %s", (id_cita_sel,))
                    conn.commit()
                    
                    st.session_state['pago_exitoso'] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error al registrar en la base de datos: {e}")
                finally:
                    if 'conn' in locals() and conn: conn.close()
        
        # Si el pago ya fue asentado con éxito, liberamos las opciones de exportación de manera limpia
        if st.session_state.get('pago_exitoso'):
            st.info("🎉 ¡El pago ha sido registrado con éxito en el sistema!")
            
            # Definimos la función generadora en caliente para pasar al botón de descarga sin variables previas vacías
            def generar_pdf_recibo():
                from reportlab.lib.pagesizes import letter
                from reportlab.platypus import SimpleDocTemplate, Paragraph
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib import colors
                import io
                from datetime import datetime

                buffer = io.BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
                story = []
                styles = getSampleStyleSheet()
                
                title_style = ParagraphStyle('TStyle', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor("#1E3A8A"), spaceAfter=12)
                normal_style = ParagraphStyle('NStyle', parent=styles['Normal'], fontSize=11, spaceAfter=6)
                
                story.append(Paragraph("🦷 DENTCAL - CONTROL PROFESIONAL", title_style))
                story.append(Paragraph(f"<b>Recibo de Pago - Cita #{id_cita_sel}</b>", normal_style))
                story.append(Paragraph(f"<b>Paciente:</b> {nombre_paciente}", normal_style))
                story.append(Paragraph(f"<b>Monto Neto Recaudado:</b> ${monto_a_cobrar:,.2f}", normal_style))
                story.append(Paragraph(f"<b>Fecha de Emisión:</b> {datetime.now().strftime('%d-%m-%Y %H:%M')}", normal_style))
                
                doc.build(story)
                buffer.seek(0)
                return buffer.getvalue()

            c_down, c_wa, c_em = st.columns(3)
            with c_down:
                # Al pasar 'data=generar_pdf_recibo' (como función), Streamlit la ejecuta BAJO DEMANDA al hacer clic, evitando el TypeError
                st.download_button(
                    label="📥 Descargar PDF Comercial",
                    data=generar_pdf_recibo(),
                    fileName=f"Recibo_Cita_{id_cita_sel}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            
            with c_wa:
                import urllib.parse
                texto_wa = f"Hola {nombre_paciente}, confirmamos el pago de tu consulta por ${monto_a_cobrar:,.2f}. ¡Muchas gracias!"
                url_wa = f"https://wa.me/?text={urllib.parse.quote(texto_wa)}"
                st.markdown(f'<a href="{url_wa}" target="_blank"><button style="width:100%; height:38px; background-color:#25D366; color:white; border:none; border-radius:4px; cursor:pointer; font-weight:bold;">💬 Enviar WhatsApp</button></a>', unsafe_allow_html=True)
                
            with c_em:
                import urllib.parse
                asunto_m = f"Comprobante DentCal - Cita #{id_cita_sel}"
                cuerpo_m = f"Estimado/a {nombre_paciente},\n\nConfirmamos su pago de ${monto_a_cobrar:,.2f}.\n\nSaludos."
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
        query_ingresos = """
            SELECT i.id_ingreso, p.nombre AS paciente, i.monto, i.fecha 
            FROM ingresos i
            JOIN pacientes p ON i.id_paciente = p.id_paciente
            WHERE DATE(i.fecha) = CURDATE()
            ORDER BY i.fecha DESC
        """
        df_ingresos = pd.read_sql(query_ingresos, conn_historial)
        
        if not df_ingresos.empty:
            df_ingresos['monto'] = df_ingresos['monto'].apply(lambda x: f"${x:,.2f}")
            df_ingresos['fecha'] = pd.to_datetime(df_ingresos['fecha']).dt.strftime('%H:%M:%S')
            df_ingresos.columns = ["ID Ingreso", "Paciente", "Monto Recaudado", "Hora de Pago"]
            
            with conn_historial.cursor() as cur_t:
                cur_t.execute("SELECT SUM(monto) FROM ingresos WHERE DATE(fecha) = CURDATE()")
                total_dia = cur_t.fetchone()[0] or 0.0
            
            st.metric(label="💰 Total Recaudado en Caja Hoy", value=f"${total_dia:,.2f}")
            st.dataframe(df_ingresos, use_container_width=True)
        else:
            st.warning("📭 Aún no se han registrado cobros ni entradas de dinero el día de hoy.")
            
    except Exception as e_hist:
        st.caption("Historial temporalmente en espera de transacciones.")
    finally:
        if conn_historial: 
            conn_historial.close()

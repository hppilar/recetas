import streamlit as st
import json
import pandas as pd
from PIL import Image
import io

# --- CONFIGURACIÓN ---
st.set_page_config(
    page_title="Recetas de Repostería Pro",
    page_icon="🧁",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- CONSTANTES Y CONFIGURACIÓN ---
# ¡ADVERTENCIA! Esto no es seguro para producción. Usa st.secrets para apps reales.
ADMIN_PASSWORD = "admin123"
DATA_FILE = 'data/recetas.json'

# --- FUNCIONES DE MANEJO DE DATOS ---
@st.cache_data(ttl=60) # Se actualiza cada 60 segundos para permitir cambios
def load_data():
    """Carga los datos desde el archivo JSON."""
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        st.error(f"El archivo '{DATA_FILE}' no fue encontrado.")
        return {"ingredientes_globales": {}, "recetas": []}

def save_data(data):
    """Guarda los datos en el archivo JSON."""
    with st.spinner('Guardando cambios...'):
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        st.cache_data.clear()
        st.toast("✅ ¡Cambios guardados con éxito!", icon="success")

# --- FUNCIONES DE PÁGINA (NUEVAS Y MODIFICADAS) ---

def show_login():
    """Muestra la interfaz de login en la barra lateral."""
    if not st.session_state.get('logged_in', False):
        st.sidebar.subheader("Acceso de Administrador")
        password = st.sidebar.text_input("Contraseña", type="password")
        if st.sidebar.button("Ingresar"):
            if password == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.sidebar.success("Acceso concedido.")
                st.rerun()
            else:
                st.sidebar.error("Contraseña incorrecta.")
    else:
        st.sidebar.success(f"Administrador logueado.")
        if st.sidebar.button("Cerrar sesión"):
            st.session_state.logged_in = False
            st.session_state.current_page = 'menu'
            st.rerun()

def page_menu(data):
    """Muestra el menú principal de recetas con búsqueda."""
    st.title("🧁 Mis Recetas de Repostería")
    
    # --- NUEVO: Barra de búsqueda ---
    search_query = st.text_input("🔍 Buscar recetas...", placeholder="Escribe el nombre de una receta...").lower()
    
    # Filtrar recetas basadas en la búsqueda
    if search_query:
        recetas_filtradas = [r for r in data['recetas'] if search_query in r['nombre'].lower()]
    else:
        recetas_filtradas = data['recetas']

    if not recetas_filtradas:
        st.warning("No se encontraron recetas con ese nombre.")
        return

    st.write(f"Mostrando {len(recetas_filtradas)} receta(s).")
    
    cols = st.columns(3)
    for i, receta in enumerate(recetas_filtradas):
        with cols[i % 3]:
            with st.container(border=True):
                st.image(receta['imagen'], use_column_width='always')
                st.subheader(receta['nombre'])
                if st.button("Ver Receta", key=f"btn_{receta['id']}"):
                    st.session_state.receta_seleccionada_id = receta['id']
                    st.session_state.current_page = 'detalle'
                    st.rerun()

def page_detalle(data):
    """Muestra el detalle de una receta con edición mejorada y opción de borrar."""
    receta_index = next((i for i, r in enumerate(data['recetas']) if r['id'] == st.session_state.receta_seleccionada_id), None)
    if receta_index is None:
        st.error("Receta no encontrada.")
        return
    
    receta = data['recetas'][receta_index]

    if st.button("← Volver al menú"):
        st.session_state.current_page = 'menu'
        st.rerun()

    # --- MODO EDICIÓN MEJORADO ---
    if st.session_state.get('logged_in', False):
        edit_mode = st.sidebar.toggle("📝 Modo Edición", key="edit_toggle")
        if edit_mode:
            st.header(f"Editando: {receta['nombre']}")
            
            # --- NUEVO: Botón de eliminar receta ---
            if st.button("🗑️ Eliminar Esta Receta", type="secondary"):
                st.session_state.receta_a_borrar_index = receta_index
                st.session_state.mostrar_confirmacion_borrado = True
            
            # --- NUEVO: Confirmación de borrado ---
            if st.session_state.get('mostrar_confirmacion_borrado', False):
                st.error(f"¿Estás seguro de que quieres eliminar '{receta['nombre']}'? Esta acción no se puede deshacer.")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Sí, eliminar", type="primary"):
                        data['recetas'].pop(receta_index)
                        save_data(data)
                        st.session_state.current_page = 'menu'
                        st.session_state.mostrar_confirmacion_borrado = False
                        st.rerun()
                with col2:
                    if st.button("Cancelar"):
                        st.session_state.mostrar_confirmacion_borrado = False
                        st.rerun()
                return # Detener la ejecución mientras se muestra la confirmación

            # Formulario de edición
            with st.form("edit_recipe_form"):
                nuevo_id = st.text_input("ID Único", value=receta['id'])
                nuevo_nombre = st.text_input("Nombre de la receta", value=receta['nombre'])
                nueva_imagen = st.text_input("Ruta de la imagen", value=receta['imagen'])
                
                # --- NUEVO: Edición dinámica de ingredientes ---
                st.subheader("Ingredientes")
                num_ingredientes = st.session_state.get('num_ingredientes_edit', len(receta['ingredientes']))
                
                if st.button("➕ Añadir Ingrediente"):
                    st.session_state.num_ingredientes_edit = num_ingredientes + 1
                    st.rerun()
                
                ingredientes_editados = []
                for i in range(num_ingredientes):
                    cols = st.columns([3, 1, 1])
                    with cols[0]:
                        nombre_ing = st.selectbox("Ingrediente", options=list(data['ingredientes_globales'].keys()), key=f"ing_name_{i}")
                    with cols[1]:
                        cantidad_ing = st.number_input("Cantidad", value=receta['ingredientes'][i]['cantidad'] if i < len(receta['ingredientes']) else 1.0, key=f"ing_cant_{i}")
                    ingredientes_editados.append({"nombre": nombre_ing, "cantidad": cantidad_ing})
                
                # --- NUEVO: Edición dinámica de pasos ---
                st.subheader("Pasos")
                num_pasos = st.session_state.get('num_pasos_edit', len(receta['pasos']))
                if st.button("➕ Añadir Paso"):
                    st.session_state.num_pasos_edit = num_pasos + 1
                    st.rerun()
                
                pasos_editados = []
                for i in range(num_pasos):
                    paso_texto = receta['pasos'][i] if i < len(receta['pasos']) else ""
                    pasos_editados.append(st.text_area(f"Paso {i+1}", value=paso_texto, key=f"paso_{i}"))
                
                submitted = st.form_submit_button("💾 Guardar Cambios en esta Receta")
                if submitted:
                    # Actualizar el diccionario de la receta en memoria
                    receta['id'] = nuevo_id
                    receta['nombre'] = nuevo_nombre
                    receta['imagen'] = nueva_imagen
                    receta['ingredientes'] = ingredientes_editados
                    receta['pasos'] = pasos_editados
                    save_data(data)
                    st.session_state.num_ingredientes_edit = None
                    st.session_state.num_pasos_edit = None
                    st.rerun()
            return

    # --- MODO VISUALIZACIÓN NORMAL ---
    st.title(receta['nombre'])
    st.image(receta['imagen'], width=500)

    # (Código de la calculadora - se adapta al nuevo JSON)
    st.header("🥄 Calculadora de Ingredientes y Costos")
    cantidad_deseada = st.number_input(f"¿Cuántas {receta['unidad_base']} quieres hacer?", min_value=1, value=receta['cantidad_base'], step=1)
    factor_escala = cantidad_deseada / receta['cantidad_base']

    datos_tabla = []
    costo_total_receta = 0.0
    for ing_receta in receta['ingredientes']:
        info_global = data['ingredientes_globales'].get(ing_receta['nombre'])
        if not info_global:
            st.error(f"No se encontró información global para el ingrediente: {ing_receta['nombre']}")
            continue
        
        cantidad_final = ing_receta['cantidad'] * factor_escala
        costo_total_ingrediente = cantidad_final * info_global['costo_por_unidad']
        costo_total_receta += costo_total_ingrediente
        
        datos_tabla.append({
            "Ingrediente": ing_receta['nombre'],
            "Cantidad": f"{round(cantidad_final, 2)} {info_global['unidad_base']}",
            "Costo Unitario": f"${info_global['costo_por_unidad']:.4f}/{info_global['unidad_base']}",
            "Costo Total": f"${round(costo_total_ingrediente, 2):.2f}"
        })
    
    df = pd.DataFrame(datos_tabla)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.metric(label="💰 Costo Total de la Receta", value=f"${round(costo_total_receta, 2):.2f}")

    st.header("📝 Instrucciones")
    for i, paso in enumerate(receta['pasos']):
        st.write(f"{i+1}. {paso}")

def page_editar_precios(data):
    """Página para editar los precios de los ingredientes globales."""
    st.title("💰 Editar Precios de Ingredientes")
    st.write("Modifica el costo por unidad base de cada ingrediente.")
    
    with st.form("edit_prices_form"):
        ingredientes_editados = {}
        for nombre, info in data['ingredientes_globales'].items():
            cols = st.columns([2, 1, 1])
            with cols[0]:
                st.text(nombre)
            with cols[1]:
                st.text(f"({info['unidad_base']})")
            with cols[2]:
                nuevo_costo = st.number_input("Costo/Unidad", value=float(info['costo_por_unidad']), key=f"price_{nombre}", format="%.4f")
                ingredientes_editados[nombre] = {
                    "unidad_base": info['unidad_base'],
                    "costo_por_unidad": nuevo_costo
                }
        
        submitted = st.form_submit_button("Guardar Todos los Precios")
        if submitted:
            data['ingredientes_globales'] = ingredientes_editados
            save_data(data)
            st.rerun()

# --- NUEVAS PÁGINAS DE ADMINISTRACIÓN ---

def page_crear_receta(data):
    """Página para crear una nueva receta desde cero."""
    st.title("➕ Crear Nueva Receta")
    with st.form("create_recipe_form"):
        nuevo_id = st.text_input("ID Único (ej: pastel_nuevo)")
        nuevo_nombre = st.text_input("Nombre de la receta")
        nueva_imagen = st.text_input("Ruta de la imagen (ej: images/pastel_nuevo.jpg)")
        nueva_cantidad_base = st.number_input("Cantidad base de la receta", value=1, step=1)
        nueva_unidad_base = st.text_input("Unidad base (ej: porciones, unidades)")
        
        st.subheader("Ingredientes")
        num_ingredientes = st.session_state.get('num_ingredientes_new', 3)
        if st.button("➕ Añadir Ingrediente", key="add_new_ing"):
            st.session_state.num_ingredientes_new = num_ingredientes + 1
            st.rerun()

        ingredientes_nuevos = []
        for i in range(num_ingredientes):
            cols = st.columns([3, 1])
            with cols[0]:
                nombre_ing = st.selectbox("Ingrediente", options=list(data['ingredientes_globales'].keys()), key=f"new_ing_name_{i}")
            with cols[1]:
                cantidad_ing = st.number_input("Cantidad", value=100.0, key=f"new_ing_cant_{i}")
            ingredientes_nuevos.append({"nombre": nombre_ing, "cantidad": cantidad_ing})

        st.subheader("Pasos")
        num_pasos = st.session_state.get('num_pasos_new', 3)
        if st.button("➕ Añadir Paso", key="add_new_step"):
            st.session_state.num_pasos_new = num_pasos + 1
            st.rerun()

        pasos_nuevos = []
        for i in range(num_pasos):
            pasos_nuevos.append(st.text_area(f"Paso {i+1}", key=f"new_paso_{i}"))

        submitted = st.form_submit_button("✅ Crear Receta")
        if submitted:
            # Validar que el ID no exista
            if any(r['id'] == nuevo_id for r in data['recetas']):
                st.error(f"El ID '{nuevo_id}' ya existe. Por favor, elige otro.")
            else:
                nueva_receta = {
                    "id": nuevo_id,
                    "nombre": nuevo_nombre,
                    "imagen": nueva_imagen,
                    "cantidad_base": nueva_cantidad_base,
                    "unidad_base": nueva_unidad_base,
                    "ingredientes": ingredientes_nuevos,
                    "pasos": pasos_nuevos
                }
                data['recetas'].append(nueva_receta)
                save_data(data)
                st.session_state.num_ingredientes_new = None
                st.session_state.num_pasos_new = None
                st.success(f"Receta '{nuevo_nombre}' creada con éxito.")
                st.session_state.current_page = 'menu'
                st.rerun()

def page_gestionar_ingredientes(data):
    """Página para añadir y eliminar ingredientes globales."""
    st.title("🛒 Gestionar Ingredientes Globales")
    
    st.subheader("Añadir Nuevo Ingrediente")
    with st.form("add_ingredient_form"):
        nuevo_nombre = st.text_input("Nombre del nuevo ingrediente")
        nueva_unidad = st.text_input("Unidad base (ej: kg, litros)")
        nuevo_costo = st.number_input("Costo por unidad", value=0.0, format="%.4f")
        if st.form_submit_button("➕ Añadir Ingrediente"):
            if nuevo_nombre in data['ingredientes_globales']:
                st.warning(f"El ingrediente '{nuevo_nombre}' ya existe.")
            else:
                data['ingredientes_globales'][nuevo_nombre] = {
                    "unidad_base": nueva_unidad,
                    "costo_por_unidad": nuevo_costo
                }
                save_data(data)
                st.rerun()

    st.subheader("Eliminar Ingrediente")
    ingrediente_a_borrar = st.selectbox("Selecciona un ingrediente para eliminar", options=list(data['ingredientes_globales'].keys()))
    if st.button("🗑️ Eliminar Seleccionado"):
        if ingrediente_a_borrar:
            del data['ingredientes_globales'][ingrediente_a_borrar]
            save_data(data)
            st.toast(f"Ingrediente '{ingrediente_a_borrar}' eliminado.", icon="success")
            st.rerun()

def page_importar_excel(data):
    """Página para importar y exportar ingredientes desde un archivo Excel."""
    st.title("📊 Importar/Exportar Ingredientes con Excel")
    
    st.subheader("Exportar Ingredientes Actuales")
    if st.button("📥 Descargar Plantilla Excel"):
        df = pd.DataFrame.from_dict(data['ingredientes_globales'], orient='index').reset_index()
        df.rename(columns={'index': 'Nombre'}, inplace=True)
        # Reordenar columnas para que coincidan con el formato
        df = df[['Nombre', 'unidad_base', 'costo_por_unidad']]
        df.rename(columns={'unidad_base': 'Unidad_Base', 'costo_por_unidad': 'Costo_Por_Unidad'}, inplace=True)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Ingredientes', index=False)
        st.download_button(
            label="Descargar ingredientes.xlsx",
            data=output.getvalue(),
            file_name="ingredientes_plantilla.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    st.divider()
    st.subheader("Importar Ingredientes desde Excel")
    uploaded_file = st.file_uploader("Elige un archivo Excel", type="xlsx")
    
    if uploaded_file:
        try:
            df_importado = pd.read_excel(uploaded_file, sheet_name='Ingredientes')
            required_columns = ['Nombre', 'Unidad_Base', 'Costo_Por_Unidad']
            if not all(col in df_importado.columns for col in required_columns):
                st.error(f"El archivo Excel debe tener las columnas: {', '.join(required_columns)}")
            else:
                st.dataframe(df_importado)
                if st.button("📤 Confirmar Importación y Sobrescribir Precios"):
                    with st.spinner("Importando datos..."):
                        nuevos_ingredientes = {}
                        for index, row in df_importado.iterrows():
                            nombre = row['Nombre']
                            if pd.isna(nombre):
                                continue
                            nuevos_ingredientes[nombre] = {
                                "unidad_base": row['Unidad_Base'],
                                "costo_por_unidad": float(row['Costo_Por_Unidad'])
                            }
                        data['ingredientes_globales'] = nuevos_ingredientes
                        save_data(data)
                        st.success("¡Ingredientes importados y guardados con éxito!")
                        st.rerun()
        except Exception as e:
            st.error(f"Ocurrió un error al leer el archivo: {e}")


# --- LÓGICA PRINCIPAL ---
def main():
    # Inicializar estado de la sesión
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'menu'

    data = load_data()

    # --- BARRA LATERAL ---
    with st.sidebar:
        show_login()

        st.title("Navegación")
        if st.button("📖 Ver Recetas", use_container_width=True):
            st.session_state.current_page = 'menu'
            st.rerun()
        
        if st.session_state.logged_in:
            st.divider()
            st.subheader("Panel de Administración")
            if st.button("➕ Crear Receta", use_container_width=True):
                st.session_state.current_page = 'crear_receta'
                st.rerun()
            if st.button("💰 Editar Precios", use_container_width=True):
                st.session_state.current_page = 'editar_precios'
                st.rerun()
            if st.button("🛒 Gestionar Ingredientes", use_container_width=True):
                st.session_state.current_page = 'gestionar_ingredientes'
                st.rerun()
            if st.button("📊 Importar/Exportar Excel", use_container_width=True):
                st.session_state.current_page = 'importar_excel'
                st.rerun()

    # --- CONTENIDO PRINCIPAL ---
    if st.session_state.current_page == 'menu':
        page_menu(data)
    elif st.session_state.current_page == 'detalle':
        page_detalle(data)
    elif st.session_state.current_page == 'editar_precios':
        page_editar_precios(data)
    elif st.session_state.current_page == 'crear_receta':
        page_crear_receta(data)
    elif st.session_state.current_page == 'gestionar_ingredientes':
        page_gestionar_ingredientes(data)
    elif st.session_state.current_page == 'importar_excel':
        page_importar_excel(data)

if __name__ == '__main__':
    main()

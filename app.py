import streamlit as st
import json
import pandas as pd
from PIL import Image

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Recetas de Repostería", page_icon="🧁", layout="centered")

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
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    st.success("¡Cambios guardados con éxito!")
    # Limpiar el cache para que la próxima carga lea los nuevos datos
    st.cache_data.clear()

# --- FUNCIONES DE PÁGINA ---
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
    """Muestra el menú principal de recetas."""
    st.title("🧁 Mis Recetas de Repostería")
    st.write("Selecciona una receta para ver los detalles.")
    
    cols = st.columns(3)
    for i, receta in enumerate(data['recetas']):
        with cols[i % 3]:
            with st.container(border=True):
                st.image(receta['imagen'], use_column_width='always')
                st.subheader(receta['nombre'])
                if st.button("Ver Receta", key=f"btn_{receta['id']}"):
                    st.session_state.receta_seleccionada_id = receta['id']
                    st.session_state.current_page = 'detalle'
                    st.rerun()

def page_detalle(data):
    """Muestra el detalle de una receta y permite editar si está en modo admin."""
    receta = next((r for r in data['recetas'] if r['id'] == st.session_state.receta_seleccionada_id), None)
    if not receta:
        st.error("Receta no encontrada.")
        return

    if st.button("← Volver al menú"):
        st.session_state.current_page = 'menu'
        st.rerun()

    # --- MODO EDICIÓN ---
    if st.session_state.get('logged_in', False):
        edit_mode = st.sidebar.toggle("📝 Modo Edición", key="edit_toggle")
        if edit_mode:
            st.header(f"Editando: {receta['nombre']}")
            # Formulario de edición
            with st.form("edit_recipe_form"):
                nuevo_nombre = st.text_input("Nombre de la receta", value=receta['nombre'])
                nueva_imagen = st.text_input("Ruta de la imagen", value=receta['imagen'])
                
                st.subheader("Ingredientes")
                ingredientes_editados = []
                for i, ing in enumerate(receta['ingredientes']):
                    cols = st.columns([3, 1, 1])
                    with cols[0]:
                        nombre_ing = st.selectbox("Ingrediente", options=list(data['ingredientes_globales'].keys()), index=list(data['ingredientes_globales'].keys()).index(ing['nombre']), key=f"ing_name_{i}")
                    with cols[1]:
                        cantidad_ing = st.number_input("Cantidad", value=ing['cantidad'], key=f"ing_cant_{i}")
                    with cols[2]:
                        st.markdown("<br>", unsafe_allow_html=True) # Alinea el botón
                        if st.button("❌", key=f"del_ing_{i}"):
                            # Lógica para eliminar se maneja fuera del form por complejidad de estado
                            pass # Se implementará con estado de sesión
                    ingredientes_editados.append({"nombre": nombre_ing, "cantidad": cantidad_ing})
                
                if st.button("➕ Añadir Ingrediente"):
                    # Esto requiere manejo de estado dinámico, es complejo en Streamlit.
                    # Una alternativa es permitir un número fijo de "slots" vacíos.
                    st.warning("Funcionalidad de añadir/eliminar ingredientes requiere un manejo de estado más avanzado.")

                st.subheader("Pasos")
                pasos_editados = []
                for i, paso in enumerate(receta['pasos']):
                    pasos_editados.append(st.text_area(f"Paso {i+1}", value=paso, key=f"paso_{i}"))
                
                # Botón de guardado
                submitted = st.form_submit_button("💾 Guardar Cambios en esta Receta")
                if submitted:
                    # Confirmación
                    if st.sidebar.button("Confirmar Guardado", type="primary"):
                        # Actualizar el diccionario de la receta en memoria
                        receta['nombre'] = nuevo_nombre
                        receta['imagen'] = nueva_imagen
                        receta['ingredientes'] = ingredientes_editados
                        receta['pasos'] = pasos_editados
                        save_data(data)
                        st.rerun()
                    else:
                        st.sidebar.warning("Haz clic en 'Confirmar Guardado' para aplicar los cambios.")
            return # Detener la ejecución de la vista normal

    # --- MODO VISUALIZACIÓN NORMAL ---
    st.title(receta['nombre'])
    st.image(receta['imagen'], width=500)

    # (El resto del código de cálculo de ingredientes y costos va aquí)
    # ... (Código de la calculadora que ya teníamos) ...
    # ... Se adapta para usar el nuevo formato de datos ...
    
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
                # El valor debe ser un float para el input
                nuevo_costo = st.number_input("Costo/Unidad", value=float(info['costo_por_unidad']), key=f"price_{nombre}", format="%.4f")
                ingredientes_editados[nombre] = {
                    "unidad_base": info['unidad_base'],
                    "costo_por_unidad": nuevo_costo
                }
        
        submitted = st.form_submit_button("Guardar Todos los Precios")
        if submitted:
            if st.sidebar.button("Confirmar Cambios de Precios", type="primary"):
                data['ingredientes_globales'] = ingredientes_editados
                save_data(data)
                st.rerun()
            else:
                st.sidebar.warning("Confirma los cambios en la barra lateral.")

# --- LÓGICA PRINCIPAL ---
def main():
    # Inicializar estado de la sesión
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'menu'

    data = load_data()

    # --- BARRA LATERAL ---
    show_login()

    st.sidebar.title("Navegación")
    if st.sidebar.button("📖 Ver Recetas", use_container_width=True):
        st.session_state.current_page = 'menu'
        st.rerun()
    
    if st.session_state.logged_in:
        st.sidebar.divider()
        st.sidebar.subheader("Panel de Administración")
        if st.sidebar.button("💰 Editar Precios", use_container_width=True):
            st.session_state.current_page = 'editar_precios'
            st.rerun()
        # Aquí se podrían añadir más botones para otras páginas de admin

    # --- CONTENIDO PRINCIPAL ---
    if st.session_state.current_page == 'menu':
        page_menu(data)
    elif st.session_state.current_page == 'detalle':
        page_detalle(data)
    elif st.session_state.current_page == 'editar_precios':
        page_editar_precios(data)

if __name__ == '__main__':
    main()
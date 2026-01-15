import streamlit as st
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
import io
import json
import base64
import os

# --- ⚙️ CONFIGURACIÓN ---

# Poner en True para probar GRATIS (simulación).
# Poner en False para usar la IA y gastar saldo.
MODO_PRUEBA = True 

# Tu API KEY de OpenAI (Reemplaza esto cuando pongas MODO_PRUEBA = False)
# O mejor aún, usa st.secrets en producción.
API_KEY = "sk-TU_CLAVE_AQUI" 

# --- FUNCIONES ---

def encode_image(image):
    """Convierte la imagen a base64 para enviarla a la API."""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def get_mock_response():
    """Simula una respuesta de la IA para no gastar dinero."""
    return {
        "elements": [
            {
                "text": "PRUEBA: TEXTO ARRIBA",
                "color": "#FF00FF", # Magenta
                "size_percentage": 8,
                "x_percentage": 50,
                "y_percentage": 15,
                "alignment": "center"
            },
            {
                "text": "Esto es una simulación",
                "color": "#FFFFFF", # Blanco
                "size_percentage": 5,
                "x_percentage": 50,
                "y_percentage": 85,
                "alignment": "center"
            }
        ]
    }

def analyze_and_get_layout(image, user_instruction):
    """Decide si llamar a la IA o usar el Mock según la configuración."""
    
    if MODO_PRUEBA:
        # Simular retardo para que parezca real
        import time
        time.sleep(1) 
        return get_mock_response()

    try:
        api_key = st.secrets["OPENAI_API_KEY"]
    except:
        # Por si te olvidas de configurarlo, que avise
        st.error("No se encontró la API KEY. Configurala en los Secrets.")
        st.stop()

    # --- LÓGICA REAL DE IA ---
    client = OpenAI(api_key=api_key)
    base64_image = encode_image(image)
    
    prompt_system = """
    Eres un diseñador experto. Recibes una imagen y una instrucción.
    Devuelve SOLAMENTE un JSON con este formato.
    
    Tienes disponibles estos estilos de fuente: "moderna", "elegante", "impacto".
    Elige el que mejor se adapte a la intención del texto (ej: "elegante" para saludos, "impacto" para descuentos).

    {
        "elements": [
            {
                "text": "string",
                "color": "#HEX",
                "size_percentage": int (1-100),
                "font_style": "moderna" | "elegante" | "impacto",  <-- NUEVO CAMPO
                "x_percentage": int (0-100),
                "y_percentage": int (0-100),
                "alignment": "left|center|right"
            }
        ]
    }
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini", # Usamos mini para que sea barato
        messages=[
            {"role": "system", "content": prompt_system},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Instrucción: {user_instruction}"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}},
                ],
            },
        ],
        response_format={"type": "json_object"}
    )
    
    content = response.choices[0].message.content
    return json.loads(content)

def draw_text_on_image(image, layout_data):
    """Dibuja el texto sobre la imagen."""
    draw = ImageDraw.Draw(image)
    width, height = image.size
    
    # Intenta cargar una fuente del sistema, sino usa la default
    # TIP: Para que quede lindo, descarga una fuente .ttf (ej. Roboto.ttf) y ponla junto al script
    fuentes_map = {
        "moderna": "fuentes/moderna.ttf",
        "elegante": "fuentes/elegante.ttf",
        "impacto": "fuentes/impacto.ttf"
    }
    
    # Fuente por defecto por si algo falla
    default_font_path = "fuentes/moderna.ttf"
    
    for el in layout_data['elements']:
        target_pixel_size = int(height * (el['size_percentage'] / 100))
        
        # 1. Identificar qué estilo pidió la IA
        estilo_elegido = el.get('font_style', 'moderna') # 'moderna' es el backup
        ruta_fuente = fuentes_map.get(estilo_elegido, default_font_path)

        # 2. Cargar la fuente correcta
        try:
            font = ImageFont.truetype(ruta_fuente, target_pixel_size)
        except:
            # Si falla (ej. no encuentra el archivo), usa la default de sistema
            font = ImageFont.load_default()

        text = el['text']
        color = el['color']
        
        # Posición
        x = int(width * (el['x_percentage'] / 100))
        y = int(height * (el['y_percentage'] / 100))
        
        # Anclajes
        anchor_map = {'left': 'lm', 'center': 'mm', 'right': 'rm'}
        anchor = anchor_map.get(el['alignment'], 'mm')
        
        # Borde negro para legibilidad (stroke)
        stroke_width = max(1, int(target_pixel_size / 15))
        
        draw.text((x, y), text, font=font, fill=color, anchor=anchor, stroke_width=stroke_width, stroke_fill="black")
        
    return image

# --- INTERFAZ DE STREAMLIT ---

st.set_page_config(page_title="Editor Mamá AI", page_icon="🎨")

st.title("🎨 Editor Automático para Mamá")

if MODO_PRUEBA:
    st.info("🛠️ MODO PRUEBA ACTIVADO: No se cobrará nada. La IA está simulada.")

# 1. Cargar Archivo
uploaded_file = st.file_uploader("1. Subí la imagen o plantilla", type=["jpg", "png", "jpeg"])

# 2. Instrucción
instruction = st.text_area("2. ¿Qué le escribimos?", placeholder="Ej: Poner 'OFERTA' arriba en rojo y el precio abajo.")

if uploaded_file and instruction:
    if st.button("✨ Generar Imagen"):
        with st.spinner("El robot diseñador está trabajando..."):
            try:
                # Cargar imagen
                input_image = Image.open(uploaded_file).convert("RGB")
                
                # Obtener diseño (IA o Mock)
                layout = analyze_and_get_layout(input_image, instruction)
                
                # Dibujar
                final_image = draw_text_on_image(input_image.copy(), layout)
                
                # Mostrar
                st.image(final_image, caption="Resultado", use_container_width=True)
                
                # Botón de descarga
                buf = io.BytesIO()
                final_image.save(buf, format="PNG")
                byte_im = buf.getvalue()
                
                st.download_button(
                    label="⬇️ Descargar Imagen Lista",
                    data=byte_im,
                    file_name="diseño_listo.png",
                    mime="image/png"
                )
                
            except Exception as e:
                st.error(f"Ocurrió un error: {e}")
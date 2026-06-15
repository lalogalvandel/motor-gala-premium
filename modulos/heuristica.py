# modulos/heuristica.py
import json

PROMPT_SISTEMA_QUANT = """
Eres el Director de Estrategia Cuantitativa de un Hedge Fund. 
Tu única función es leer un conjunto de noticias financieras recientes y extraer "Vistas de Mercado" (Market Views) cuantitativas para alimentar un modelo de Black-Litterman.

REGLAS ESTRICTAS:
1. No escribas texto introductorio, ni explicaciones, ni resúmenes.
2. Tu salida debe ser EXCLUSIVAMENTE un arreglo JSON válido.
3. Solo puedes emitir una vista si la noticia sugiere un impacto claro y directo en el precio del activo a corto/mediano plazo.
4. Los rendimientos esperados ("rendimiento_esperado") deben ser números decimales realistas entre -0.50 y 0.50 (ej. un impacto positivo fuerte es 0.15, un impacto negativo es -0.10).
5. La "confianza" solo puede ser "Baja", "Media" o "Alta".
6. El "tipo" solo puede ser "absoluta" (el activo subirá/bajará por sí solo) o "relativa" (el activo superará a otro).

FORMATO DE SALIDA ESPERADO (ESTRICTO):
[
  {
    "tipo": "absoluta",
    "activo_1": "TICKER",
    "rendimiento_esperado": 0.12,
    "confianza": "Alta",
    "razonamiento_breve": "10 palabras máximo justificando el número basado en la noticia"
  },
  {
    "tipo": "relativa",
    "activo_1": "TICKER_A",
    "activo_2": "TICKER_B",
    "rendimiento_esperado": 0.05,
    "confianza": "Media",
    "razonamiento_breve": "10 palabras máximo"
  }
]
"""
# modulos/heuristica.py (continuación)

def generar_vistas_black_litterman(noticias_lista, tickers_universo, api_key):
    """
    Toma un arreglo de noticias (diccionarios), las sintetiza y llama al LLM
    para generar las vistas matemáticas de Black-Litterman.
    """
    import google.generativeai as genai
    
    # 1. Configurar la API de IA
    genai.configure(api_key=api_key)
    
    # Usamos un modelo rápido y barato para tareas de extracción estructurada
    model = genai.GenerativeModel('gemini-1.5-flash') 
    
    # 2. Empaquetar las noticias para la IA
    texto_noticias = "NOTICIAS RECIENTES DEL MERCADO:\n"
    for n in noticias_lista[:10]:  # Limitamos a las 10 noticias más relevantes
        titulo = n.get("title", n.get("headline", "Sin título"))
        texto_noticias += f"- Ticker Relacionado: {n.get('origen_ticker', 'Macro')}\n"
        texto_noticias += f"  Titular: {titulo}\n\n"
        
    texto_noticias += f"UNIVERSO DE ACTIVOS DISPONIBLES: {', '.join(tickers_universo)}\n"
    texto_noticias += "Genera las vistas de Black-Litterman en formato JSON basándote ÚNICAMENTE en la información anterior."

    # 3. Llamada estocástica al LLM (Forzando salida JSON)
    try:
        response = model.generate_content(
            f"{PROMPT_SISTEMA_QUANT}\n\n{texto_noticias}",
            generation_config=genai.types.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.2 # Temperatura baja para que sea analítico y no creativo
            )
        )
        
        # 4. Parsear el JSON puro a diccionarios de Python
        vistas_generadas = json.loads(response.text)
        
        # Limpieza de seguridad: filtrar activos que no estén en nuestro universo
        vistas_filtradas = []
        for v in vistas_generadas:
            if v.get("activo_1") in tickers_universo:
                vistas_filtradas.append(v)
                
        return True, vistas_filtradas
        
    except Exception as e:
        return False, f"Error en el Motor Heurístico: {e}"

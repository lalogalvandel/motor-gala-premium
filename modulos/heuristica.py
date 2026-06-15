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
    Toma un arreglo de noticias, las sintetiza y llama al LLM usando 
    Auto-Descubrimiento de modelos para evitar errores 404 por versiones de SDK.
    """
    import google.generativeai as genai
    import json
    import re
    
    genai.configure(api_key=api_key)
    
    texto_noticias = "NOTICIAS RECIENTES DEL MERCADO:\n"
    for n in noticias_lista[:10]:
        titulo = n.get("title", n.get("headline", "Sin título"))
        texto_noticias += f"- Ticker Relacionado: {n.get('origen_ticker', 'Macro')}\n"
        texto_noticias += f"  Titular: {titulo}\n\n"
        
    texto_noticias += f"UNIVERSO DE ACTIVOS DISPONIBLES: {', '.join(tickers_universo)}\n"
    texto_noticias += "Genera las vistas de Black-Litterman en formato JSON basándote ÚNICAMENTE en la información anterior."

    # ── 1. AUTO-DESCUBRIMIENTO DE MODELOS DISPONIBLES ──
    modelo_elegido = 'gemini-pro' # Fallback universal de la primera versión
    try:
        # Le preguntamos a Google qué modelos están activos para esta llave
        modelos_disponibles = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Nuestra lista de deseos, del mejor al más básico
        preferencias = ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-1.0-pro', 'models/gemini-pro']
        
        for pref in preferencias:
            if pref in modelos_disponibles:
                modelo_elegido = pref.replace('models/', '')
                break
        else:
            if modelos_disponibles:
                modelo_elegido = modelos_disponibles[0].replace('models/', '')
    except Exception:
        pass # Si falla la consulta, seguimos con gemini-pro por defecto

    # ── 2. EJECUCIÓN DEL MODELO ──
    try:
        model = genai.GenerativeModel(modelo_elegido)
        
        # Pasamos solo la temperatura para no romper SDKs antiguos con parámetros nuevos
        response = model.generate_content(
            f"{PROMPT_SISTEMA_QUANT}\n\n{texto_noticias}",
            generation_config=genai.types.GenerationConfig(temperature=0.2)
        )
        
        # ── 3. LIMPIEZA DEL JSON (Extracción Regex) ──
        texto_respuesta = response.text
        # Si la IA envuelve la respuesta en bloques de código markdown, se los quitamos
        texto_respuesta = re.sub(r'^```json\n?', '', texto_respuesta, flags=re.MULTILINE)
        texto_respuesta = re.sub(r'^```\n?', '', texto_respuesta, flags=re.MULTILINE)
        texto_respuesta = texto_respuesta.strip()
        
        # 4. Parsear a diccionario de Python
        vistas_generadas = json.loads(texto_respuesta)
        
        # ── 4. FILTRO DE SEGURIDAD (Emparejamiento Inteligente de Tickers) ──
        vistas_filtradas = []
        for v in vistas_generadas:
            activo_ia = str(v.get("activo_1", "")).upper().strip()
            
            # Buscamos si el ticker de la IA está dentro del nuestro (ej. AAPL en AAPL.MX) o viceversa
            coincidencia = next((t for t in tickers_universo if activo_ia in t.upper() or t.upper() in activo_ia), None)
            
            if coincidencia:
                v["activo_1"] = coincidencia # Forzamos el ticker exacto que Markowitz espera
                
                # Si es una vista relativa, también corregimos el segundo activo
                if v.get("tipo") == "relativa" and "activo_2" in v:
                    act2_ia = str(v.get("activo_2", "")).upper().strip()
                    coincidencia2 = next((t for t in tickers_universo if act2_ia in t.upper() or t.upper() in act2_ia), None)
                    if coincidencia2:
                        v["activo_2"] = coincidencia2
                    else:
                        continue # Si no encontramos el par, descartamos esta vista
                        
                vistas_filtradas.append(v)
                
        return True, vistas_filtradas
        
    except json.JSONDecodeError:
        return False, f"La IA no devolvió un JSON válido usando el modelo {modelo_elegido}. Respuesta cruda: {texto_respuesta[:100]}..."
    except Exception as e:
        return False, f"Error al ejecutar el modelo {modelo_elegido}: {e}"

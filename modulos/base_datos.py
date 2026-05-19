import os
from supabase import create_client, Client
from dotenv import load_dotenv

# 1. Cargamos tus llaves secretas desde el archivo .env
load_dotenv('apiky.env')

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

# 2. Inicializamos el cliente de conexión
supabase: Client = create_client(url, key)

def registrar_usuario_prueba():
    """Inyecta un cliente dummy para probar la tubería hacia la nube."""
    try:
        # Hacemos un INSERT a la tabla de Usuarios (Nota: Supabase usa minúsculas por defecto para las tablas en su API)
        respuesta = supabase.table('usuarios').insert({
            "tipo_cliente": "Fisica",
            "nombre_razon_social": "Cliente Alpha GaLa",
            "email": "alpha@motor-gala.com",
            "password_hash": "hash_criptografico_falso_123"
        }).execute()
        
        print("✅ ¡Conexión exitosa! Usuario inyectado en la base de datos.")
        return respuesta.data[0]
    
    except Exception as e:
        print(f"🚨 Error en la conexión: {e}")
        return None

# Si corres este archivo directamente, ejecuta la prueba
if __name__ == "__main__":
    registrar_usuario_prueba()
    
def guardar_portafolio_optimo(id_usuario, retorno_cagr, volatilidad, pesos_activos):
    """
    Guarda el portafolio generado por Markowitz en la base de datos de Supabase.
    pesos_activos debe ser un diccionario, ej: {'GLD': 0.4193, 'MO': 0.2046}
    """
    try:
        # 1. Creamos el registro del Portafolio Maestro
        data_portafolio = {
            "id_usuario": id_usuario,
            "rendimiento_esperado_cagr": round(retorno_cagr, 4),
            "volatilidad_esperada": round(volatilidad, 4),
            "fecha_proximo_rebalanceo": "2026-11-15" # Seis meses a futuro (puedes hacerlo dinámico luego)
        }
        
        resp_portafolio = supabase.table('portafolios_asignados').insert(data_portafolio).execute()
        id_portafolio_nuevo = resp_portafolio.data[0]['id_portafolio']
        
        # 2. Preparamos los activos individuales para la tabla de composición
        composicion = []
        for ticker, peso in pesos_activos.items():
            if peso > 0.001: # Solo guardamos si el peso es mayor al 0.1% para evitar basura
                composicion.append({
                    "id_portafolio": id_portafolio_nuevo,
                    "ticker": ticker,
                    "peso_asignado": round(peso, 4),
                    "precio_compra": 0.00 # Aquí luego podemos jalar el precio de cierre real
                })
        
        # 3. Hacemos una inserción masiva (Bulk Insert) de todos los activos de golpe
        supabase.table('composicion_activos').insert(composicion).execute()
        
        print(f"✅ Portafolio guardado con éxito. ID: {id_portafolio_nuevo}")
        return True

    except Exception as e:
        print(f"🚨 Error al guardar el portafolio: {e}")
        return False
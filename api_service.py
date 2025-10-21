"""
Servicio web FastAPI para consultar predicciones de calidad del aire.
Proporciona endpoints REST para acceder a datos de la base de datos PostgreSQL.

Autor: Sistema de Pronóstico de Calidad del Aire
Versión: 1.0
"""

import os
import logging
import netrc
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import asyncpg
from asyncpg import Pool

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Modelos Pydantic para validación de datos
class PronosticoItem(BaseModel):
    """Modelo para un elemento de pronóstico individual"""
    dia: str = Field(..., description="Fecha del pronóstico en formato YYYY-MM-DD")
    valor: float = Field(..., description="Valor de la predicción")
    fuente: str = Field(..., description="Fuente de la predicción")
    id_est: str = Field(..., description="ID de la estación con valor máximo")
    hora: str = Field(..., description="Hora del pronóstico (HH:MM)")

class PronosticoResponse(BaseModel):
    """Modelo para la respuesta del endpoint de pronósticos"""
    ciudad: str = Field(..., description="Ciudad de la predicción")
    fecha_pron: str = Field(..., description="Fecha de pronóstico en formato YYYY-MM-DD")
    modelo_id: str = Field(..., description="ID del modelo utilizado")
    unidades: str = Field(..., description="Unidades de medida")
    pronos: List[PronosticoItem] = Field(..., description="Lista de pronósticos")

class ErrorResponse(BaseModel):
    """Modelo para respuestas de error"""
    message: str = Field(..., description="Mensaje de error")

# Función para obtener credenciales AMATE-SOLOREAD (igual que postgres_data_service.py)
def get_db_config():
    """Obtiene configuración de base de datos usando credenciales AMATE-SOLOREAD"""
    try:
        # Obtener credenciales desde .netrc (igual que el sistema principal)
        secrets = netrc.netrc()
        login, account, password = secrets.hosts['AMATE-SOLOREAD']
        
        # Configuración de conexión (igual que postgres_data_service.py)
        host = account or os.getenv('DB_HOST', '132.248.8.152')
        database = os.getenv('DB_NAME', 'contingencia')
        
        return {
            'host': host,
            'port': int(os.getenv('DB_PORT', '5432')),
            'user': login,
            'password': password,
            'database': database
        }
    except Exception as e:
        logger.warning(f"⚠️ No se pudieron obtener credenciales AMATE-SOLOREAD: {e}")
        # Fallback a variables de entorno
        return {
            'host': os.getenv('DB_HOST', '132.248.8.152'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'contingencia')
        }

# Configuración de base de datos usando credenciales AMATE-SOLOREAD
DB_CONFIG = get_db_config()

# Configuración del servidor API
API_CONFIG = {
    'host': os.getenv('API_HOST', '0.0.0.0'),
    'port': int(os.getenv('API_PORT', '8888')),
    'debug': os.getenv('API_DEBUG', 'false').lower() == 'true'
}

# Pool de conexiones global
db_pool: Optional[Pool] = None

class ForecastProcessor:
    """Procesa datos de pronósticos desde la base de datos y genera respuestas JSON"""
    
    def __init__(self, contaminante: str, ciudad: str, fecha_datetime: datetime):
        """
        Inicializa el procesador de pronósticos.
        
        Args:
            contaminante: Tipo de contaminante (ozono, pm10, etc.)
            ciudad: Ciudad o estación (CDMX, UIZ, etc.)
            fecha_datetime: Fecha base del pronóstico
        """
        self.contaminante = contaminante.lower()
        self.ciudad = ciudad.upper()
        self.fecha_base = fecha_datetime
        
    def get_table_name(self) -> str:
        """Mapea el contaminante a su tabla correspondiente"""
        table_mapping = {
            'ozono': 'forecast_otres',
            'co': 'forecast_co',
            'no': 'forecast_no',
            'nodos': 'forecast_nodos',
            'nox': 'forecast_nox',
            'pmco': 'forecast_pmco',
            'pm10': 'forecast_pmdiez',
            'pm25': 'forecast_pmdoscinco',
            'sodos': 'forecast_sodos'
        }
        return table_mapping.get(self.contaminante, 'forecast_otres')
    
    def get_unidades(self) -> str:
        """Obtiene las unidades según el contaminante"""
        unidades_map = {
            'ozono': 'ppb',
            'co': 'ppm',
            'no': 'ppb',
            'nodos': 'ppb',
            'nox': 'ppb',
            'pmco': 'μg/m³',
            'pm10': 'μg/m³',
            'pm25': 'μg/m³',
            'sodos': 'ppb'
        }
        return unidades_map.get(self.contaminante, 'ppb')
    
    async def fetch_raw_data(self, pool: Pool) -> list:
        """
        Ejecuta la consulta SQL y obtiene los datos crudos de la base de datos.
        
        Args:
            pool: Pool de conexiones de asyncpg
            
        Returns:
            Lista de registros de la base de datos
        """
        table_name = self.get_table_name()
        
        # Construir query según tabla y ciudad
        if table_name == 'forecast_otres':
            if self.ciudad == 'CDMX':
                # Para CDMX: obtener todas las estaciones
                query = """
                SELECT 
                    fecha,
                    id_est as estacion,
                    hour_p01, hour_p02, hour_p03, hour_p04, hour_p05, hour_p06,
                    hour_p07, hour_p08, hour_p09, hour_p10, hour_p11, hour_p12,
                    hour_p13, hour_p14, hour_p15, hour_p16, hour_p17, hour_p18,
                    hour_p19, hour_p20, hour_p21, hour_p22, hour_p23, hour_p24
                FROM forecast_otres 
                WHERE DATE(fecha) = $1 
                AND id_tipo_pronostico = 7
                ORDER BY fecha ASC
                """
                params = [self.fecha_base]
            else:
                # Para estación específica
                query = """
                SELECT 
                    fecha,
                    id_est as estacion,
                    hour_p01, hour_p02, hour_p03, hour_p04, hour_p05, hour_p06,
                    hour_p07, hour_p08, hour_p09, hour_p10, hour_p11, hour_p12,
                    hour_p13, hour_p14, hour_p15, hour_p16, hour_p17, hour_p18,
                    hour_p19, hour_p20, hour_p21, hour_p22, hour_p23, hour_p24
                FROM forecast_otres 
                WHERE DATE(fecha) = $1 
                AND id_tipo_pronostico = 7
                AND id_est = $2
                ORDER BY fecha ASC
                """
                params = [self.fecha_base, self.ciudad]
        else:
            # Tablas de estadísticas (co, pm10, etc.)
            query = """
            SELECT 
                fecha,
                avg_hour_p01, avg_hour_p02, avg_hour_p03, avg_hour_p04, avg_hour_p05, avg_hour_p06,
                avg_hour_p07, avg_hour_p08, avg_hour_p09, avg_hour_p10, avg_hour_p11, avg_hour_p12,
                avg_hour_p13, avg_hour_p14, avg_hour_p15, avg_hour_p16, avg_hour_p17, avg_hour_p18,
                avg_hour_p19, avg_hour_p20, avg_hour_p21, avg_hour_p22, avg_hour_p23, avg_hour_p24
            FROM {} 
            WHERE DATE(fecha) = $1
            ORDER BY fecha ASC
            """.format(table_name)
            params = [self.fecha_base]
        
        # Ejecutar consulta
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        return rows
    
    def process_hourly_forecasts(self, rows: list) -> Dict[str, Dict[str, Any]]:
        """
        Procesa los pronósticos horarios y calcula el máximo por día.
        
        Args:
            rows: Registros de la base de datos
            
        Returns:
            Diccionario con {fecha_str: {'valor': max, 'id_est': estacion, 'hora': hora}}
        """
        if not rows:
            return {}
        
        # Diccionario para almacenar todos los valores por día con metadata
        valores_por_dia = {}
        
        # Determinar si es tabla de ozono (hour_pXX) o estadísticas (avg_hour_pXX)
        first_row = rows[0]
        is_ozono_table = 'hour_p01' in first_row
        prefix = 'hour_p' if is_ozono_table else 'avg_hour_p'
        
        # Procesar cada fila (cada fila es una estación o registro)
        for row in rows:
            fecha_base_row = row['fecha']
            estacion = row.get('estacion', 'CDMX')  # Obtener estación o usar CDMX por defecto
            
            # Procesar cada hora (p01 a p24)
            for hour_num in range(1, 25):
                hour_col = f'{prefix}{hour_num:02d}'
                
                if hour_col in row and row[hour_col] is not None:
                    valor = float(row[hour_col])
                    
                    # Calcular la fecha y hora real del pronóstico
                    # hour_p01 = fecha_base + 1 hora, hour_p02 = fecha_base + 2 horas, etc.
                    if isinstance(fecha_base_row, datetime):
                        fecha_hora_pronostico = fecha_base_row + timedelta(hours=hour_num)
                    else:
                        fecha_base_dt = datetime.strptime(str(fecha_base_row), '%Y-%m-%d %H:%M:%S')
                        fecha_hora_pronostico = fecha_base_dt + timedelta(hours=hour_num)
                    
                    # Extraer día y hora
                    dia_str = fecha_hora_pronostico.strftime('%Y-%m-%d')
                    hora_str = fecha_hora_pronostico.strftime('%H:%M')
                    
                    # Guardar el valor con metadata para este día
                    if dia_str not in valores_por_dia:
                        valores_por_dia[dia_str] = []
                    
                    valores_por_dia[dia_str].append({
                        'valor': valor,
                        'id_est': estacion,
                        'hora': hora_str
                    })
        
        # Calcular el máximo por cada día y guardar la metadata del máximo
        max_por_dia = {}
        for dia, registros in valores_por_dia.items():
            # Encontrar el registro con el valor máximo
            registro_max = max(registros, key=lambda x: x['valor'])
            max_por_dia[dia] = registro_max
        
        # Ordenar por fecha
        max_por_dia_ordenado = dict(sorted(max_por_dia.items()))
        
        return max_por_dia_ordenado
    
    def build_response(self, daily_max: Dict[str, Dict[str, Any]]) -> PronosticoResponse:
        """
        Construye la respuesta JSON final.
        
        Args:
            daily_max: Diccionario con valores máximos por día y metadata
            
        Returns:
            PronosticoResponse con el formato requerido
        """
        # Construir lista de pronósticos con toda la metadata
        pronosticos = [
            PronosticoItem(
                dia=dia_str,
                valor=round(registro['valor'], 2),  # Redondear a 2 decimales
                fuente="pronostico",  # Default por ahora
                id_est=registro['id_est'],
                hora=registro['hora']
            )
            for dia_str, registro in daily_max.items()
        ]
        
        # Construir respuesta
        response = PronosticoResponse(
            ciudad=self.ciudad,
            fecha_pron=self.fecha_base.strftime('%Y-%m-%d'),
            modelo_id="7",  # id_tipo_pronostico
            unidades=self.get_unidades(),
            pronos=pronosticos
        )
        
        return response

async def generate_forecast_json(contaminante: str, ciudad: str, fecha_datetime: datetime) -> PronosticoResponse:
    """
    Genera la respuesta JSON completa para pronósticos de contaminantes.
    
    Args:
        contaminante: Tipo de contaminante (ej: ozono, pm10, co, etc.)
        ciudad: Ciudad de la predicción (ej: CDMX, UIZ, etc.)
        fecha_datetime: Fecha de pronóstico como objeto datetime
    
    Returns:
        PronosticoResponse: Respuesta JSON formateada
    """
    # Crear procesador de pronósticos
    processor = ForecastProcessor(contaminante, ciudad, fecha_datetime)
    
    # Obtener datos crudos de la base de datos
    rows = await processor.fetch_raw_data(db_pool)
    
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron datos"
        )
    
    # Procesar pronósticos horarios y calcular máximos por día
    daily_max = processor.process_hourly_forecasts(rows)
    
    # Construir respuesta JSON
    response = processor.build_response(daily_max)
    
    return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    global db_pool
    
    # Inicialización
    logger.info("🚀 Iniciando servicio de pronósticos de calidad del aire")
    
    try:
        # Crear pool de conexiones
        db_pool = await asyncpg.create_pool(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            min_size=1,
            max_size=10
        )
        logger.info("✅ Pool de conexiones PostgreSQL creado exitosamente")
        
        # Verificar conexión
        async with db_pool.acquire() as conn:
            await conn.fetchval('SELECT 1')
        logger.info("✅ Conexión a base de datos verificada")
        
    except Exception as e:
        logger.error(f"❌ Error al conectar con la base de datos: {e}")
        raise
    
    yield
    
    # Limpieza
    if db_pool:
        await db_pool.close()
        logger.info("🔌 Pool de conexiones cerrado")

# Crear aplicación FastAPI
app = FastAPI(
    title="Servicio de Pronósticos de Calidad del Aire",
    description="API REST para consultar predicciones de calidad del aire desde PostgreSQL",
    version="1.0.0",
    lifespan=lifespan
)

async def get_db_connection():
    """Obtener conexión de la base de datos"""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Pool de base de datos no disponible")
    return db_pool.acquire()

@app.get("/", response_model=Dict[str, Any])
async def root():
    """Endpoint raíz con información del servicio"""
    return {
        "service": "Pronósticos de Calidad del Aire API",
        "version": "1.0.0",
        "status": "active",
        "database": "PostgreSQL (AMATE-SOLOREAD)",
        "endpoints": {
            "ai_vi_transformer01": "/ai_vi_transformer01/{contaminante}/{ciudad}/{fecha_pron}",
            "pronosticos_ia": "/get_ia_resume/{ciudad}/{fecha_pron}",
            "health": "/health",
            "docs": "/docs"
        },
        "contaminantes_disponibles": {
            "ozono": "Ozono (ai_vi_transformer01) - forecast_otres",
            "co": "Monóxido de Carbono (ai_vi_transformer01) - forecast_co",
            "no": "Óxido Nítrico (ai_vi_transformer01) - forecast_no",
            "nodos": "Dióxido de Nitrógeno (ai_vi_transformer01) - forecast_nodos",
            "nox": "Óxidos de Nitrógeno (ai_vi_transformer01) - forecast_nox",
            "pmco": "PMco (ai_vi_transformer01) - forecast_pmco",
            "pm10": "PM10 (ai_vi_transformer01) - forecast_pmdiez",
            "pm25": "PM2.5 (ai_vi_transformer01) - forecast_pmdoscinco",
            "sodos": "Dióxido de Azufre (ai_vi_transformer01) - forecast_sodos"
        },
        "ciudades_disponibles": {
            "CDMX": "Ciudad de México (máximo de todas las estaciones)",
            "UIZ": "Estación UIZ", "AJU": "Estación AJU", "ATI": "Estación ATI", 
            "CUA": "Estación CUA", "SFE": "Estación SFE", "SAG": "Estación SAG", 
            "CUT": "Estación CUT", "PED": "Estación PED", "TAH": "Estación TAH", 
            "GAM": "Estación GAM", "IZT": "Estación IZT", "CCA": "Estación CCA", 
            "HGM": "Estación HGM", "LPR": "Estación LPR", "MGH": "Estación MGH", 
            "CAM": "Estación CAM", "FAC": "Estación FAC", "TLA": "Estación TLA", 
            "MER": "Estación MER", "XAL": "Estación XAL", "LLA": "Estación LLA", 
            "TLI": "Estación TLI", "UAX": "Estación UAX", "BJU": "Estación BJU", 
            "MPA": "Estación MPA", "MON": "Estación MON", "NEZ": "Estación NEZ", 
            "INN": "Estación INN", "AJM": "Estación AJM", "VIF": "Estación VIF"
        }
    }

@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """Endpoint de verificación de salud del servicio"""
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval('SELECT 1')
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Servicio no disponible")

@app.get(
    "/ai_vi_transformer01/{contaminante}/{ciudad}/{fecha_pron}",
    response_model=PronosticoResponse,
    responses={
        404: {"model": ErrorResponse, "description": "No se encontraron datos"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def get_ai_vi_transformer01(
    contaminante: str = Path(..., description="Contaminante (ej: ozono, pm10, co, etc.)"),
    ciudad: str = Path(..., description="Ciudad de la predicción"),
    fecha_pron: str = Path(..., description="Fecha de pronóstico en formato YYYY-MM-DD")
):
    """
    Obtiene resumen de pronósticos del modelo AI VI Transformer01 para una ciudad y fecha específica.
    
    Args:
        contaminante: Tipo de contaminante (ej: ozono, pm10, co, etc.)
        ciudad: Ciudad de la predicción
        fecha_pron: Fecha de pronóstico en formato YYYY-MM-DD
    
    Returns:
        PronosticoResponse: Datos de pronóstico agrupados por ciudad y fecha
    """
    try:
        # Validar formato de fecha
        try:
            datetime.strptime(fecha_pron, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Formato de fecha inválido. Use YYYY-MM-DD"
            )
        
        # Convertir fecha string a datetime para PostgreSQL
        fecha_datetime = datetime.strptime(fecha_pron, '%Y-%m-%d')
        
        # Usar la función centralizada para generar el JSON
        response = await generate_forecast_json(contaminante, ciudad, fecha_datetime)
        
        logger.info(f"✅ Consulta exitosa: {ciudad}, {fecha_pron}, {len(response.pronos)} registros")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en consulta: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@app.get(
    "/get_ia_resume/{ciudad}/{fecha_pron}",
    response_model=PronosticoResponse,
    responses={
        404: {"model": ErrorResponse, "description": "No se encontraron datos"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def get_ia_resume(
    ciudad: str = Path(..., description="Ciudad de la predicción"),
    fecha_pron: str = Path(..., description="Fecha de pronóstico en formato YYYY-MM-DD")
):
    """
    Obtiene resumen de pronósticos de IA para una ciudad y fecha específica.
    Endpoint alternativo que agrupa por ciudad y fecha sin especificar componente.
    """
    try:
        # Validar formato de fecha
        try:
            datetime.strptime(fecha_pron, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Formato de fecha inválido. Use YYYY-MM-DD"
            )
        
        # Construir consulta SQL agrupada
        query = """
        SELECT 
            ciudad,
            fecha_pron,
            modelo_id,
            unidades,
            completo,
            dia,
            valor,
            fuente
        FROM predicciones_ia 
        WHERE ciudad = $1 
        AND DATE(fecha_pron) = $2
        ORDER BY dia ASC
        """
        
        # Ejecutar consulta
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(query, ciudad, fecha_pron)
        
        if not rows:
            return JSONResponse(
                status_code=404,
                content={"message": "no data found"}
            )
        
        # Procesar resultados
        first_row = rows[0]
        pronosticos = []
        
        for row in rows:
            pronosticos.append(PronosticoItem(
                dia=row['dia'].strftime('%Y-%m-%d') if isinstance(row['dia'], datetime) else str(row['dia']),
                valor=float(row['valor']),
                fuente=row['fuente'] or 'observado'
            ))
        
        # Formatear fecha de pronóstico
        fecha_pron_iso = first_row['fecha_pron']
        if isinstance(fecha_pron_iso, datetime):
            fecha_pron_iso = fecha_pron_iso.isoformat()
        else:
            fecha_pron_iso = str(fecha_pron_iso)
        
        # Construir respuesta
        response = PronosticoResponse(
            ciudad=first_row['ciudad'],
            fecha_pron=fecha_pron_iso,
            modelo=first_row['modelo_id'] or 'IA_Model',
            unidades=first_row['unidades'] or 'ppb',
            pronos=pronosticos
        )
        
        logger.info(f"✅ Consulta IA exitosa: {ciudad}, {fecha_pron}, {len(pronosticos)} registros")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en consulta IA: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

@app.get(
    "/get_wrf_resume/{contaminante}/{ciudad}/{fecha_pron}",
    response_model=PronosticoResponse,
    responses={
        404: {"model": ErrorResponse, "description": "No se encontraron datos"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def get_wrf_resume_legacy(
    contaminante: str = Path(..., description="Contaminante (ej: ozono, pm10, co, etc.)"),
    ciudad: str = Path(..., description="Ciudad de la predicción"),
    fecha_pron: str = Path(..., description="Fecha de pronóstico en formato YYYY-MM-DD")
):
    """
    Endpoint legacy para compatibilidad. Redirige al endpoint principal.
    """
    # Redirigir al endpoint principal
    return await get_ai_vi_transformer01(contaminante, ciudad, fecha_pron)

if __name__ == "__main__":
    # Configuración para desarrollo usando la misma configuración que la app Dash
    uvicorn.run(
        "api_service:app",
        host=API_CONFIG['host'],
        port=API_CONFIG['port'],
        reload=API_CONFIG['debug'],
        log_level="info"
    )

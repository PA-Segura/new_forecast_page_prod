"""
Servicio web FastAPI para consultar predicciones de calidad del aire.
Proporciona endpoints REST para acceder a datos de la base de datos PostgreSQL.

Versión 4: Incluye endpoint histórico para series de tiempo
- Mantiene toda la funcionalidad de v3 (consistencia diaria)
- Agrega endpoint histórico: /{component}/{location_id}/{horizon_days}/{startdate}/{enddate}
- Retorna máximos diarios de pronósticos de 7 AM para gráficos de series de tiempo

Autor: Sistema de Pronóstico de Calidad del Aire
Versión: 4.0
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Activar debug si se necesita (descomentar la siguiente línea para debug detallado)
# logger.setLevel(logging.DEBUG)

# ============================================================================
# MODELOS PYDANTIC PARA VALIDACIÓN DE DATOS
# ============================================================================

# Modelos para endpoints v3 (existentes)
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
    modelo: str = Field(..., description="Nombre del modelo utilizado")
    unidades: str = Field(..., description="Unidades de medida")
    pronos: List[PronosticoItem] = Field(..., description="Lista de pronósticos")

# Nuevos modelos para endpoint histórico (v4)
class HistoricalForecastItem(BaseModel):
    """Modelo para un elemento de pronóstico histórico"""
    model_name: str = Field(..., description="Nombre del modelo de pronóstico")
    forecast_date: str = Field(..., description="Fecha del pronóstico en formato YYYY-MM-DD")
    predicted_value: str = Field(..., description="Valor predicho (máximo del día)")
    forecast_generation_date: str = Field(..., description="Fecha de generación del pronóstico en formato YYYY-MM-DD")
    horizon: int = Field(..., description="Horizonte del pronóstico en días (0 = mismo día)")

class HistoricalForecastResponse(BaseModel):
    """Modelo para la respuesta del endpoint histórico"""
    success: bool = Field(..., description="Indicador de éxito de la consulta")
    data: List[HistoricalForecastItem] = Field(..., description="Lista de pronósticos históricos")
    count: int = Field(..., description="Número de registros retornados")
    params: Dict[str, Any] = Field(..., description="Parámetros de la consulta")

class ErrorResponse(BaseModel):
    """Modelo para respuestas de error"""
    message: str = Field(..., description="Mensaje de error")

# ============================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================================================

def get_db_config():
    """Obtiene configuración de base de datos usando credenciales AMATE-SOLOREAD (igual que config.py)"""
    def get_db_credentials():
        """Obtiene credenciales de BD desde .netrc"""
        try:
            n = netrc.netrc()
            login, account, password = n.authenticators('AMATE-SOLOREAD')
            return login, password, account
        except (FileNotFoundError, netrc.NetrcParseError):
            # Fallback a variables de entorno
            return os.getenv('DB_USER'), os.getenv('DB_PASSWORD'), os.getenv('DB_HOST')
    
    try:
        # Obtener credenciales (igual que config.py)
        login, password, account = get_db_credentials() 
        
        return {
            'host': account or os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'user': login or os.getenv('DB_USER', 'postgres'),
            'password': password or os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'contingencia')
        }
    except Exception as e:
        logger.warning(f"⚠️ No se pudieron obtener credenciales AMATE-SOLOREAD: {e}")
        # Fallback a variables de entorno
        return {
            'host': os.getenv('DB_HOST', 'localhost'),
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
    # 'port': int(os.getenv('API_PORT', '6006')),  # Puerto 6006 para debugging
    'port': int(os.getenv('API_PORT', '8888')),  # Puerto 8888 para producción (descomentar cuando esté listo)
    'debug': os.getenv('API_DEBUG', 'false').lower() == 'true'
}

# Pool de conexiones global
db_pool: Optional[Pool] = None

# Mapeo de componentes a modelos
COMPONENT_MODEL_MAP = {
    'comp6': {
        'id_tipo_pronostico': 7,
        'nombre': 'C6: Aprendizaje automático',
        'tabla': 'forecast_otres'
    },
    'comp2': {
        'id_tipo_pronostico': 2,
        'nombre': 'C2: Modelos multivariados y de valores extremos',
        'tabla': 'forecast_otres'
    }
}

# ============================================================================
# CLASE FORECASTPROCESSOR (v3 - sin cambios)
# ============================================================================

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
    
    async def fetch_forecast_by_hour(self, pool: Pool, hora_generacion: int) -> list:
        """
        Obtiene el pronóstico generado a una hora específica.
        
        Args:
            pool: Pool de conexiones de asyncpg
            hora_generacion: Hora de generación del pronóstico (ej: 7 para 7 AM, 16 para 4 PM)
            
        Returns:
            Lista de registros de la base de datos
        """
        table_name = self.get_table_name()
        
        logger.info(f"🔍 Buscando pronóstico generado a las {hora_generacion}:00")
        
        if table_name == 'forecast_otres':
            if self.ciudad == 'CDMX':
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
                AND EXTRACT(HOUR FROM fecha) = $2
                AND id_tipo_pronostico = 7
                ORDER BY fecha ASC
                """
                params = [self.fecha_base, hora_generacion]
            else:
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
                AND EXTRACT(HOUR FROM fecha) = $2
                AND id_tipo_pronostico = 7
                AND id_est = $3
                ORDER BY fecha ASC
                """
                params = [self.fecha_base, hora_generacion, self.ciudad]
        else:
            query = """
            SELECT 
                fecha,
                avg_hour_p01, avg_hour_p02, avg_hour_p03, avg_hour_p04, avg_hour_p05, avg_hour_p06,
                avg_hour_p07, avg_hour_p08, avg_hour_p09, avg_hour_p10, avg_hour_p11, avg_hour_p12,
                avg_hour_p13, avg_hour_p14, avg_hour_p15, avg_hour_p16, avg_hour_p17, avg_hour_p18,
                avg_hour_p19, avg_hour_p20, avg_hour_p21, avg_hour_p22, avg_hour_p23, avg_hour_p24
            FROM {} 
            WHERE DATE(fecha) = $1
            AND EXTRACT(HOUR FROM fecha) = $2
            ORDER BY fecha ASC
            """.format(table_name)
            params = [self.fecha_base, hora_generacion]
        
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
        except Exception as e:
            logger.error(f"❌ Error ejecutando query: {e}")
            raise
        
        logger.info(f"✅ Query ejecutado: {len(rows)} registros obtenidos")
        
        return rows
    
    def process_hourly_forecasts(self, rows: list) -> Dict[str, Dict[str, Any]]:
        """
        Procesa los pronósticos horarios y calcula el máximo por día.
        
        Args:
            rows: Registros de la base de datos (ya filtrados por hora de generación)
            
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
            estacion = row.get('estacion', 'CDMX')
            
            # Procesar cada hora (p01 a p24)
            for hour_num in range(1, 25):
                hour_col = f'{prefix}{hour_num:02d}'
                
                if hour_col in row and row[hour_col] is not None:
                    valor = float(row[hour_col])
                    
                    # Calcular la fecha y hora real del pronóstico
                    if isinstance(fecha_base_row, datetime):
                        fecha_hora_pronostico = fecha_base_row + timedelta(hours=hour_num)
                    else:
                        fecha_base_dt = datetime.strptime(str(fecha_base_row), '%Y-%m-%d %H:%M:%S')
                        fecha_hora_pronostico = fecha_base_dt + timedelta(hours=hour_num)
                    
                    # Extraer día y hora
                    dia_str = fecha_hora_pronostico.strftime('%Y-%m-%d')
                    hora_str = fecha_hora_pronostico.strftime('%H:%M')
                    hora_int = fecha_hora_pronostico.hour
                    
                    # Guardar el valor con metadata para este día
                    if dia_str not in valores_por_dia:
                        valores_por_dia[dia_str] = []
                    
                    valores_por_dia[dia_str].append({
                        'valor': valor,
                        'id_est': estacion,
                        'hora': hora_str,
                        'hora_int': hora_int
                    })
        
        # Calcular el MÁXIMO de todos los valores por cada día
        max_por_dia = {}
        for dia, registros in valores_por_dia.items():
            if not registros:
                continue
            
            # Encontrar el registro con el valor MÁXIMO
            registro_max = max(registros, key=lambda x: x['valor'])
            registro_max['horas_disponibles'] = [r['hora_int'] for r in registros]
            registro_max['num_horas_evaluadas'] = len(registros)
            
            max_por_dia[dia] = registro_max
        
        # Ordenar por fecha
        return dict(sorted(max_por_dia.items()))
    
    def build_response(self, daily_max: Dict[str, Dict[str, Any]]) -> PronosticoResponse:
        """Construye la respuesta JSON final."""
        daily_max_filtrado = daily_max.copy()
        
        if self.contaminante == 'ozono' and daily_max:
            dia_siguiente = (self.fecha_base + timedelta(days=1)).strftime('%Y-%m-%d')
            dia_corriente = self.fecha_base.strftime('%Y-%m-%d')
            
            tiene_datos_despues_4pm_dia_siguiente = False
            
            if dia_siguiente in daily_max:
                horas_disponibles = daily_max[dia_siguiente].get('horas_disponibles', [])
                tiene_datos_despues_4pm_dia_siguiente = any(hora >= 16 for hora in horas_disponibles)
            
            if tiene_datos_despues_4pm_dia_siguiente:
                daily_max_filtrado = {
                    dia: registro for dia, registro in daily_max.items()
                    if dia == dia_corriente or dia == dia_siguiente
                }
                daily_max_filtrado = dict(sorted(daily_max_filtrado.items()))
            else:
                daily_max_filtrado = {
                    dia: registro for dia, registro in daily_max.items()
                    if dia == dia_corriente
                }
        
        pronosticos = [
            PronosticoItem(
                dia=dia_str,
                valor=round(registro['valor'], 2),
                fuente="pronostico",
                id_est=registro['id_est'],
                hora=registro['hora']
            )
            for dia_str, registro in daily_max_filtrado.items()
        ]
        
        response = PronosticoResponse(
            ciudad=self.ciudad,
            fecha_pron=self.fecha_base.strftime('%Y-%m-%d'),
            modelo_id="7",
            modelo="C6: Aprendizaje automático",
            unidades=self.get_unidades(),
            pronos=pronosticos
        )
        
        return response

# ============================================================================
# CLASE HISTORICALFORECASTPROCESSOR (NUEVA en v4)
# ============================================================================

class HistoricalForecastProcessor:
    """Procesa pronósticos históricos para series de tiempo"""
    
    def __init__(self, component: str, location_id: str, horizon_days: int):
        """
        Inicializa el procesador de pronósticos históricos.
        
        Args:
            component: Componente del modelo (ej: comp6, comp2)
            location_id: ID de la ubicación (ej: CDMX, UIZ)
            horizon_days: Horizonte de pronóstico en días
        """
        self.component = component.lower()
        self.location_id = location_id.upper()
        self.horizon_days = horizon_days
        
        # Obtener configuración del modelo
        if self.component not in COMPONENT_MODEL_MAP:
            raise ValueError(f"Componente no soportado: {component}")
        
        self.model_config = COMPONENT_MODEL_MAP[self.component]
        self.id_tipo_pronostico = self.model_config['id_tipo_pronostico']
        self.model_name = self.model_config['nombre']
        self.table_name = self.model_config['tabla']
    
    async def fetch_historical_data(self, pool: Pool, startdate: str, enddate: str, 
                                   hora_generacion: int = 7) -> list:
        """
        Obtiene datos históricos de pronósticos para un rango de fechas.
        
        Args:
            pool: Pool de conexiones de asyncpg
            startdate: Fecha inicial en formato YYYY-MM-DD
            enddate: Fecha final en formato YYYY-MM-DD
            hora_generacion: Hora de generación del pronóstico (default: 7 AM)
            
        Returns:
            Lista de registros de la base de datos
        """
        logger.info(f"🔍 Obteniendo datos históricos de {startdate} a {enddate}")
        logger.info(f"   Componente: {self.component}, Modelo: {self.model_name}")
        logger.info(f"   Ubicación: {self.location_id}, Hora generación: {hora_generacion}:00")
        
        # Convertir strings de fecha a objetos date para asyncpg
        startdate_obj = datetime.strptime(startdate, '%Y-%m-%d').date()
        enddate_obj = datetime.strptime(enddate, '%Y-%m-%d').date()
        
        # Construir query según si es CDMX (todas las estaciones) o estación específica
        if self.location_id == 'CDMX':
            query = """
            SELECT 
                DATE(fecha) as fecha_gen,
                fecha,
                id_est as estacion,
                hour_p01, hour_p02, hour_p03, hour_p04, hour_p05, hour_p06,
                hour_p07, hour_p08, hour_p09, hour_p10, hour_p11, hour_p12,
                hour_p13, hour_p14, hour_p15, hour_p16, hour_p17, hour_p18,
                hour_p19, hour_p20, hour_p21, hour_p22, hour_p23, hour_p24
            FROM forecast_otres 
            WHERE DATE(fecha) BETWEEN $1 AND $2
            AND EXTRACT(HOUR FROM fecha) = $3
            AND id_tipo_pronostico = $4
            ORDER BY fecha ASC, id_est ASC
            """
            params = [startdate_obj, enddate_obj, hora_generacion, self.id_tipo_pronostico]
        else:
            query = """
            SELECT 
                DATE(fecha) as fecha_gen,
                fecha,
                id_est as estacion,
                hour_p01, hour_p02, hour_p03, hour_p04, hour_p05, hour_p06,
                hour_p07, hour_p08, hour_p09, hour_p10, hour_p11, hour_p12,
                hour_p13, hour_p14, hour_p15, hour_p16, hour_p17, hour_p18,
                hour_p19, hour_p20, hour_p21, hour_p22, hour_p23, hour_p24
            FROM forecast_otres 
            WHERE DATE(fecha) BETWEEN $1 AND $2
            AND EXTRACT(HOUR FROM fecha) = $3
            AND id_tipo_pronostico = $4
            AND id_est = $5
            ORDER BY fecha ASC
            """
            params = [startdate_obj, enddate_obj, hora_generacion, self.id_tipo_pronostico, self.location_id]
        
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(query, *params)
        except Exception as e:
            logger.error(f"❌ Error ejecutando query histórico: {e}")
            raise
        
        logger.info(f"✅ Query histórico ejecutado: {len(rows)} registros obtenidos")
        
        return rows
    
    def calculate_daily_maximums(self, rows: list) -> Dict[str, Dict[str, Any]]:
        """
        Calcula el máximo diario de los pronósticos.
        
        Args:
            rows: Registros de la base de datos
            
        Returns:
            Diccionario con {fecha_gen: {'fecha_gen': str, 'max_valor': float, 'fecha_pron': str}}
        """
        if not rows:
            return {}
        
        # Agrupar por fecha de generación
        datos_por_fecha = {}
        
        for row in rows:
            fecha_gen = str(row['fecha_gen'])  # Fecha de generación del pronóstico
            fecha_base = row['fecha']  # Timestamp completo con hora
            estacion = row.get('estacion', 'CDMX')
            
            if fecha_gen not in datos_por_fecha:
                datos_por_fecha[fecha_gen] = []
            
            # Procesar las 24 horas de pronóstico
            for hour_num in range(1, 25):
                hour_col = f'hour_p{hour_num:02d}'
                
                if hour_col in row and row[hour_col] is not None:
                    valor = float(row[hour_col])
                    
                    # Calcular la fecha/hora del pronóstico
                    if isinstance(fecha_base, datetime):
                        fecha_hora_pron = fecha_base + timedelta(hours=hour_num)
                    else:
                        fecha_base_dt = datetime.strptime(str(fecha_base), '%Y-%m-%d %H:%M:%S')
                        fecha_hora_pron = fecha_base_dt + timedelta(hours=hour_num)
                    
                    datos_por_fecha[fecha_gen].append({
                        'valor': valor,
                        'estacion': estacion,
                        'fecha_pron': fecha_hora_pron.strftime('%Y-%m-%d'),
                        'hora_pron': fecha_hora_pron.strftime('%H:%M')
                    })
        
        # Calcular máximo por fecha de generación
        maximos_por_fecha = {}
        for fecha_gen, valores in datos_por_fecha.items():
            if not valores:
                continue
            
            # Encontrar el valor máximo
            max_registro = max(valores, key=lambda x: x['valor'])
            
            maximos_por_fecha[fecha_gen] = {
                'fecha_gen': fecha_gen,
                'max_valor': max_registro['valor'],
                'fecha_pron': max_registro['fecha_pron'],
                'estacion': max_registro['estacion'],
                'num_valores': len(valores)
            }
            
            logger.info(f"  📅 {fecha_gen}: Máximo={max_registro['valor']:.2f} "
                       f"(estación {max_registro['estacion']}, {len(valores)} valores)")
        
        return maximos_por_fecha
    
    def build_historical_response(self, daily_maxes: Dict[str, Dict[str, Any]], 
                                 location_id: str, horizon_days: int) -> HistoricalForecastResponse:
        """
        Construye la respuesta JSON para el endpoint histórico.
        
        Args:
            daily_maxes: Diccionario con máximos diarios
            location_id: ID de la ubicación consultada
            horizon_days: Horizonte consultado
            
        Returns:
            HistoricalForecastResponse con el formato requerido
        """
        # Construir lista de items
        data_items = []
        for fecha_gen in sorted(daily_maxes.keys()):
            registro = daily_maxes[fecha_gen]
            
            data_items.append(HistoricalForecastItem(
                model_name=self.model_name,
                forecast_date=registro['fecha_gen'],
                predicted_value=f"{registro['max_valor']:.2f}",
                forecast_generation_date=registro['fecha_gen'],
                horizon=0  # Siempre 0 para pronósticos del mismo día
            ))
        
        # Construir respuesta completa
        response = HistoricalForecastResponse(
            success=True,
            data=data_items,
            count=len(data_items),
            params={
                'location_id': location_id,
                'horizon_days': horizon_days,
                'component': self.component
            }
        )
        
        return response

# ============================================================================
# FUNCIONES AUXILIARES (v3)
# ============================================================================

async def generate_forecast_json(contaminante: str, ciudad: str, fecha_datetime: datetime) -> PronosticoResponse:
    """Genera la respuesta JSON completa para pronósticos de contaminantes."""
    hora_actual = datetime.now().hour
    es_despues_4pm = hora_actual >= 16
    
    logger.info(f"🔍 Obteniendo datos para {contaminante}, {ciudad}, {fecha_datetime}")
    logger.info(f"⏰ Hora actual: {hora_actual:02d}:00, Después de 4 PM: {es_despues_4pm}")
    
    processor = ForecastProcessor(contaminante, ciudad, fecha_datetime)
    
    # PASO 1: SIEMPRE obtener el pronóstico MATUTINO (7 AM)
    logger.info(f"\n📅 PASO 1: Obteniendo pronóstico MATUTINO (7 AM) para día actual")
    rows_matutino = await processor.fetch_forecast_by_hour(db_pool, hora_generacion=7)
    
    if not rows_matutino:
        raise HTTPException(
            status_code=404,
            detail="No se encontró pronóstico matutino (7 AM) en la base de datos"
        )
    
    logger.info(f"✅ Pronóstico matutino: {len(rows_matutino)} registros")
    daily_max_matutino = processor.process_hourly_forecasts(rows_matutino)
    
    # PASO 2: Si es después de las 4 PM, obtener pronóstico VESPERTINO (4 PM)
    daily_max_vespertino = {}
    if es_despues_4pm:
        logger.info(f"\n📅 PASO 2: Obteniendo pronóstico VESPERTINO (4 PM) para día siguiente")
        rows_vespertino = await processor.fetch_forecast_by_hour(db_pool, hora_generacion=16)
        
        if rows_vespertino:
            logger.info(f"✅ Pronóstico vespertino: {len(rows_vespertino)} registros")
            daily_max_vespertino = processor.process_hourly_forecasts(rows_vespertino)
        else:
            logger.warning(f"⚠️ No se encontró pronóstico vespertino (4 PM)")
    else:
        logger.info(f"\n📅 PASO 2: Omitido (solo después de las 4 PM se agrega día siguiente)")
    
    # PASO 3: Combinar resultados
    logger.info(f"\n📅 PASO 3: Combinando resultados")
    
    daily_max_combinado = {}
    
    dia_actual = fecha_datetime.strftime('%Y-%m-%d')
    if dia_actual in daily_max_matutino:
        daily_max_combinado[dia_actual] = daily_max_matutino[dia_actual]
        logger.info(f"   ✅ Día actual ({dia_actual}): {daily_max_matutino[dia_actual]['valor']:.2f} ppb (matutino)")
    
    if es_despues_4pm and daily_max_vespertino:
        dia_siguiente = (fecha_datetime + timedelta(days=1)).strftime('%Y-%m-%d')
        if dia_siguiente in daily_max_vespertino:
            daily_max_combinado[dia_siguiente] = daily_max_vespertino[dia_siguiente]
            logger.info(f"   ✅ Día siguiente ({dia_siguiente}): {daily_max_vespertino[dia_siguiente]['valor']:.2f} ppb (vespertino)")
    
    if not daily_max_combinado:
        raise HTTPException(
            status_code=404,
            detail="No se encontraron datos después de combinar pronósticos"
        )
    
    response = processor.build_response(daily_max_combinado)
    
    return response

# ============================================================================
# CONFIGURACIÓN DE FASTAPI
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida de la aplicación"""
    global db_pool
    
    # Inicialización
    logger.info("🚀 Iniciando servicio de pronósticos de calidad del aire v4 (con endpoint histórico)")
    
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
    title="Servicio de Pronósticos de Calidad del Aire v4",
    description="API REST con endpoint histórico para series de tiempo y funcionalidad v3",
    version="4.0.0",
    lifespan=lifespan
)

# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/", response_model=Dict[str, Any])
async def root():
    """Endpoint raíz con información del servicio"""
    hora_actual = datetime.now().hour
    es_despues_4pm = hora_actual >= 16
    
    return {
        "service": "Pronósticos de Calidad del Aire API v4",
        "version": "4.0.0",
        "status": "active",
        "database": "PostgreSQL (AMATE-SOLOREAD)",
        "hora_actual": f"{hora_actual:02d}:00",
        "novedades_v4": {
            "nuevo_endpoint": "/{component}/{location_id}/{horizon_days}/{startdate}/{enddate}",
            "descripcion": "Endpoint histórico para series de tiempo con máximos diarios de pronósticos",
            "ejemplo": "/comp6/CDMX/0/2026-01-10/2026-01-15"
        },
        "endpoints": {
            "historical": "/{component}/{location_id}/{horizon_days}/{startdate}/{enddate}",
            "ai_vi_transformer01": "/ai_vi_transformer01/{contaminante}/{ciudad}/{fecha_pron}",
            "pronosticos_ia": "/get_ia_resume/{ciudad}/{fecha_pron}",
            "health": "/health",
            "docs": "/docs"
        },
        "componentes_disponibles": {
            "comp6": "C6: Aprendizaje automático (id_tipo_pronostico=7)",
            "comp2": "C2: Modelos multivariados y de valores extremos (id_tipo_pronostico=2)"
        },
        "contaminantes_disponibles": {
            "ozono": "Ozono (ai_vi_transformer01) - forecast_otres",
            "co": "Monóxido de Carbono - forecast_co",
            "pm10": "PM10 - forecast_pmdiez",
            "pm25": "PM2.5 - forecast_pmdoscinco"
        }
    }

@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """Endpoint de verificación de salud del servicio"""
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval('SELECT 1')
        return {"status": "healthy", "database": "connected", "version": "4.0.0"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Servicio no disponible")

# ============================================================================
# NUEVO ENDPOINT HISTÓRICO (v4)
# ============================================================================

@app.get(
    "/{component}/{location_id}/{horizon_days}/{startdate}/{enddate}",
    response_model=HistoricalForecastResponse,
    responses={
        404: {"model": ErrorResponse, "description": "No se encontraron datos"},
        500: {"model": ErrorResponse, "description": "Error interno del servidor"}
    }
)
async def get_historical_forecasts(
    component: str = Path(..., description="Componente del modelo (ej: comp6, comp2)"),
    location_id: str = Path(..., description="ID de la ubicación (ej: CDMX, UIZ)"),
    horizon_days: int = Path(..., description="Horizonte en días (típicamente 0)"),
    startdate: str = Path(..., description="Fecha inicial en formato YYYY-MM-DD"),
    enddate: str = Path(..., description="Fecha final en formato YYYY-MM-DD")
):
    """
    Obtiene serie histórica de pronósticos máximos diarios para un rango de fechas.
    
    Este endpoint retorna el valor máximo de pronóstico para cada día en el rango especificado,
    basado en los pronósticos generados a las 7 AM de cada día.
    
    Args:
        component: Componente del modelo (comp6 para C6: Aprendizaje automático)
        location_id: Ubicación (CDMX para máximo de todas las estaciones, o código de estación)
        horizon_days: Horizonte en días (0 = mismo día)
        startdate: Fecha inicial (YYYY-MM-DD)
        enddate: Fecha final (YYYY-MM-DD)
    
    Returns:
        HistoricalForecastResponse: Serie de pronósticos históricos
        
    Example:
        GET /comp6/CDMX/0/2026-01-10/2026-01-15
        
        Returns:
        {
            "success": true,
            "data": [
                {
                    "model_name": "C6: Aprendizaje automático",
                    "forecast_date": "2026-01-10",
                    "predicted_value": "104.85",
                    "forecast_generation_date": "2026-01-10",
                    "horizon": 0
                },
                ...
            ],
            "count": 6,
            "params": {
                "location_id": "CDMX",
                "horizon_days": 0,
                "component": "comp6"
            }
        }
    """
    try:
        # Validar formato de fechas
        try:
            datetime.strptime(startdate, '%Y-%m-%d')
            datetime.strptime(enddate, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Formato de fecha inválido. Use YYYY-MM-DD"
            )
        
        # Validar que startdate <= enddate
        if startdate > enddate:
            raise HTTPException(
                status_code=400,
                detail="La fecha inicial debe ser menor o igual a la fecha final"
            )
        
        # Validar componente
        if component.lower() not in COMPONENT_MODEL_MAP:
            raise HTTPException(
                status_code=400,
                detail=f"Componente no soportado: {component}. Componentes disponibles: {list(COMPONENT_MODEL_MAP.keys())}"
            )
        
        logger.info(f"🔍 Consulta histórica: {component}/{location_id}/{horizon_days}/{startdate}/{enddate}")
        
        # Crear procesador histórico
        processor = HistoricalForecastProcessor(component, location_id, horizon_days)
        
        # Obtener datos históricos (pronósticos de 7 AM)
        rows = await processor.fetch_historical_data(db_pool, startdate, enddate, hora_generacion=7)
        
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No se encontraron datos para el rango {startdate} - {enddate}"
            )
        
        # Calcular máximos diarios
        daily_maxes = processor.calculate_daily_maximums(rows)
        
        if not daily_maxes:
            raise HTTPException(
                status_code=404,
                detail="No se pudieron calcular máximos diarios"
            )
        
        # Construir respuesta
        response = processor.build_historical_response(daily_maxes, location_id, horizon_days)
        
        logger.info(f"✅ Consulta histórica exitosa: {location_id}, {startdate}-{enddate}, {response.count} registros")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en consulta histórica: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )

# ============================================================================
# ENDPOINTS v3 (SIN CAMBIOS)
# ============================================================================

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
    """Obtiene resumen de pronósticos del modelo AI VI Transformer01."""
    try:
        # Validar formato de fecha
        try:
            datetime.strptime(fecha_pron, '%Y-%m-%d')
        except ValueError:
            raise HTTPException(
                status_code=400, 
                detail="Formato de fecha inválido. Use YYYY-MM-DD"
            )
        
        # Convertir fecha string a datetime
        fecha_datetime = datetime.strptime(fecha_pron, '%Y-%m-%d')
        
        # Generar respuesta
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
    """Obtiene resumen de pronósticos de IA para una ciudad y fecha específica."""
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
                fuente=row['fuente'] or 'observado',
                id_est="CDMX",
                hora="00:00"
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
            modelo_id=first_row['modelo_id'] or 'IA_Model',
            modelo="Aprendizaje automático",
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
    """Endpoint legacy para compatibilidad. Redirige al endpoint principal."""
    return await get_ai_vi_transformer01(contaminante, ciudad, fecha_pron)

# ============================================================================
# PUNTO DE ENTRADA
# ============================================================================

if __name__ == "__main__":
    # Configuración para desarrollo usando puerto 6006 (debug) o 8888 (producción)
    uvicorn.run(
        "api_service4:app",
        host=API_CONFIG['host'],
        port=API_CONFIG['port'],
        reload=API_CONFIG['debug'],
        log_level="info"
    )


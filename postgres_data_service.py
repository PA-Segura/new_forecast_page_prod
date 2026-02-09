"""
Servicio principal de datos PostgreSQL para el sistema de pronósticos de calidad del aire.
Este es el sistema de PRODUCCIÓN que reemplaza completamente SQLite.

Usa las credenciales AMATE-SOLOREAD y las nuevas tablas forecast_*.
"""

import psycopg2
import netrc
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from scipy.stats import norm

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PostgresConnection:
    """Maneja la conexión a PostgreSQL con las nuevas tablas de pronóstico"""
    
    def __init__(self):
        self.connection = None
        self._connect()
    
    def _connect(self):
        """Establece conexión a PostgreSQL usando credenciales AMATE-SOLOREAD (igual que config.py)"""
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
            
            # Configuración de conexión
            host = account or os.getenv('DB_HOST', 'localhost')
            database = os.getenv('DB_NAME', 'contingencia')
            
            self.connection = psycopg2.connect(
                database=database,
                user=login or os.getenv('DB_USER', 'postgres'),
                host=host,
                password=password or os.getenv('DB_PASSWORD', ''),
                port=int(os.getenv('DB_PORT', '5432'))
            )
            
            logger.info(f"✅ Conectado a PostgreSQL en {host}/{database}")
            
        except Exception as e:
            logger.error(f"❌ Error conectando a PostgreSQL: {e}")
            self.connection = None
    
    def is_connected(self) -> bool:
        """Verifica si la conexión está activa"""
        if self.connection is None:
            return False
        try:
            # Verificar conexión con un query simple
            with self.connection.cursor() as cur:
                cur.execute("SELECT 1")
                return True
        except:
            return False
    
    def reconnect(self):
        """Reconecta a la base de datos"""
        if self.connection:
            try:
                self.connection.close()
            except:
                pass
        self._connect()
    
    def execute_query(self, query: str, params: Optional[Tuple] = None) -> pd.DataFrame:
        """
        Ejecuta una consulta SQL y retorna un DataFrame
        
        Args:
            query: Consulta SQL
            params: Parámetros para la consulta (opcional)
            
        Returns:
            DataFrame con los resultados
        """
        if not self.is_connected():
            self.reconnect()
            if not self.is_connected():
                logger.error("❌ No se pudo conectar a la base de datos")
                return pd.DataFrame()
        
        try:
            with self.connection.cursor() as cur:
                if params:
                    cur.execute(query, params)
                else:
                    cur.execute(query)
                
                # Obtener nombres de columnas
                columns = [desc[0] for desc in cur.description]
                
                # Obtener datos
                data = cur.fetchall()
                
                # Crear DataFrame
                df = pd.DataFrame(data, columns=columns)
                
                logger.debug(f"✅ Query ejecutada exitosamente: {len(df)} filas")
                return df
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando query: {e}")
            logger.error(f"Query: {query}")
            if params:
                logger.error(f"Parámetros: {params}")
            return pd.DataFrame()
    
    def close(self):
        """Cierra la conexión a la base de datos"""
        if self.connection:
            try:
                self.connection.close()
                logger.info("✅ Conexión a PostgreSQL cerrada")
            except:
                pass
            self.connection = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class ForecastDataService:
    """Servicio principal para obtener datos de pronóstico de las nuevas tablas PostgreSQL"""
    
    def __init__(self):
        self.connection = PostgresConnection()
        self.forecast_id = 7  # Nuevo ID de pronóstico
    
    def get_latest_forecast_date(self) -> Optional[datetime]:
        """Obtiene la fecha del último pronóstico disponible"""
        query = """
        SELECT MAX(fecha) as ultima_fecha 
        FROM forecast_otres 
        WHERE id_tipo_pronostico = %s
        """
        
        df = self.connection.execute_query(query, (self.forecast_id,))
        
        if not df.empty and 'ultima_fecha' in df.columns:
            return df['ultima_fecha'].iloc[0]
        return None
    
    def get_ozone_forecast(self, fecha: str, station: str = None) -> pd.DataFrame:
        """
        Obtiene pronóstico de ozono para una fecha específica
        
        Args:
            fecha: Fecha en formato 'YYYY-MM-DD HH:MM:SS'
            station: Estación específica (opcional, si no se especifica trae todas)
            
        Returns:
            DataFrame con el pronóstico de ozono
        """
        # Construir columnas de horas
        hour_columns = ', '.join([f'hour_p{str(i).zfill(2)}' for i in range(1, 25)])
        
        if station:
            # Pronóstico para una estación específica
            query = f"""
            SELECT fecha, id_est, {hour_columns}
            FROM forecast_otres 
            WHERE fecha = %s 
            AND id_tipo_pronostico = %s
            AND id_est = %s
            ORDER BY id_est
            """
            params = (fecha, self.forecast_id, station)
        else:
            # Pronóstico para todas las estaciones
            query = f"""
            SELECT fecha, id_est, {hour_columns}
            FROM forecast_otres 
            WHERE fecha = %s 
            AND id_tipo_pronostico = %s
            ORDER BY id_est
            """
            params = (fecha, self.forecast_id)
        
        return self.connection.execute_query(query, params)
    
    def get_pollutant_stats(self, fecha: str, pollutant: str) -> pd.DataFrame:
        """
        Obtiene estadísticas de un contaminante específico
        
        Args:
            fecha: Fecha en formato 'YYYY-MM-DD HH:MM:SS'
            pollutant: Contaminante (co, no, nodos, nox, pmco, pmdiez, pmdoscinco, sodos)
            
        Returns:
            DataFrame con las estadísticas (min, max, avg por hora)
        """
        # Mapeo de contaminantes a tablas
        pollutant_tables = {
            'co': 'forecast_co',
            'no': 'forecast_no',
            'nodos': 'forecast_nodos',
            'nox': 'forecast_nox',
            'pmco': 'forecast_pmco',
            'pmdiez': 'forecast_pmdiez',
            'pmdoscinco': 'forecast_pmdoscinco',
            'sodos': 'forecast_sodos'
        }
        
        if pollutant not in pollutant_tables:
            logger.error(f"❌ Contaminante no válido: {pollutant}")
            return pd.DataFrame()
        
        table = pollutant_tables[pollutant]
        
        # Construir columnas de estadísticas por hora
        stat_columns = []
        for hour in range(1, 25):
            hour_str = str(hour).zfill(2)
            stat_columns.extend([
                f'min_hour_p{hour_str}',
                f'max_hour_p{hour_str}',
                f'avg_hour_p{hour_str}'
            ])
        
        columns_str = ', '.join(stat_columns)
        
        # Construir query según la tabla
        if pollutant in ['nox', 'pmdiez', 'pmdoscinco', 'sodos']:
            # Estas tablas tienen id_tipo_pronostico
            query = f"""
            SELECT fecha, {columns_str}
            FROM {table}
            WHERE fecha = %s 
            AND id_tipo_pronostico = %s
            """
            params = (fecha, self.forecast_id)
            logger.info(f"📊 Query para {pollutant} con id_tipo_pronostico={self.forecast_id}")
        else:
            # Otras tablas no tienen id_tipo_pronostico
            query = f"""
            SELECT fecha, {columns_str}
            FROM {table}
            WHERE fecha = %s
            """
            params = (fecha,)
            logger.info(f"📊 Query para {pollutant} sin id_tipo_pronostico")
        
        return self.connection.execute_query(query, params)
    
    def get_all_pollutants_stats(self, fecha: str) -> Dict[str, pd.DataFrame]:
        """
        Obtiene estadísticas de todos los contaminantes para una fecha
        
        Args:
            fecha: Fecha en formato 'YYYY-MM-DD HH:MM:SS'
            
        Returns:
            Diccionario con DataFrames de cada contaminante
        """
        pollutants = ['co', 'no', 'nodos', 'nox', 'pmco', 'pmdiez', 'pmdoscinco', 'sodos']
        results = {}
        
        for pollutant in pollutants:
            df = self.get_pollutant_stats(fecha, pollutant)
            if not df.empty:
                results[pollutant] = df
            else:
                logger.warning(f"⚠️ No hay datos para {pollutant} en {fecha}")
        
        return results
    
    def get_available_stations(self) -> List[str]:
        """Obtiene lista de estaciones disponibles para ozono"""
        query = """
        SELECT DISTINCT id_est 
        FROM forecast_otres 
        WHERE id_tipo_pronostico = %s
        ORDER BY id_est
        """
        
        df = self.connection.execute_query(query, (self.forecast_id,))
        
        if not df.empty and 'id_est' in df.columns:
            return df['id_est'].tolist()
        return []
    
    def close(self):
        """Cierra la conexión"""
        if self.connection:
            self.connection.close()


# =====================================
# FUNCIONES PRINCIPALES DEL SISTEMA
# =====================================
# Estas son las funciones que usa la aplicación principal

def get_ozone_forecast(fecha: str, station: str = None) -> pd.DataFrame:
    """
    Función de conveniencia para obtener pronóstico de ozono
    """
    service = ForecastDataService()
    try:
        return service.get_ozone_forecast(fecha, station)
    finally:
        service.close()

def db_query_predhours(id_est: str, end_time_str: str) -> pd.DataFrame:
    """
    Consulta pronósticos de ozono para una estación específica
    Función principal del sistema
    """
    service = ForecastDataService()
    try:
        return service.get_ozone_forecast(end_time_str, id_est)
    finally:
        service.close()

def db_query_pasthours(id_est: str, start_time_str: str, end_time_str: str) -> pd.DataFrame:
    """
    Consulta datos históricos de ozono
    Por ahora retorna DataFrame vacío (se puede implementar si es necesario)
    """
    # TODO: Implementar consulta de datos históricos si es necesario
    return pd.DataFrame()

def db_query_max_predhour(end_time_str: str = None) -> pd.DataFrame:
    """
    Consulta los valores máximos del pronóstico de ozono para todas las estaciones
    Retorna DataFrame con columnas: id_est, name, lat, lon, max_pred
    """
    service = ForecastDataService()
    try:
        # Si no se especifica fecha, usar la última disponible
        if not end_time_str:
            end_time_str = service.get_latest_forecast_date()
            if end_time_str:
                end_time_str = end_time_str.strftime('%Y-%m-%d %H:%M:%S')
            else:
                return pd.DataFrame()
        
        # Obtener pronósticos para todas las estaciones
        all_forecasts = service.get_ozone_forecast(end_time_str)
        
        if all_forecasts.empty:
            return pd.DataFrame()
        
        # Calcular máximos por estación
        max_data = []
        station_coords = {
            'AJM': {'name': 'AJM - Ajusco Medio', 'lat': 19.154621, 'lon': -99.21286},
            'AJU': {'name': 'AJU - Ajusco', 'lat': 19.103353, 'lon': -99.162551},
            'ATI': {'name': 'ATI - Atizapán', 'lat': 19.580448, 'lon': -99.254532},
            'BJU': {'name': 'BJU - Benito Juárez', 'lat': 19.372885, 'lon': -99.159041},
            'CAM': {'name': 'CAM - Camarones', 'lat': 19.471715, 'lon': -99.165214},
            'CCA': {'name': 'CCA - Centro de Ciencias de la Atmósfera', 'lat': 19.326125, 'lon': -99.176901},
            'CHO': {'name': 'CHO - Chalco', 'lat': 19.26506, 'lon': -98.895455},
            'CUA': {'name': 'CUA - Cuajimalpa', 'lat': 19.364623, 'lon': -99.29141},
            'CUT': {'name': 'CUT - Cuautitlán', 'lat': 19.695024, 'lon': -99.1772},
            'DIC': {'name': 'DIC - Desierto de los Leones', 'lat': 19.302167, 'lon': -99.313833},
            'EAJ': {'name': 'EAJ - Ecoguardas Ajusco', 'lat': 19.130264, 'lon': -99.155845},
            'FAC': {'name': 'FAC - FES Acatlán', 'lat': 19.482247, 'lon': -99.244039},
            'HAN': {'name': 'HAN - Hangares', 'lat': 19.424513, 'lon': -99.072269},
            'INN': {'name': 'INN - Investigaciones Nucleares', 'lat': 19.297381, 'lon': -99.342414},
            'IZT': {'name': 'IZT - Iztacalco', 'lat': 19.384097, 'lon': -99.11261},
            'LAG': {'name': 'LAG - Laguna', 'lat': 19.424513, 'lon': -99.072269},
            'LLA': {'name': 'LLA - Los Laureles', 'lat': 19.609717, 'lon': -98.963008},
            'LPR': {'name': 'LPR - La Presa', 'lat': 19.135, 'lon': -99.074},
            'MER': {'name': 'MER - Merced', 'lat': 19.42461, 'lon': -99.119594},
            'MGH': {'name': 'MGH - Miguel Hidalgo', 'lat': 19.400255, 'lon': -99.202777},
            'MON': {'name': 'MON - Montecillo', 'lat': 19.461914, 'lon': -98.903739},
            'NEZ': {'name': 'NEZ - Nezahualcóyotl', 'lat': 19.400969, 'lon': -99.026988},
            'PED': {'name': 'PED - Pedregal', 'lat': 19.325, 'lon': -99.204},
            'SAG': {'name': 'SAG - San Agustín', 'lat': 19.529528, 'lon': -99.030583},
            'SFE': {'name': 'SFE - Santa Fe', 'lat': 19.357989, 'lon': -99.267089},
            'SHA': {'name': 'SHA - Sahagún', 'lat': 19.626814, 'lon': -98.982119},
            'SJA': {'name': 'SJA - San Juan Aragón', 'lat': 19.459136, 'lon': -99.096306},
            'TAH': {'name': 'TAH - Tláhuac', 'lat': 19.246919, 'lon': -99.01235},
            'TLA': {'name': 'TLA - Tlalnepantla', 'lat': 19.529528, 'lon': -99.030583},
            'UIZ': {'name': 'UIZ - UAM Iztapalapa', 'lat': 19.360556, 'lon': -99.073889}
        }
        
        for station in all_forecasts['id_est'].unique():
            station_data = all_forecasts[all_forecasts['id_est'] == station]
            if not station_data.empty:
                # Calcular máximo de las 24 horas (hour_p01 a hour_p24)
                hour_columns = [f'hour_p{i:02d}' for i in range(1, 25)]
                available_columns = [col for col in hour_columns if col in station_data.columns]
                
                if available_columns:
                    max_value = station_data[available_columns].max().max()
                    
                    # Obtener información de la estación
                    station_info = station_coords.get(station, {
                        'name': station,
                        'lat': 19.4,
                        'lon': -99.1
                    })
                    
                    max_data.append({
                        'id_est': station,
                        'name': station_info['name'],
                        'lat': station_info['lat'],
                        'lon': station_info['lon'],
                        'max_pred': max_value
                    })
        
        df_max = pd.DataFrame(max_data)
        return df_max
        
    except Exception as e:
        import logging
        logging.error(f"Error en db_query_max_predhour: {e}")
        return pd.DataFrame()
    finally:
        service.close()

def db_query_last_predhour(id_est: str, end_time_str: str) -> Tuple[pd.DataFrame, datetime]:
    """
    Consulta el último pronóstico de ozono
    Retorna DataFrame y fecha
    """
    service = ForecastDataService()
    try:
        df = service.get_ozone_forecast(end_time_str, id_est)
        latest_date = service.get_latest_forecast_date()
        return df, latest_date
    finally:
        service.close()

def get_last_available_date() -> datetime:
    """Obtiene la fecha del último pronóstico disponible"""
    service = ForecastDataService()
    try:
        latest_date = service.get_latest_forecast_date()
        if latest_date:
            return latest_date
        # Fallback: fecha actual menos 1 hora
        return datetime.now() - timedelta(hours=1)
    finally:
        service.close()

def get_available_stations() -> List[str]:
    """Obtiene lista de estaciones disponibles"""
    service = ForecastDataService()
    try:
        stations = service.get_available_stations()
        if stations:
            return stations
        # Fallback: estaciones por defecto
        return ["UIZ", "AJU", "ATI", "CUA", "SFE", "SAG", "CUT", "PED", "TAH", "GAM", 
                "IZT", "CCA", "HGM", "LPR", "MGH", "CAM", "FAC", "TLA", "MER", "XAL", 
                "LLA", "TLI", "UAX", "BJU", "MPA", "MON", "NEZ", "INN", "AJM", "VIF"]
    finally:
        service.close()

def get_maximum_ozone_forecast_summary(fecha: str = None) -> Dict[str, Any]:
    """
    Obtiene el resumen del máximo pronóstico de ozono para las próximas 24 horas.
    Retorna el valor máximo, la estación donde ocurre y la hora.
    
    Args:
        fecha: Fecha en formato 'YYYY-MM-DD HH:MM:SS' (opcional, usa la última disponible si no se especifica)
    
    Returns:
        Dict con:
            - max_value: Valor máximo pronosticado (float)
            - station: Código de la estación (str)
            - station_name: Nombre completo de la estación (str)
            - hour: Hora en formato 'HH:MM' (str)
            - hour_number: Número de hora (1-24) (int)
    """
    from datetime import timedelta
    import logging
    
    service = ForecastDataService()
    try:
        # SIEMPRE consultar la última fecha disponible si no se especifica
        if not fecha:
            logging.info("🔄 Consultando última fecha disponible en BD para resumen...")
            latest_date = service.get_latest_forecast_date()
            if latest_date:
                fecha = latest_date.strftime('%Y-%m-%d %H:%M:%S')
                logging.info(f"✅ Resumen: usando última fecha de BD: {fecha}")
            else:
                logging.warning("⚠️ Resumen: No hay fecha disponible en BD")
                return {
                    'max_value': None,
                    'station': None,
                    'station_name': None,
                    'hour': None,
                    'hour_number': None
                }
        else:
            logging.info(f"📋 Resumen: usando fecha especificada: {fecha}")
        
        # Obtener pronósticos para todas las estaciones (query fresca a la BD)
        all_forecasts = service.get_ozone_forecast(fecha)
        logging.info(f"📊 Resumen: obtenidos pronósticos para {len(all_forecasts)} estaciones")
        
        if all_forecasts.empty:
            return {
                'max_value': None,
                'station': None,
                'station_name': None,
                'hour': None,
                'hour_number': None
            }
        
        # Diccionario de nombres de estaciones
        station_coords = {
            'AJM': {'name': 'AJM - Ajusco Medio', 'lat': 19.154621, 'lon': -99.21286},
            'AJU': {'name': 'AJU - Ajusco', 'lat': 19.103353, 'lon': -99.162551},
            'ATI': {'name': 'ATI - Atizapán', 'lat': 19.580448, 'lon': -99.254532},
            'BJU': {'name': 'BJU - Benito Juárez', 'lat': 19.372885, 'lon': -99.159041},
            'CAM': {'name': 'CAM - Camarones', 'lat': 19.471715, 'lon': -99.165214},
            'CCA': {'name': 'CCA - Centro de Ciencias de la Atmósfera', 'lat': 19.326125, 'lon': -99.176901},
            'CHO': {'name': 'CHO - Chalco', 'lat': 19.26506, 'lon': -98.895455},
            'CUA': {'name': 'CUA - Cuajimalpa', 'lat': 19.364623, 'lon': -99.29141},
            'CUT': {'name': 'CUT - Cuautitlán', 'lat': 19.695024, 'lon': -99.1772},
            'DIC': {'name': 'DIC - Desierto de los Leones', 'lat': 19.302167, 'lon': -99.313833},
            'EAJ': {'name': 'EAJ - Ecoguardas Ajusco', 'lat': 19.130264, 'lon': -99.155845},
            'FAC': {'name': 'FAC - FES Acatlán', 'lat': 19.482247, 'lon': -99.244039},
            'HAN': {'name': 'HAN - Hangares', 'lat': 19.424513, 'lon': -99.072269},
            'INN': {'name': 'INN - Investigaciones Nucleares', 'lat': 19.297381, 'lon': -99.342414},
            'IZT': {'name': 'IZT - Iztacalco', 'lat': 19.384097, 'lon': -99.11261},
            'LAG': {'name': 'LAG - Laguna', 'lat': 19.424513, 'lon': -99.072269},
            'LLA': {'name': 'LLA - Los Laureles', 'lat': 19.609717, 'lon': -98.963008},
            'LPR': {'name': 'LPR - La Presa', 'lat': 19.135, 'lon': -99.074},
            'MER': {'name': 'MER - Merced', 'lat': 19.42461, 'lon': -99.119594},
            'MGH': {'name': 'MGH - Miguel Hidalgo', 'lat': 19.400255, 'lon': -99.202777},
            'MON': {'name': 'MON - Montecillo', 'lat': 19.461914, 'lon': -98.903739},
            'NEZ': {'name': 'NEZ - Nezahualcóyotl', 'lat': 19.400969, 'lon': -99.026988},
            'PED': {'name': 'PED - Pedregal', 'lat': 19.325, 'lon': -99.204},
            'SAG': {'name': 'SAG - San Agustín', 'lat': 19.529528, 'lon': -99.030583},
            'SFE': {'name': 'SFE - Santa Fe', 'lat': 19.357989, 'lon': -99.267089},
            'SHA': {'name': 'SHA - Sahagún', 'lat': 19.626814, 'lon': -98.982119},
            'SJA': {'name': 'SJA - San Juan Aragón', 'lat': 19.459136, 'lon': -99.096306},
            'TAH': {'name': 'TAH - Tláhuac', 'lat': 19.246919, 'lon': -99.01235},
            'TLA': {'name': 'TLA - Tlalnepantla', 'lat': 19.529528, 'lon': -99.030583},
            'UIZ': {'name': 'UIZ - UAM Iztapalapa', 'lat': 19.360556, 'lon': -99.073889}
        }
        
        # Encontrar el máximo global entre todas las estaciones y todas las horas
        max_value = None
        max_station = None
        max_hour_number = None
        
        # Parsear la fecha base del pronóstico
        fecha_base = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
        
        for _, row in all_forecasts.iterrows():
            station = row['id_est']
            
            # Revisar cada hora (hour_p01 a hour_p24)
            for hour_num in range(1, 25):
                hour_col = f'hour_p{hour_num:02d}'
                
                if hour_col in row and pd.notna(row[hour_col]):
                    value = float(row[hour_col])
                    
                    # Actualizar máximo si encontramos un valor mayor
                    if max_value is None or value > max_value:
                        max_value = value
                        max_station = station
                        max_hour_number = hour_num
        
        # Si encontramos un máximo, calcular la hora real
        if max_value is not None and max_station is not None and max_hour_number is not None:
            # La hora del pronóstico es fecha_base + max_hour_number horas - 1 hora (corrección)
            max_hour_datetime = fecha_base + timedelta(hours=max_hour_number) - timedelta(hours=1)
            max_hour_str = max_hour_datetime.strftime('%H:%M')
            
            # Obtener nombre de la estación
            station_info = station_coords.get(max_station, {
                'name': max_station
            })
            station_name = station_info['name']
            
            logging.info(f"✅ Resumen calculado: {max_value:.1f} ppb en {max_station} a las {max_hour_str}")
            
            return {
                'max_value': max_value,
                'station': max_station,
                'station_name': station_name,
                'hour': max_hour_str,
                'hour_number': max_hour_number
            }
        else:
            return {
                'max_value': None,
                'station': None,
                'station_name': None,
                'hour': None,
                'hour_number': None
            }
            
    except Exception as e:
        import logging
        logging.error(f"Error en get_maximum_ozone_forecast_summary: {e}")
        return {
            'max_value': None,
            'station': None,
            'station_name': None,
            'hour': None,
            'hour_number': None
        }
    finally:
        service.close()

# =====================================
# FUNCIONES DE PROBABILIDAD
# =====================================

def calculate_probabilities(df_pred_bd: pd.DataFrame) -> List[float]:
    """
    Calcula varias probabilidades basadas en diferentes criterios para el DataFrame proporcionado.
    Basado en la implementación de dash_ozono_v002.py
    """
    try:
        probabilities = []

        # Preparar datos de pronóstico
        df_pred_bd['fecha'] = pd.to_datetime(df_pred_bd['fecha'])
        timestamps_pred = [df_pred_bd['fecha'][0] + pd.Timedelta(hours=i) for i in range(1, 25)]
        values_pred = df_pred_bd.loc[0, 'hour_p01':'hour_p24']

        # Caso 1: Probabilidad de superar "Más de 50 ppb en 8hrs en siguientes 24 horas"
        mu, sigma = -0.43, 6.11  # Para mean_err_24h
        thresholdC2 = 50
        mean8probs = moving_average_probabilities(values_pred, 8, mu, sigma, thresholdC2)
        probabilities.append(max(mean8probs))

        # Caso 2: Probabilidad de superar "Umbral de 90 ppb en las siguientes 24 horas"
        forecast_level = values_pred.max()
        mu, sigma = 5.08, 18.03  # Para max_err_24h
        thresholdC3 = 90
        probabilities.append(probability_2pass_threshold(forecast_level, mu, sigma, thresholdC3))

        # Caso 3: Probabilidad de superar "Umbral de 120 ppb en las siguientes 24 horas"
        forecast_level = values_pred.max()
        mu, sigma = 5.08, 18.03  # Para max_err_24h
        thresholdC4 = 120
        probabilities.append(probability_2pass_threshold(forecast_level, mu, sigma, thresholdC4))

        # Caso 4: Probabilidad de superar Umbral de 150 ppb en las siguientes 24 horas
        forecast_level = values_pred.max()
        mu, sigma = 5.08, 18.03  # Para max_err_24h
        thresholdC1 = 150
        probabilities.append(probability_2pass_threshold(forecast_level, mu, sigma, thresholdC1))

        logger.info(f"✅ Probabilidades calculadas: {probabilities}")
        return probabilities

    except Exception as e:
        logger.error(f"❌ Error calculando probabilidades: {e}")
        import traceback
        traceback.print_exc()
        return [0.0, 0.0, 0.0, 0.0]

def calculate_prediction_intervals(df_pred_bd: pd.DataFrame) -> Tuple[List[float], List[float]]:
    """
    Calcula intervalos de predicción
    Por ahora retorna listas vacías (se puede implementar si es necesario)
    """
    # TODO: Implementar cálculo de intervalos de predicción
    return ([0]*24, [0]*24)

# =====================================
# FUNCIONES AUXILIARES
# =====================================

def moving_average_probabilities(values: pd.Series, window: int, mu: float, sigma: float, threshold: float) -> List[float]:
    """
    Calcula probabilidades usando media móvil
    """
    try:
        # Calcular media móvil
        moving_avg = values.rolling(window=window, center=True).mean()
        
        # Calcular probabilidades usando distribución normal
        probabilities = []
        for value in moving_avg:
            if pd.isna(value):
                probabilities.append(0.0)
            else:
                # Probabilidad de superar el umbral
                z_score = (threshold - value - mu) / sigma
                prob = 1 - norm.cdf(z_score)
                probabilities.append(max(0.0, min(1.0, prob)))
        
        return probabilities
    except:
        return [0.0] * len(values)

def probability_2pass_threshold(forecast_level: float, mu: float, sigma: float, threshold: float) -> float:
    """
    Calcula probabilidad de superar umbral usando distribución normal
    """
    try:
        z_score = (threshold - forecast_level - mu) / sigma
        prob = 1 - norm.cdf(z_score)
        return max(0.0, min(1.0, prob))
    except:
        return 0.0

# =====================================
# DICCIONARIO DE ESTACIONES
# =====================================

# Crear diccionario de estaciones
def _create_stations_dict():
    """Crea el diccionario de estaciones con nombres correctos"""
    stations = get_available_stations()
    stations_dict = {}
    
    # Diccionario con nombres correctos de estaciones (formato: "KEY - Nombre")
    station_names = {
        'AJM': 'AJM - Ajusco Medio',
        'AJU': 'AJU - Ajusco',
        'ATI': 'ATI - Atizapán',
        'BJU': 'BJU - Benito Juárez',
        'CAM': 'CAM - Camarones',
        'CCA': 'CCA - Centro de Ciencias de la Atmósfera',
        'CHO': 'CHO - Chalco',
        'CUA': 'CUA - Cuajimalpa',
        'CUT': 'CUT - Cuautitlán',
        'DIC': 'DIC - Desierto de los Leones',
        'EAJ': 'EAJ - Ecoguardas Ajusco',
        'FAC': 'FAC - FES Acatlán',
        'HAN': 'HAN - Hangares',
        'INN': 'INN - Investigaciones Nucleares',
        'IZT': 'IZT - Iztacalco',
        'LAG': 'LAG - Laguna',
        'LLA': 'LLA - Los Laureles',
        'LPR': 'LPR - La Presa',
        'MER': 'MER - Merced',
        'MGH': 'MGH - Miguel Hidalgo',
        'MON': 'MON - Montecillo',
        'NEZ': 'NEZ - Nezahualcóyotl',
        'PED': 'PED - Pedregal',
        'SAG': 'SAG - San Agustín',
        'SFE': 'SFE - Santa Fe',
        'SHA': 'SHA - Sahagún',
        'SJA': 'SJA - San Juan Aragón',
        'TAH': 'TAH - Tláhuac',
        'TLA': 'TLA - Tlalnepantla',
        'UIZ': 'UIZ - UAM Iztapalapa'
    }
    
    # Coordenadas aproximadas de las estaciones (se pueden actualizar)
    coordinates = {
        'UIZ': {'lat': 19.360556, 'lon': -99.073889},
        'AJU': {'lat': 19.103353, 'lon': -99.162551},
        'ATI': {'lat': 19.580448, 'lon': -99.254532},
        'CUA': {'lat': 19.364623, 'lon': -99.29141},
        'SFE': {'lat': 19.357989, 'lon': -99.267089},
        'SAG': {'lat': 19.529528, 'lon': -99.030583},
        'CUT': {'lat': 19.695024, 'lon': -99.1772},
        'PED': {'lat': 19.325, 'lon': -99.204},
        'TAH': {'lat': 19.246919, 'lon': -99.01235},
        'GAM': {'lat': 19.35, 'lon': -99.15},
        'IZT': {'lat': 19.384097, 'lon': -99.11261},
        'CCA': {'lat': 19.326125, 'lon': -99.176901},
        'HGM': {'lat': 19.35, 'lon': -99.15},
        'LPR': {'lat': 19.135, 'lon': -99.074},
        'MGH': {'lat': 19.400255, 'lon': -99.202777},
        'CAM': {'lat': 19.471715, 'lon': -99.165214},
        'FAC': {'lat': 19.482247, 'lon': -99.244039},
        'TLA': {'lat': 19.529528, 'lon': -99.030583},
        'MER': {'lat': 19.42461, 'lon': -99.119594},
        'XAL': {'lat': 19.35, 'lon': -99.15},
        'LLA': {'lat': 19.609717, 'lon': -98.963008},
        'TLI': {'lat': 19.35, 'lon': -99.15},
        'UAX': {'lat': 19.35, 'lon': -99.15},
        'BJU': {'lat': 19.372885, 'lon': -99.159041},
        'MPA': {'lat': 19.35, 'lon': -99.15},
        'MON': {'lat': 19.461914, 'lon': -98.903739},
        'NEZ': {'lat': 19.400969, 'lon': -99.026988},
        'INN': {'lat': 19.297381, 'lon': -99.342414},
        'AJM': {'lat': 19.154621, 'lon': -99.21286},
        'VIF': {'lat': 19.35, 'lon': -99.15},
        'CHO': {'lat': 19.26506, 'lon': -98.895455},
        'DIC': {'lat': 19.302167, 'lon': -99.313833},
        'EAJ': {'lat': 19.130264, 'lon': -99.155845},
        'HAN': {'lat': 19.424513, 'lon': -99.072269},
        'LAG': {'lat': 19.424513, 'lon': -99.072269},
        'SHA': {'lat': 19.626814, 'lon': -98.982119},
        'SJA': {'lat': 19.459136, 'lon': -99.096306}
    }
    
    for station in stations:
        # Usar nombre correcto si está disponible, sino usar formato genérico
        name = station_names.get(station, f'{station} - Estación')
        
        if station in coordinates:
            stations_dict[station] = {
                'name': name,
                'lat': coordinates[station]['lat'],
                'lon': coordinates[station]['lon']
            }
        else:
            # Coordenadas por defecto
            stations_dict[station] = {
                'name': name,
                'lat': 19.35,
                'lon': -99.15
            }
    
    return stations_dict

# Crear diccionario de estaciones
stations_dict = _create_stations_dict()

# =====================================
# INICIALIZACIÓN DEL SISTEMA
# =====================================

def initialize_postgres_system():
    """Inicializa el sistema PostgreSQL"""
    try:
        # Verificar conexión
        service = ForecastDataService()
        latest_date = service.get_latest_forecast_date()
        stations = service.get_available_stations()
        service.close()
        
        logger.info(f"✅ Sistema PostgreSQL inicializado correctamente")
        logger.info(f"   📅 Última fecha de pronóstico: {latest_date}")
        logger.info(f"   🏭 Estaciones disponibles: {len(stations)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error inicializando sistema PostgreSQL: {e}")
        return False

if __name__ == "__main__":
    # Test del sistema
    print("🧪 Probando sistema PostgreSQL...")
    
    if initialize_postgres_system():
        print("✅ Sistema PostgreSQL funcionando correctamente")
        
        # Obtener fecha más reciente
        latest_date = get_last_available_date()
        print(f"📅 Última fecha de pronóstico: {latest_date}")
        
        # Obtener estaciones disponibles
        stations = get_available_stations()
        print(f"🏭 Estaciones disponibles: {len(stations)}")
        print(f"   Primeras 5: {stations[:5]}")
        
        # Obtener pronóstico de ozono para la primera estación
        if stations:
            ozone_df = db_query_predhours(stations[0], latest_date.strftime('%Y-%m-%d %H:%M:%S'))
            print(f"📊 Datos de ozono para {stations[0]}: {len(ozone_df)} filas")
            
            # Obtener estadísticas de CO
            service = ForecastDataService()
            co_stats = service.get_pollutant_stats(latest_date.strftime('%Y-%m-%d %H:%M:%S'), 'co')
            service.close()
            print(f"📊 Estadísticas de CO: {len(co_stats)} filas")
    else:
        print("❌ Sistema PostgreSQL no pudo inicializarse")
"""
Configuración centralizada para la aplicación de pronóstico de calidad del aire.
Maneja diferentes modos de operación de manera profesional.
"""

from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import os
import json
import netrc

# =============================================================================
# CONFIGURACIÓN GLOBAL PARA PRONÓSTICOS DE OZONO
# =============================================================================
# Variable configurable para cambiar entre diferentes tipos de pronóstico
# - 6: Estándar SQLite anterior
# - 7: Nuevo estándar PostgreSQL (recomendado)
OZONE_FORECAST_ID = 7  # Cambiar aquí para alternar entre 6 y 7

# Función para obtener el ID del pronóstico de ozono
def get_ozone_forecast_id() -> int:
    """
    Retorna el ID del tipo de pronóstico para ozono.
    
    Returns:
        int: ID del tipo de pronóstico (6 o 7)
    
    Ejemplo de uso:
        from config import get_ozone_forecast_id
        forecast_id = get_ozone_forecast_id()  # Retorna 7 por defecto
    """
    return OZONE_FORECAST_ID

# Función para cambiar dinámicamente el ID del pronóstico
def set_ozone_forecast_id(new_id: int) -> None:
    """
    Cambia el ID del tipo de pronóstico para ozono.
    
    Args:
        new_id (int): Nuevo ID (6 o 7)
    
    Ejemplo de uso:
        from config import set_ozone_forecast_id
        set_ozone_forecast_id(6)  # Cambiar a estándar anterior
        set_ozone_forecast_id(7)  # Cambiar a nuevo estándar
    """
    global OZONE_FORECAST_ID
    if new_id in [6, 7]:
        OZONE_FORECAST_ID = new_id
        print(f"🔄 ID de pronóstico de ozono cambiado a: {new_id}")
    else:
        print(f"⚠️ ID inválido: {new_id}. Solo se permiten valores 6 o 7.")

class DataMode(Enum):
    """
    Modos de operación para el manejo de datos.
    
    - PRODUCTION: Datos reales de la base de datos (modo final)
    - MOCK_SYNTHETIC: Datos sintéticos generados aleatoriamente (desarrollo)
    - MOCK_HISTORICAL: Datos reales de una fecha específica (testing)
    - HYBRID: Combinación de datos reales y mock según disponibilidad
    """
    PRODUCTION = "production"
    MOCK_SYNTHETIC = "mock_synthetic"
    MOCK_HISTORICAL = "mock_historical"
    HYBRID = "hybrid"

class Environment(Enum):
    """
    Entornos de ejecución.
    """
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

class AppConfig:
    """
    Configuración centralizada de la aplicación.
    """
    
    def __init__(self):
        # =============================================================================
        # CONFIGURACIÓN POSTGRESQL PARA PRODUCCIÓN
        # =============================================================================
        self.USE_SQLITE_CONTINGENCY = False  # Desactivado - ahora usamos PostgreSQL
        self.USE_POSTGRESQL_PRODUCTION = True  # Sistema principal PostgreSQL
        self.SQLITE_FORECAST_DB_PATH = "/home/pedro/git2/gitflow2/news_july/ensamble_ai_pollution_forecast/forecast_predictions.db"
        self.SQLITE_HISTORICAL_DB_PATH = "/home/pedro/git2/gitflow2/hack_sqlite/ensamble_ai_pollution_forecast/contingencia_sqlite_bd.db"
        
        # Configuración por defecto - Si PostgreSQL está activado, usar modo PRODUCTION
        self.environment = Environment.PRODUCTION
        if self.USE_POSTGRESQL_PRODUCTION:
            self.data_mode = DataMode.PRODUCTION  # Usar datos reales con PostgreSQL
        elif self.USE_SQLITE_CONTINGENCY:
            self.data_mode = DataMode.PRODUCTION  # Usar datos reales cuando SQLite está activado
        else:
            self.data_mode = DataMode.MOCK_HISTORICAL
        
        # Fecha de referencia para datos históricos mock (solo se usa si no hay SQLite)
        self.mock_reference_date = datetime(2023, 5, 15, 14, 0, 0)  # 15 de mayo 2023, 14:00
        
        # Configuración de base de datos PostgreSQL de PRODUCCIÓN
        def get_db_credentials():
            """Obtiene credenciales de BD desde .netrc"""
            try:
                n = netrc.netrc()
                login, account, password = n.authenticators('AMATE-SOLOREAD')
                return login, password, account
            except (FileNotFoundError, netrc.NetrcParseError):
                # Fallback a variables de entorno
                return os.getenv('DB_USER'), os.getenv('DB_PASSWORD'), os.getenv('DB_HOST')

        # Configuración PostgreSQL de producción
        login, password, account = get_db_credentials()
        self.db_config = {
            'host': account or os.getenv('DB_HOST', '132.248.8.152'),
            'port': os.getenv('DB_PORT', '5432'),
            'database': os.getenv('DB_NAME', 'contingencia'),
            'user': login or 'forecast_user',
            'password': password or '',
            'forecast_id': 7  # Nuevo ID de pronóstico PostgreSQL
        }
        
        # Configuración de la aplicación
        self.app_config = {
            'debug': True,
            'host': '0.0.0.0',
            'port': 8888,
            'title': 'Pronóstico de Calidad del Aire'
        }
        
        # Configuración de datos
        self.data_config = {
            'default_station': 'MER',
            'forecast_hours': 24,
            'historical_hours': 24,
            'update_interval': 300  # 5 minutos
        }
        
        # Cargar configuración desde variables de entorno
        self._load_from_environment()
        
    def _load_from_environment(self):
        """Carga configuración desde variables de entorno."""
        
        # Si PostgreSQL está activado, SIEMPRE usar modo PRODUCTION
        if self.USE_POSTGRESQL_PRODUCTION:
            print("🔄 PostgreSQL activado: forzando modo PRODUCTION")
            self.data_mode = DataMode.PRODUCTION
        # Si SQLite está activado, forzar modo PRODUCTION
        elif self.USE_SQLITE_CONTINGENCY:
            print("🔄 SQLite activado: forzando modo PRODUCTION")
            self.data_mode = DataMode.PRODUCTION
        else:
            # Modo de datos normal (solo si ninguna BD está activada)
            data_mode_str = os.getenv('DATA_MODE', 'mock_historical')
            try:
                self.data_mode = DataMode(data_mode_str)
            except ValueError:
                print(f"⚠️ Modo de datos '{data_mode_str}' no válido, usando MOCK_HISTORICAL")
                if self.is_debug_mode():
                    print(f"   📋 Modos válidos: {[mode.value for mode in DataMode]}")
                    print(f"   🔧 Usando: MOCK_HISTORICAL")
                self.data_mode = DataMode.MOCK_HISTORICAL
        
        # Entorno
        env_str = os.getenv('ENVIRONMENT', 'development')
        try:
            self.environment = Environment(env_str)
        except ValueError:
            print(f"⚠️ Entorno '{env_str}' no válido, usando DEVELOPMENT")
            if self.is_debug_mode():
                print(f"   📋 Entornos válidos: {[env.value for env in Environment]}")
                print(f"   🔧 Usando: DEVELOPMENT")
            self.environment = Environment.DEVELOPMENT
        
        # Fecha de referencia mock (solo si SQLite no está activado)
        if not self.USE_SQLITE_CONTINGENCY:
            mock_date_str = os.getenv('MOCK_REFERENCE_DATE')
            if mock_date_str:
                try:
                    self.mock_reference_date = datetime.strptime(mock_date_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    print(f"⚠️ Fecha de referencia mock '{mock_date_str}' no válida, usando fecha por defecto")
        else:
            print("🔄 SQLite activado: ignorando fecha de referencia mock")
        
        # Debug mode
        debug_str = os.getenv('DEBUG', 'true').lower()
        self.app_config['debug'] = debug_str in ('true', '1', 'yes')
        
        # Puerto
        port_str = os.getenv('PORT')
        if port_str:
            try:
                self.app_config['port'] = int(port_str)
            except ValueError:
                print(f"⚠️ Puerto '{port_str}' no válido, usando 8889")
    
    def get_data_service_config(self) -> Dict[str, Any]:
        """
        Retorna configuración para el servicio de datos.
        """
        config = {
            'use_mock_data': self.data_mode in [DataMode.MOCK_SYNTHETIC, DataMode.MOCK_HISTORICAL],
            'mock_reference_date': self.mock_reference_date,
            'data_mode': self.data_mode,
            'environment': self.environment
        }
        
        # Configuración específica por modo
        if self.data_mode == DataMode.MOCK_HISTORICAL:
            config.update({
                'use_real_db_for_mock': True,  # Usar BD real pero con fecha específica
                'fallback_to_synthetic': True  # Si no hay datos, usar sintéticos
            })
        elif self.data_mode == DataMode.MOCK_SYNTHETIC:
            config.update({
                'use_real_db_for_mock': False,
                'fallback_to_synthetic': False
            })
        elif self.data_mode == DataMode.HYBRID:
            config.update({
                'use_real_db_for_mock': True,
                'fallback_to_synthetic': True,
                'prefer_real_data': True
            })
        else:  # PRODUCTION
            config.update({
                'use_real_db_for_mock': False,
                'fallback_to_synthetic': False,
                'prefer_real_data': True
            })
        
        return config
    
    def get_sqlite_config(self) -> Dict[str, Any]:
        """Obtiene la configuración específica de SQLite."""
        return {
            'use_sqlite_contingency': self.USE_SQLITE_CONTINGENCY,
            'forecast_db_path': self.SQLITE_FORECAST_DB_PATH,
            'historical_db_path': self.SQLITE_HISTORICAL_DB_PATH
        }
    
    def is_sqlite_mode(self) -> bool:
        """Verifica si está en modo SQLite."""
        return self.USE_SQLITE_CONTINGENCY
    
    def is_postgresql_mode(self) -> bool:
        """Verifica si está en modo PostgreSQL."""
        return self.USE_POSTGRESQL_PRODUCTION
    
    def get_app_title(self) -> str:
        """Retorna el título de la aplicación con indicadores de modo."""
        base_title = self.app_config['title']
        
        if self.environment == Environment.DEVELOPMENT:
            mode_indicators = []
            
            if self.data_mode == DataMode.MOCK_SYNTHETIC:
                mode_indicators.append("DATOS SINTÉTICOS")
            elif self.data_mode == DataMode.MOCK_HISTORICAL:
                mode_indicators.append(f"DATOS HISTÓRICOS ({self.mock_reference_date.strftime('%Y-%m-%d')})")
            elif self.data_mode == DataMode.HYBRID:
                mode_indicators.append("MODO HÍBRIDO")
            
            # Agregar indicador de base de datos activa
            if self.USE_POSTGRESQL_PRODUCTION:
                mode_indicators.append("POSTGRESQL PRODUCCIÓN")
            elif self.USE_SQLITE_CONTINGENCY:
                mode_indicators.append("SQLITE CONTINGENCIA")
            
            if mode_indicators:
                return f"[{' | '.join(mode_indicators)}] {base_title}"
        
        return base_title
    
    def is_debug_mode(self) -> bool:
        """Determina si estamos en modo debug."""
        return self.app_config['debug'] or self.environment == Environment.DEVELOPMENT
    
    def get_current_reference_date(self) -> datetime:
        """
        Retorna la fecha de referencia actual según el modo de datos.
        """
        if self.data_mode == DataMode.MOCK_HISTORICAL:
            return self.mock_reference_date
        elif self.data_mode == DataMode.MOCK_SYNTHETIC:
            # Para datos sintéticos, usar fecha actual pero con hora fija
            now = datetime.now()
            return now.replace(hour=14, minute=0, second=0, microsecond=0)
        elif self.data_mode == DataMode.PRODUCTION and self.USE_POSTGRESQL_PRODUCTION:
            # Si está en modo PostgreSQL, SIEMPRE obtener la fecha real del último pronóstico
            try:
                from postgres_data_service import get_last_available_date
                last_forecast_date = get_last_available_date()
                if last_forecast_date:
                    print(f"✅ Usando última fecha disponible de PostgreSQL: {last_forecast_date}")
                    return last_forecast_date
                else:
                    print("⚠️ No se pudo obtener fecha de pronóstico PostgreSQL, usando fecha actual")
                    return datetime.now()
            except Exception as e:
                print(f"⚠️ Error obteniendo fecha PostgreSQL: {e}, usando fecha actual")
                return datetime.now()
        elif self.data_mode == DataMode.PRODUCTION and self.USE_SQLITE_CONTINGENCY:
            # Si está en modo SQLite, intentar obtener la fecha real del último pronóstico
            try:
                from sqlite_data_service import get_sqlite_service
                sqlite_service = get_sqlite_service()
                last_forecast_date = sqlite_service.get_last_forecast_date()
                if last_forecast_date:
                    return datetime.strptime(last_forecast_date, '%Y-%m-%d %H:%M:%S')
                else:
                    print("⚠️ No se pudo obtener fecha de pronóstico SQLite, usando fecha actual")
                    return datetime.now()
            except Exception as e:
                print(f"⚠️ Error obteniendo fecha SQLite: {e}, usando fecha actual")
                return datetime.now()
        else:
            return datetime.now()
    
    def should_show_debug_annotations(self) -> bool:
        """Determina si mostrar anotaciones de debug en los gráficos."""
        return self.is_debug_mode() and self.data_mode in [DataMode.MOCK_SYNTHETIC, DataMode.MOCK_HISTORICAL]

# Instancia global de configuración
app_config = AppConfig()

# Funciones de conveniencia
def get_data_mode() -> DataMode:
    """Retorna el modo de datos actual."""
    return app_config.data_mode

def get_environment() -> Environment:
    """Retorna el entorno actual."""
    return app_config.environment

def is_mock_mode() -> bool:
    """Determina si estamos en modo mock."""
    return app_config.data_mode in [DataMode.MOCK_SYNTHETIC, DataMode.MOCK_HISTORICAL]

def is_production_mode() -> bool:
    """Determina si estamos en modo producción."""
    return app_config.data_mode == DataMode.PRODUCTION and app_config.environment == Environment.PRODUCTION

def get_mock_reference_date() -> datetime:
    """Retorna la fecha de referencia para datos mock."""
    return app_config.mock_reference_date

def get_current_reference_date() -> datetime:
    """Retorna la fecha de referencia actual."""
    return app_config.get_current_reference_date()

def is_sqlite_mode() -> bool:
    """Verifica si está en modo SQLite."""
    return app_config.is_sqlite_mode()

def is_postgresql_mode() -> bool:
    """Verifica si está en modo PostgreSQL."""
    return app_config.is_postgresql_mode()

def get_sqlite_config() -> Dict[str, Any]:
    """Obtiene la configuración de SQLite."""
    return app_config.get_sqlite_config()

def get_postgresql_config() -> Dict[str, Any]:
    """Obtiene la configuración de PostgreSQL."""
    return app_config.db_config

# Configuración específica para diferentes componentes
# Si PostgreSQL está activado, SIEMPRE usar fecha dinámica del último pronóstico
if app_config.USE_POSTGRESQL_PRODUCTION and app_config.data_mode == DataMode.PRODUCTION:
    try:
        from postgres_data_service import get_last_available_date
        last_forecast_date = get_last_available_date()
        if last_forecast_date:
            specific_date = last_forecast_date.strftime('%Y-%m-%d %H:%M:%S')
            print(f"🎯 Configuración específica: usando última fecha PostgreSQL {specific_date}")
        else:
            specific_date = app_config.mock_reference_date.strftime('%Y-%m-%d %H:%M:%S')
            print(f"⚠️ Configuración específica: fallback a fecha mock {specific_date}")
    except Exception as e:
        specific_date = app_config.mock_reference_date.strftime('%Y-%m-%d %H:%M:%S')
        print(f"❌ Configuración específica: error PostgreSQL, fallback a fecha mock {specific_date}")
# Si SQLite está activado, usar fecha dinámica del último pronóstico (fallback)
elif app_config.USE_SQLITE_CONTINGENCY and app_config.data_mode == DataMode.PRODUCTION:
    try:
        from sqlite_data_service import get_sqlite_service
        sqlite_service = get_sqlite_service()
        last_forecast_date = sqlite_service.get_last_forecast_date()
        if last_forecast_date:
            specific_date = last_forecast_date
        else:
            specific_date = app_config.mock_reference_date.strftime('%Y-%m-%d %H:%M:%S')
    except:
        specific_date = app_config.mock_reference_date.strftime('%Y-%m-%d %H:%M:%S')
else:
    specific_date = app_config.mock_reference_date.strftime('%Y-%m-%d %H:%M:%S')

DEFAULT_DATE_CONFIG = {
    'use_specific_date': True,
    'specific_date': specific_date,
    'station_default': 'MER'  # Estación por defecto
}

# COLORS moved to professional configuration section below

# CHART_CONFIG moved to professional configuration section below

# Configuración de estaciones por defecto
DEFAULT_STATION = 'MER'
STATIONS_WITH_DATA = ['MER', 'UIZ', 'CCA', 'PED', 'TLA']  # Estaciones que típicamente tienen datos

# =====================================
# CONFIGURACIÓN DE COLORES Y ESTILOS (vdev8)
# =====================================

# Colores principales (exactamente como vdev8)
COLORS = {
    'background': '#edeff2',
    'header': '#00505C',
    'text': '#2c3e50',
    'grid': 'rgba(173, 216, 230, 0.3)',
    'prediction_band': 'rgba(160, 223, 242, 0.25)',
    'threshold': 'rgba(250, 0, 0, 0.6)',
    'card': '#ffffff',
    'accent': '#3498db',
    'success': '#2ecc71',
    'warning': '#f1c40f',
    'danger': '#e74c3c',
    'gradient_start': '#00505C',
    'gradient_end': '#006D7D',
    # Colores para calidad del aire (estándares oficiales)
    'aire_buena': '#00E400',          # Verde
    'aire_aceptable': '#FFFF00',      # Amarillo
    'aire_mala': '#FF7E00',           # Naranja
    'aire_muy_mala': '#FF0000',       # Rojo
    'aire_extremadamente_mala': '#8F3F97'  # Morado
}

# Umbrales de ozono en ppb (convertidos de ppm) - exactamente como vdev8
OZONE_THRESHOLDS = {
    'buena': 58,          # 0.058 ppm * 1000
    'aceptable': 90,      # 0.090 ppm * 1000
    'mala': 135,          # 0.135 ppm * 1000
    'muy_mala': 175       # 0.175 ppm * 1000
}

# Estilos (exactamente como vdev8)
STYLES = {
    'header': {
        'font-family': 'Helvetica',
        'color': 'white',
        'padding': '20px',
        'font-size': '32px',
        'font-weight': 'bold',
        'text-shadow': '2px 2px 4px rgba(0,0,0,0.3)',
        'background': f'linear-gradient(135deg, {COLORS["gradient_start"]}, {COLORS["gradient_end"]})',
        'border-radius': '15px',
        'box-shadow': '0 4px 6px rgba(0,0,0,0.1)'
    },
    'title': {
        'font-family': 'Helvetica',
        'font-size': '26px',
        'text-align': 'center',
        'margin': '20px',
        'color': COLORS['text'],
        'font-weight': 'bold',
        'text-shadow': '1px 1px 2px rgba(0,0,0,0.1)'
    },
    'container': {
        'margin': '20px',
        'padding': '30px',
        'border-radius': '15px',
        'box-shadow': '0 8px 16px rgba(0,0,0,0.1)',
        'background-color': COLORS['card'],
        'transition': 'all 0.3s ease',
        'border': '1px solid rgba(0,0,0,0.05)'
    },
    'dropdown': {
        'width': '400px',
        'font-family': 'Helvetica',
        'font-size': '16px',
        'border-radius': '8px',
        'box-shadow': '0 2px 4px rgba(0,0,0,0.05)'
    },
    'label': {
        'font-family': 'Helvetica',
        'font-size': '20px',
        'font-weight': 'bold',
        'color': COLORS['text'],
        'margin-bottom': '15px',
        'text-shadow': '1px 1px 2px rgba(0,0,0,0.1)'
    },
    'footer': {
        'text-align': 'center',
        'padding': '25px',
        'background': f'linear-gradient(135deg, {COLORS["gradient_start"]}, {COLORS["gradient_end"]})',
        'color': 'white',
        'margin-top': '40px',
        'border-radius': '15px 15px 0 0',
        'box-shadow': '0 -4px 6px rgba(0,0,0,0.1)'
    }
}

# Configuración de contaminantes con metadatos - NUEVO SISTEMA POSTGRESQL
POLLUTANT_CONFIG = {
    'O3': {
        'name': 'O₃ (Ozono)',
        'units': 'ppb',
        'db_key': 'forecast_otres',  # Nueva tabla PostgreSQL
        'has_station_forecast': True,
        'color': '#FF6B6B',
        'forecast_id': OZONE_FORECAST_ID  # Usa la variable global configurable
    },
    'PM2.5': {
        'name': 'PM2.5',
        'units': 'µg/m³',
        'db_key': 'forecast_pmdoscinco',  # Nueva tabla PostgreSQL
        'has_station_forecast': False,
        'color': '#4ECDC4',
        'forecast_id': 7
    },
    'PM10': {
        'name': 'PM10',
        'units': 'µg/m³',
        'db_key': 'forecast_pmdiez',  # Nueva tabla PostgreSQL
        'has_station_forecast': False,
        'color': '#45B7D1',
        'forecast_id': 7
    },
    'NO2': {
        'name': 'NO₂',
        'units': 'ppb',
        'db_key': 'forecast_nodos',  # Nueva tabla PostgreSQL
        'has_station_forecast': False,
        'color': '#96CEB4',
        'forecast_id': 7
    },
    'CO': {
        'name': 'CO',
        'units': 'ppm',
        'db_key': 'forecast_co',  # Nueva tabla PostgreSQL
        'has_station_forecast': False,
        'color': '#FFEAA7',
        'forecast_id': 7
    },
    'SO2': {
        'name': 'SO₂',
        'units': 'ppb',
        'db_key': 'forecast_sodos',  # Nueva tabla PostgreSQL
        'has_station_forecast': False,
        'color': '#DDA0DD',
        'forecast_id': 7
    }
}

# Configuración de la aplicación Dash (título como vdev8)
APP_CONFIG = {
    'title': 'Pronóstico de Calidad del Aire Basado en Redes Neuronales: Concentraciones de Ozono, PM10 y PM2.5',
    'debug': True,
    'host': '0.0.0.0',
    'port': 8888,
    'suppress_callback_exceptions': True
}

# Configuración del mapa (exactamente como vdev8)
MAP_CONFIG = {
    'center_lat': 19.35,
    'center_lon': -99.15,
    'zoom': 8.2,  # Reducido de 8.5 a 8.2 para ver más área (como vdev8)
    'mapbox_style': "white-bg",
    'max_value': 250,  # ppb para normalización
    'marker_size': 20,
    'height': 400
}

# Configuración de los gráficos (como vdev8)
CHART_CONFIG = {
    'responsive': True,
    'displayModeBar': False,
    'height': 400,
    'margin': dict(t=40, b=40, l=40, r=40),  # Exactamente como vdev8
    'font_family': 'Helvetica, sans-serif'
}

# Configuración de indicadores (diales) - como vdev8
INDICATOR_CONFIG = {
    'height': 230,  # Exactamente como vdev8
    'margin': dict(t=60, b=25, l=25, r=25),  # Exactamente como vdev8
    'thresholds': {
        'low': 0.2,
        'medium': 0.5
    },
    'colors': {
        'low': 'green',
        'medium': 'yellow',
        'high': 'red'
    }
}

# Labels para probabilidades (exactamente como vdev8)
PROBABILITY_LABELS = [
    "Media de más de 50 ppb en 8hrs",
    "Umbral de 90 ppb",
    "Umbral de 120 ppb",
    "Umbral de 150 ppb"
]

# Configuración responsiva de Bootstrap
RESPONSIVE_CONFIG = {
    'breakpoints': {
        'xs': 12,
        'sm': 12, 
        'md': 8,
        'lg': 6
    },
    'card_breakpoints': {
        'xs': 12,
        'md': 6
    }
}

class ConfigManager:
    """Gestor centralizado de configuraciones"""
    
    def __init__(self):
        self.geojson: Optional[Dict] = None
        self._load_geojson()
    
    def _load_geojson(self) -> None:
        """Carga el archivo GeoJSON de límites de la Ciudad de México"""
        try:
            with open('./assets/mexico_city.geojson') as f:
                self.geojson = json.load(f)
        except FileNotFoundError:
            print("⚠️  Warning: mexico_city.geojson not found. Map will work without city boundaries.")
            if app_config.is_debug_mode():
                print(f"    Directorio actual: {os.getcwd()}")
                print(f"   🔍 Buscando en: ./assets/mexico_city.geojson")
                print(f"   💡 Asegúrate de que el archivo existe en el directorio assets/")
            self.geojson = None
    
    def get_pollutant_info(self, pollutant_key: str) -> Dict[str, Any]:
        """Obtiene información completa de un contaminante"""
        return POLLUTANT_CONFIG.get(pollutant_key, {
            'name': pollutant_key,
            'units': 'units',
            'db_key': pollutant_key.lower(),
            'has_station_forecast': False,
            'color': '#999999'
        })
    
    def get_air_quality_category(self, value: float) -> str:
        """Determina la categoría de calidad del aire basada en umbrales"""
        try:
            value = float(value)
            if value < OZONE_THRESHOLDS['buena']:
                return 'Buena'
            elif value < OZONE_THRESHOLDS['aceptable']:
                return 'Aceptable'
            elif value < OZONE_THRESHOLDS['mala']:
                return 'Mala'
            elif value < OZONE_THRESHOLDS['muy_mala']:
                return 'Muy Mala'
            else:
                return 'Extremadamente Mala'
        except (ValueError, TypeError):
            return 'No disponible'
    
    def get_colorscale_for_map(self) -> list:
        """Genera escala de colores normalizada para el mapa"""
        max_value = MAP_CONFIG['max_value']
        return [
            [0/max_value, COLORS['aire_buena']],
            [OZONE_THRESHOLDS['buena']/max_value, COLORS['aire_buena']],
            [OZONE_THRESHOLDS['buena']/max_value, COLORS['aire_aceptable']],
            [OZONE_THRESHOLDS['aceptable']/max_value, COLORS['aire_aceptable']],
            [OZONE_THRESHOLDS['aceptable']/max_value, COLORS['aire_mala']],
            [OZONE_THRESHOLDS['mala']/max_value, COLORS['aire_mala']],
            [OZONE_THRESHOLDS['mala']/max_value, COLORS['aire_muy_mala']],
            [OZONE_THRESHOLDS['muy_mala']/max_value, COLORS['aire_muy_mala']],
            [OZONE_THRESHOLDS['muy_mala']/max_value, COLORS['aire_extremadamente_mala']],
            [1.0, COLORS['aire_extremadamente_mala']]
        ]

# Instancia global del gestor de configuración  
config_manager = ConfigManager()

if __name__ == "__main__":
    print("🔧 CONFIGURACIÓN DE LA APLICACIÓN")
    print("=" * 50)
    print(f"Entorno: {app_config.environment.value}")
    print(f"Modo de datos: {app_config.data_mode.value}")
    print(f"Debug: {app_config.is_debug_mode()}")
    print(f"Fecha de referencia mock: {app_config.mock_reference_date}")
    print(f"Título de la app: {app_config.get_app_title()}")
    print(f"Puerto: {app_config.app_config['port']}")
    print(f"Estación por defecto: {app_config.data_config['default_station']}")
    print("=" * 50) 
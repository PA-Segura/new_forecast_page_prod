"""
Módulo de servicios de datos para el prototipo de calidad del aire
Arquitectura modular para desarrollo iterativo
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import sys
import os

# Importar configuración para diferentes bases de datos
from config import is_sqlite_mode, get_sqlite_config, is_postgresql_mode, get_postgresql_config

# Importar servicio PostgreSQL (sistema principal)
try:
    from postgres_data_service import (
        db_query_pasthours, db_query_predhours, db_query_max_predhour,
        db_query_last_predhour, calculate_probabilities, calculate_prediction_intervals,
        stations_dict, get_last_available_date, moving_average_probabilities, probability_2pass_threshold,
        initialize_postgres_system
    )
    POSTGRES_AVAILABLE = True
    print("✅ Sistema PostgreSQL de producción disponible")
except ImportError as e:
    POSTGRES_AVAILABLE = False
    print(f"⚠️ Sistema PostgreSQL no disponible: {e}")

# Importar servicio SQLite (fallback)
try:
    from sqlite_data_service import get_sqlite_service, close_sqlite_connections
    SQLITE_AVAILABLE = True
    print("✅ Servicio SQLite disponible como fallback")
except ImportError as e:
    SQLITE_AVAILABLE = False
    print(f"⚠️ Servicio SQLite no disponible: {e}")

# Verificar qué sistema usar según configuración
if is_postgresql_mode() and POSTGRES_AVAILABLE:
    print("✅ Usando sistema PostgreSQL de producción")
    # Las funciones ya están importadas del postgres_data_service
    # Desactivar SQLite completamente cuando PostgreSQL esté disponible
    SQLITE_AVAILABLE = False
elif is_sqlite_mode() and SQLITE_AVAILABLE:
    print("⚠️ SQLite solicitado pero PostgreSQL está disponible - usando PostgreSQL")
    # Forzar uso de PostgreSQL incluso si se solicita SQLite
    SQLITE_AVAILABLE = False
    
else:
    print("⚠️ Usando funciones mock básicas - ningún sistema de BD disponible")
    # Fallback con funciones mock básicas si no hay sistemas disponibles
    if not POSTGRES_AVAILABLE:
        stations_dict = {'MER': {'name': 'MER - Merced', 'lat': 19.42461, 'lon': -99.119594}}
        def db_query_pasthours(*args): return pd.DataFrame()
        def db_query_predhours(id_est, end_time_str): return pd.DataFrame()
        def db_query_max_predhour(*args): return pd.DataFrame()
        def db_query_last_predhour(*args): return pd.DataFrame(), datetime.now()
        def calculate_probabilities(df_pred_bd): return [0.0, 0.0, 0.0, 0.0]
        def calculate_prediction_intervals(*args): return ([0]*24, [0]*24)
        def get_last_available_date(): return datetime.now()
        def moving_average_probabilities(*args): return [0.0]
        def probability_2pass_threshold(*args): return 0.0



# Importaciones adicionales para las funciones eficientes
try:
    import plotly.graph_objects as go
    from config import app_config, get_data_mode, get_current_reference_date, is_mock_mode
except ImportError:
    # Fallback básico
    import plotly.graph_objects as go
    app_config = None
    get_data_mode = lambda: None
    get_current_reference_date = lambda: datetime.now()
    is_mock_mode = lambda: True

class AirQualityDataService:
    """
    Servicio centralizado para obtener datos de calidad del aire.
    Puede alternar entre datos mock y datos reales de la base de datos.
    """
    
    def __init__(self, use_mock_data: bool = None):
        """
        Inicializa el servicio de datos.
        
        Args:
            use_mock_data: Si True, usa datos mock. Si False, usa datos reales de PostgreSQL.
                          Si None, usa la configuración del sistema.
        """
        # Usar configuración del sistema si no se especifica
        if use_mock_data is None and app_config is not None:
            config = app_config.get_data_service_config()
            self.use_mock_data = config['use_mock_data']
            self.data_mode = config['data_mode']
            self.mock_reference_date = config['mock_reference_date']
        else:
            self.use_mock_data = use_mock_data if use_mock_data is not None else True
            self.data_mode = None
            self.mock_reference_date = None
            
        self.stations_dict = stations_dict
        
        # Determinar fecha de referencia
        if self.mock_reference_date is None:
            self.mock_reference_date = get_current_reference_date()
        
        # Configuración SQLite (siempre desactivado cuando PostgreSQL esté disponible)
        if is_postgresql_mode() and POSTGRES_AVAILABLE:
            self.sqlite_mode = False
            print(f"✅ Modo PostgreSQL activado - SQLite desactivado")
        else:
            self.sqlite_mode = is_sqlite_mode() if SQLITE_AVAILABLE else False
            if self.sqlite_mode:
                self.sqlite_service = get_sqlite_service()
                print(f"🔄 Modo SQLite activado (PostgreSQL no disponible)")
        
        print(f"🎯 AirQualityDataService inicializado:")
        print(f"   - Modo: {'MOCK' if self.use_mock_data else 'DATOS REALES'}")
        print(f"   - SQLite: {'ACTIVADO' if self.sqlite_mode else 'DESACTIVADO'}")
        if self.data_mode:
            print(f"   - Tipo de mock: {self.data_mode.value}")
        print(f"   - Fecha de referencia: {self.mock_reference_date}")
        print(f"   - Estaciones disponibles: {len(self.stations_dict)}")
        
    def get_all_stations(self) -> Dict[str, Dict[str, Any]]:
        """Obtiene el diccionario completo de estaciones disponibles"""
        return self.stations_dict
    
    def get_last_available_forecast_date(self) -> Optional[str]:
        """Obtiene la fecha del último pronóstico disponible."""
        if self.sqlite_mode and SQLITE_AVAILABLE:
            try:
                return self.sqlite_service.get_last_forecast_date()
            except Exception as e:
                print(f"❌ Error obteniendo última fecha desde SQLite: {e}")
        
        # Fallback a PostgreSQL
        try:
            return get_last_available_date()
        except Exception as e:
            print(f"❌ Error obteniendo última fecha desde PostgreSQL: {e}")
            return None
    
    def get_last_otres_forecast(self, fecha: str, station: str = 'MER') -> Dict[str, Any]:
        """
        Obtiene el último pronóstico de ozono para una estación específica.
        
        Args:
            fecha: Fecha en formato 'YYYY-MM-DD HH:MM:SS'
            station: Código de la estación (por defecto 'MER')
            
        Returns:
            Dict con timestamps, forecast_vector y metadata
        """
        if self.use_mock_data:
            # Determinar qué tipo de mock usar
            if self.data_mode and self.data_mode.value == 'mock_historical':
                # Usar datos reales de la fecha de referencia
                try:
                    reference_date = self.mock_reference_date.strftime('%Y-%m-%d %H:%M:%S')
                    df_pred = db_query_predhours(station, reference_date)
                    
                    if not df_pred.empty:
                        print(f"✅ Usando datos históricos reales de {reference_date} para {station}")
                        # Extraer las 24 horas de pronóstico
                        df_pred['fecha'] = pd.to_datetime(df_pred['fecha'])
                        timestamps = [df_pred['fecha'][0] + pd.Timedelta(hours=i) for i in range(1, 25)]
                        values = df_pred.loc[0, 'hour_p01':'hour_p24'].values
                        
                        return {
                            'forecast_vector': values,
                            'timestamps': timestamps,
                            'metadata': {
                                'station': station,
                                'forecast_date': df_pred['fecha'][0],
                                'data_source': f'Historical_{reference_date}'
                            }
                        }
                    else:
                        print(f"⚠️ No hay datos históricos para {station} en {reference_date}, usando sintéticos")
                        return self._mock_otres_forecast(fecha, station)
                        
                except Exception as e:
                    print(f"❌ Error obteniendo datos históricos: {e}, usando sintéticos")
                    return self._mock_otres_forecast(fecha, station)
            else:
                # Usar datos sintéticos
                return self._mock_otres_forecast(fecha, station)
        
        # Usar datos reales (PostgreSQL o SQLite)
        try:
            fecha_dt = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
            
            # Intentar usar SQLite si está disponible
            if self.sqlite_mode and SQLITE_AVAILABLE:
                print(f"🔄 Usando SQLite para obtener pronóstico de {station}")
                ozone_data = self.sqlite_service.get_ozone_forecast_data(fecha)
                
                if ozone_data and 'data' in ozone_data and not ozone_data['data'].empty:
                    # Filtrar por estación específica
                    station_data = ozone_data['data'][ozone_data['data']['id_est'] == station]
                    
                    if not station_data.empty:
                        # Extraer las 24 horas de pronóstico
                        station_data['fecha'] = pd.to_datetime(station_data['fecha'])
                        timestamps = [station_data['fecha'].iloc[0] + pd.Timedelta(hours=i) for i in range(1, 25)]
                        values = station_data.loc[station_data.index[0], 'hour_p01':'hour_p24'].values
                        
                        print(f"✅ Pronóstico SQLite obtenido para {station}: {len(values)} valores")
                        
                        return {
                            'forecast_vector': values,
                            'timestamps': timestamps,
                            'metadata': {
                                'station': station,
                                'forecast_date': station_data['fecha'].iloc[0],
                                'data_source': 'SQLite'
                            }
                        }
                    else:
                        print(f"⚠️ No hay datos de pronóstico SQLite para {station} en {fecha}")
                else:
                    print(f"⚠️ No hay datos de pronóstico SQLite disponibles para {fecha}")
            
            # Fallback a PostgreSQL
            print(f"🔄 Usando PostgreSQL para obtener pronóstico de {station}")
            df_pred = db_query_predhours(station, fecha)
            
            if df_pred.empty:
                print(f"⚠️ No hay datos de pronóstico para {station} en {fecha}")
                return {'forecast_vector': None, 'timestamps': [], 'metadata': {}}
            
            # Extraer las 24 horas de pronóstico
            df_pred['fecha'] = pd.to_datetime(df_pred['fecha'])
            timestamps = [df_pred['fecha'][0] + pd.Timedelta(hours=i) for i in range(1, 25)]
            values = df_pred.loc[0, 'hour_p01':'hour_p24'].values
            
            print(f"✅ Pronóstico PostgreSQL obtenido para {station}: {len(values)} valores")
            
            return {
                'forecast_vector': values,
                'timestamps': timestamps,
                'metadata': {
                    'station': station,
                    'forecast_date': df_pred['fecha'][0],
                    'data_source': 'PostgreSQL'
                }
            }
            
        except Exception as e:
            print(f"❌ Error obteniendo pronóstico real para {station}: {e}")
            return {'forecast_vector': None, 'timestamps': [], 'metadata': {}}
    
    def get_last_pollutant_forecast(self, fecha: str, pollutant_key: str, station: str = 'MER') -> Dict[str, Any]:
        """
        Obtiene el pronóstico del último contaminante.
        Para contaminantes no-O3, solo hay pronósticos regionales (mean, min, max).
        """
        if pollutant_key == 'O3':
            # Para O3 usar la función específica
            return self.get_last_otres_forecast(fecha, station)
        
        if self.use_mock_data:
            return self._mock_pollutant_forecast(fecha, pollutant_key, station)
        
        # Para otros contaminantes, no hay pronósticos reales por estación
        # Devolver estructura regional mock
        print(f"⚠️ Pronósticos no-O3 no disponibles en datos reales, usando mock para {pollutant_key}")
        return self._mock_pollutant_forecast(fecha, pollutant_key, station)
    
    def get_historical_data(self, pollutant_key: str, start_date: str, end_date: str, station: str = 'MER') -> pd.DataFrame:
        """
        Obtiene datos históricos para un contaminante específico.
        """
        if self.use_mock_data:
            return self._mock_historical_data(pollutant_key, start_date, end_date, station)
        
        # Usar datos reales
        try:
            # Mapear pollutant_key a tabla de base de datos
            pollutant_table_map = {
                'O3': 'cont_otres',
                'PM10': 'cont_pmdiez', 
                'PM2.5': 'cont_pmdoscinco',
                'NO2': 'cont_nodos',
                'CO': 'cont_co',
                'SO2': 'cont_sodos'
            }
            
            table_name = pollutant_table_map.get(pollutant_key, 'cont_otres')
            df = db_query_pasthours(station, start_date, end_date, table_name)
            
            if df.empty:
                print(f"⚠️ No hay datos históricos para {pollutant_key} en {station}")
                return pd.DataFrame()
            
            print(f"✅ Datos históricos reales obtenidos para {pollutant_key} en {station}: {len(df)} registros")
            return df
            
        except Exception as e:
            print(f"❌ Error obteniendo datos históricos reales: {e}")
            return pd.DataFrame()
    
    def get_probabilities_from_otres_forecast(self, fecha: str, station: str = 'MER') -> List[float]:
        """
        Calcula probabilidades de superar umbrales basado en pronóstico de ozono.
        """
        if self.use_mock_data:
            # Determinar qué tipo de mock usar
            if self.data_mode and self.data_mode.value == 'mock_historical':
                # Usar datos reales de la fecha de referencia
                try:
                    reference_date = self.mock_reference_date.strftime('%Y-%m-%d %H:%M:%S')
                    df_pred = db_query_predhours(station, reference_date)
                    
                    if not df_pred.empty:
                        print(f"✅ Usando datos históricos reales de {reference_date} para {station}")
                        probabilities = calculate_probabilities(df_pred)
                        print(f"✅ Probabilidades históricas calculadas para {station}: {probabilities}")
                        return probabilities
                    else:
                        print(f"⚠️ No hay datos históricos en {reference_date} para {station}, usando sintéticos")
                        return [np.random.uniform(0.1, 0.8) for _ in range(4)]
                        
                except Exception as e:
                    print(f"❌ Error obteniendo datos históricos: {e}, usando sintéticos")
                    return [np.random.uniform(0.1, 0.8) for _ in range(4)]
            else:
                # Usar datos sintéticos
                return [np.random.uniform(0.1, 0.8) for _ in range(4)]
        
        # Usar cálculo real
        try:
            df_pred = db_query_predhours(station, fecha)
            if df_pred.empty:
                print(f"⚠️ No hay pronóstico para calcular probabilidades en {station}")
                return [0.0, 0.0, 0.0, 0.0]
            
            probabilities = calculate_probabilities(df_pred)
            print(f"✅ Probabilidades reales calculadas para {station}: {probabilities}")
            return probabilities
            
        except Exception as e:
            print(f"❌ Error calculando probabilidades reales: {e}")
            return [0.0, 0.0, 0.0, 0.0]
    
    def compute_max_otres_daily_24h(self, fecha: str) -> pd.DataFrame:
        """
        Calcula los valores máximos de ozono predichos en las próximas 24h para todas las estaciones.
        """
        if self.use_mock_data:
            # Determinar qué tipo de mock usar
            if self.data_mode and self.data_mode.value == 'mock_historical':
                # Usar datos reales de la fecha de referencia
                try:
                    reference_date = self.mock_reference_date.strftime('%Y-%m-%d %H:%M:%S')
                    df_max = db_query_max_predhour(reference_date)
                    
                    if not df_max.empty:
                        print(f"✅ Usando datos máximos históricos reales de {reference_date}")
                        return df_max
                    else:
                        print(f"⚠️ No hay datos máximos históricos en {reference_date}, usando sintéticos")
                        return self._mock_max_values_map(fecha)
                        
                except Exception as e:
                    print(f"❌ Error obteniendo datos máximos históricos: {e}, usando sintéticos")
                    return self._mock_max_values_map(fecha)
            else:
                # Usar datos sintéticos
                return self._mock_max_values_map(fecha)
        
        # Usar SQLite si está activado, sino PostgreSQL
        if self.sqlite_mode and SQLITE_AVAILABLE:
            print(f"🔄 Usando SQLite para calcular máximos de ozono")
            try:
                # Obtener pronósticos batch de SQLite
                batch_forecasts = self.get_all_stations_forecast_batch(fecha)
                
                if not batch_forecasts:
                    print(f"⚠️ No hay pronósticos batch para calcular máximos")
                    return pd.DataFrame()
                
                # Calcular máximos para cada estación
                data = {
                    'id_est': [],
                    'name': [],
                    'lat': [],
                    'lon': [],
                    'max_pred': [],
                }
                
                for station_code, forecast_data in batch_forecasts.items():
                    if 'forecast_vector' in forecast_data:
                        # Calcular máximo de las próximas 24 horas
                        max_value = max(forecast_data['forecast_vector'])
                        
                        # Obtener información de la estación
                        station_info = self.stations_dict.get(station_code, {})
                        
                        data['id_est'].append(station_code)
                        data['name'].append(station_info.get('name', station_code))
                        data['lat'].append(station_info.get('lat', 0.0))
                        data['lon'].append(station_info.get('lon', 0.0))
                        data['max_pred'].append(max_value)
                
                df_max = pd.DataFrame(data)
                print(f"✅ Máximos calculados desde SQLite: {len(df_max)} estaciones")
                return df_max
                
            except Exception as e:
                print(f"❌ Error calculando máximos desde SQLite: {e}")
                return pd.DataFrame()
        else:
            # Usar PostgreSQL
            try:
                df_max = db_query_max_predhour(fecha)
                if df_max.empty:
                    print(f"⚠️ No hay datos máximos para el mapa en {fecha}")
                    return pd.DataFrame()
                
                print(f"✅ Valores máximos reales obtenidos: {len(df_max)} estaciones")
                return df_max
                
            except Exception as e:
                print(f"❌ Error obteniendo valores máximos reales: {e}")
                return pd.DataFrame()
    
    def get_prediction_intervals(self, values_pred: np.ndarray, station: str, pollutant: str) -> Optional[List[Dict]]:
        """
        Calcula intervalos de predicción para un pronóstico.
        """
        if self.use_mock_data:
            # Mock intervals
            return [{'plus': np.random.uniform(5, 15), 'minus': np.random.uniform(-15, -5)} 
                   for _ in range(len(values_pred))]
        
        # Usar cálculo real solo para O3
        if pollutant != 'O3':
            return None
            
        try:
            # Necesitamos cargar el DataFrame de errores para los intervalos
            # Por ahora devolver None ya que no tenemos acceso directo al results_errd_df
            print(f"⚠️ Intervalos de predicción reales requieren results_errd_df")
            return None
            
        except Exception as e:
            print(f"❌ Error calculando intervalos de predicción: {e}")
            return None

    # =====================================
    # FUNCIONES DE UTILIDAD
    # =====================================
    
    def get_station_info(self, station_code: str) -> Dict:
        """Obtiene información de una estación"""
        return self.stations_dict.get(station_code, {})
    
    def get_pollutant_info(self, pollutant_key: str) -> Dict:
        """Obtiene información de un contaminante"""
        # Configuración de contaminantes (mock)
        return {
            'O3': {'units': 'ppb', 'db_key': 'cont_otres'},
            'PM2.5': {'units': 'µg/m³', 'db_key': 'cont_pmdoscinco'},
            'PM10': {'units': 'µg/m³', 'db_key': 'cont_pmdiez'},
            'NO2': {'units': 'ppb', 'db_key': 'cont_nodos'},
            'NOx': {'units': 'ppb', 'db_key': 'cont_nox'},
            'CO': {'units': 'ppm', 'db_key': 'cont_co'},
            'SO2': {'units': 'ppb', 'db_key': 'cont_so2'}
        }.get(pollutant_key, {})
    
    def validate_datetime(self, fecha: str) -> bool:
        """Valida formato de fecha"""
        try:
            datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
            return True
        except ValueError:
            return False

    # =====================================
    # FUNCIONES MOCK PARA DESARROLLO
    # =====================================
    
    def _mock_otres_forecast(self, fecha: str, station: str = None) -> Dict:
        """Genera datos mock de pronóstico de ozono"""
        target_stations = [station] if station else (list(self.stations_dict.keys()))
        
        results = {}
        for st in target_stations:
            # Generar pronóstico realista de 24 horas
            base_value = np.random.normal(50, 20)
            # Patrón diurno: máximo a mediodía, mínimo en la madrugada
            hourly_pattern = 30 * np.sin(np.arange(24) * np.pi / 12 + np.pi/4)
            noise = np.random.normal(0, 10, 24)
            forecast_vector = np.maximum(0, base_value + hourly_pattern + noise)
            
            timestamp_base = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
            timestamps = [timestamp_base + timedelta(hours=i) for i in range(1, 25)]
            
            results[st] = {
                'station': st,
                'fecha': fecha,
                'forecast_vector': forecast_vector,
                'timestamps': timestamps,
                'timestamp_strings': [ts.strftime('%Y-%m-%d %H:%M:%S') for ts in timestamps],
                'pollutant': 'O3',
                'units': 'ppb'
            }
        
        return results[target_stations[0]] if len(target_stations) == 1 else results
    
    def _mock_pollutant_forecast(self, fecha: str, pollutant_key: str, 
                                station: str = None, stations: List[str] = None) -> Dict:
        """
        Genera datos mock de pronóstico de otros contaminantes
        ESTRUCTURA REAL: mean, min, max para pronóstico regional (no por estación)
        """
        # Valores base según contaminante
        base_values = {
            'PM2.5': 25, 'PM10': 45, 'NO2': 30, 'NOx': 45, 'CO': 2.5, 'SO2': 20
        }
        
        base_value = base_values.get(pollutant_key, 30)
        
        # IMPORTANTE: Usar seed basado en fecha+contaminante para consistencia regional
        seed_str = f"{fecha}_{pollutant_key}"
        np.random.seed(hash(seed_str) % (2**32 - 1))
        
        # Variación diaria más suave para PM
        if pollutant_key.startswith('PM'):
            daily_pattern = 10 * np.sin(np.arange(24) * np.pi / 12)
        else:
            daily_pattern = 15 * np.sin(np.arange(24) * np.pi / 12)
        
        # Generar las tres series: mean, min, max (IDÉNTICAS para todas las estaciones)
        mean_values = np.maximum(0, base_value + daily_pattern + np.random.normal(0, base_value * 0.15, 24))
        min_values = np.maximum(0, mean_values - np.random.uniform(5, 15, 24))  # Menor que mean
        max_values = mean_values + np.random.uniform(10, 25, 24)  # Mayor que mean
        
        # Resetear seed para evitar afectar otros random calls
        np.random.seed(None)
        
        timestamp_base = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
        timestamps = [timestamp_base + timedelta(hours=i) for i in range(1, 25)]
        
        # Estructura que refleja la realidad: mean, min, max (NO por estación)
        result = {
            'contaminante': 'cont',
            'tipo': 'cont', # Mock, no hay db_key
            'fecha': fecha,
            'pollutant': pollutant_key,
            'subtypes': {
                'mean': mean_values,
                'min': min_values, 
                'max': max_values
            },
            'timestamps': timestamps,
            'timestamp_strings': [ts.strftime('%Y-%m-%d %H:%M:%S') for ts in timestamps],
            'units': 'units', # Mock, no hay units en mock
            'is_regional': True,  # Indica que es pronóstico regional, no por estación
            'note': 'Pronóstico regional con mean/min/max - NO por estación individual'
        }
        
        return result
    
    def _mock_historical_data(self, pollutant_key: str, start_time: str, end_time: str,
                             station: str = None, stations: List[str] = None) -> pd.DataFrame:
        """Genera datos históricos mock"""
        target_stations = [station] if station else (list(self.stations_dict.keys()))
        
        start = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        end = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S')
        hours = int((end - start).total_seconds() / 3600)
        
        data = []
        for st in target_stations:
            station_name = self.stations_dict.get(st, {}).get('name', st)
            base_value = np.random.normal(40 if pollutant_key == 'O3' else 30, 15)
            
            for i in range(hours):
                ts = start + timedelta(hours=i)
                
                # Patrón diurno
                if pollutant_key == 'O3':
                    daily_pattern = 20 * np.sin(i * np.pi / 12)
                elif pollutant_key.startswith('PM'):
                    daily_pattern = 8 * np.sin(i * np.pi / 12)
                else:
                    daily_pattern = 10 * np.sin(i * np.pi / 12)
                
                value = max(0, base_value + daily_pattern + np.random.normal(0, 8))
                
                data.append({
                    'fecha': ts,
                    'station': st,
                    'station_name': station_name,
                    'val': value,
                    'pollutant': pollutant_key,
                    'is_forecast': False
                })
        
        return pd.DataFrame(data)
    
    def _mock_probabilities(self, forecast_vector: np.ndarray) -> List[float]:
        """Calcula probabilidades mock basadas en el vector de pronóstico"""
        if len(forecast_vector) == 0:
            return [0.0, 0.0, 0.0, 0.0]
            
        max_val = np.max(forecast_vector)
        avg_8h = np.mean(forecast_vector[:8])  # Primeras 8 horas
        
        # Probabilidades basadas en valores del pronóstico
        prob_50_8h = min(0.95, max(0.05, (avg_8h - 40) / 50))
        prob_90 = min(0.95, max(0.05, (max_val - 70) / 80))
        prob_120 = min(0.95, max(0.05, (max_val - 100) / 100))
        prob_150 = min(0.95, max(0.05, (max_val - 130) / 120))
        
        return [prob_50_8h, prob_90, prob_120, prob_150]
    
    def _mock_prediction_intervals(self, forecast_vector: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Genera intervalos de predicción mock"""
        # Intervalos proporcionales al valor del pronóstico
        uncertainty = forecast_vector * 0.2  # 20% de incertidumbre
        upper_bound = uncertainty
        lower_bound = -uncertainty
        
        return upper_bound, lower_bound
    
    def _mock_max_values_map(self, fecha: str) -> pd.DataFrame:
        """Genera datos mock para el mapa de valores máximos de todas las estaciones"""
        data = []
        
        for station_code, station_info in self.stations_dict.items():
            # Generar valor máximo realista para cada estación
            base_value = np.random.normal(60, 25)  # Valor base entre 35-85 ppb
            max_value = max(0, base_value + np.random.normal(0, 15))  # Agregar variabilidad
            
            data.append({
                'id_est': station_code,
                'name': station_info.get('name', f'Estación {station_code}'),
                'lat': station_info.get('lat', 19.4326),  # Coordenadas por defecto (CDMX)
                'lon': station_info.get('lon', -99.1332),
                'max_pred': max_value,
                'fecha': fecha
            })
        
        df = pd.DataFrame(data)
        print(f"✅ Datos mock generados para mapa: {len(df)} estaciones")
        return df

    # =====================================
    # FUNCIONES PARA MIGRAR A DATOS REALES
    # =====================================
    
    def _process_real_otres_forecast(self, df_raw) -> Dict:
        """Procesa datos reales de BD para ozono"""
        # TODO: Implementar cuando tengas acceso a datos reales
        pass
    
    def _process_real_pollutant_forecast(self, df_raw, pollutant_key: str) -> Dict:
        """Procesa datos reales de BD para otros contaminantes"""
        # TODO: Implementar cuando tengas acceso a datos reales
        pass

    # =====================================
    # MÉTODOS PARA MIGRAR A DATOS REALES
    # =====================================
    
    def switch_to_real_data(self):
        """Cambia a usar datos reales en lugar de mock"""
        self.use_mock_data = False
        print("✅ Cambiado a modo de datos reales")
        print("🔧 Asegúrate de que todas las funciones de BD estén disponibles")
        
    def switch_to_mock_data(self):
        """Vuelve a usar datos mock"""
        self.use_mock_data = True
        print("✅ Cambiado a modo de datos mock para desarrollo")
    
    def close_sqlite_connections(self):
        """Cierra las conexiones SQLite si están activas."""
        if self.sqlite_mode and hasattr(self, 'sqlite_service'):
            try:
                self.sqlite_service.close_connections()
                print("🔌 Conexiones SQLite cerradas")
            except Exception as e:
                print(f"⚠️ Error cerrando conexiones SQLite: {e}")
    
    def __del__(self):
        """Destructor para limpiar conexiones."""
        # Comentado para evitar cerrar conexiones prematuramente
        # self.close_sqlite_connections()


# =====================================
# FUNCIONES DE CONVENIENCIA GLOBALES
# =====================================

# =====================================
# CAMBIO DE FUNCIÓN PULLING DATA: INEFICIENTE → EFICIENTE  
# =====================================
# 
# COMENTARIO: Aquí es donde se cambia de una función de pulling data a otra
#
# ANTES (INEFICIENTE): AirQualityDataService 
# - Serie temporal O3: ~60 queries SQL individuales
# - get_historical_data() llamado 30 veces
# - get_last_otres_forecast() llamado 30 veces
# 
# DESPUÉS (EFICIENTE): EfficientAirQualityDataService
# - Serie temporal O3: ~3 queries SQL batch
# - get_all_stations_historical_batch() llamado 1 vez
# - get_all_stations_forecast_batch() llamado 1 vez
# - Reducción del 95% en carga de base de datos
# =====================================

# NOTA: La instancia global y funciones de conveniencia se crean al final del archivo


# =====================================
# EJEMPLO DE USO
# =====================================

if __name__ == "__main__":
    # Ejemplo de uso durante desarrollo - USANDO DATOS REALES
    service = AirQualityDataService(use_mock_data=False)
    
    fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print("=== EJEMPLO DE USO DEL SERVICIO DE DATOS ===")
    
    # Obtener pronóstico de ozono para una estación
    print("\n1. Pronóstico de ozono para MER:")
    ozono_forecast = service.get_last_otres_forecast(fecha_actual, station='MER')
    print(f"   - Vector (primeros 5): {ozono_forecast['forecast_vector'][:5]}")
    print(f"   - Unidades: {ozono_forecast['units']}")
    
    # Calcular probabilidades
    print("\n2. Probabilidades de superar umbrales:")
    probabilities = service.get_probabilities_from_otres_forecast(ozono_forecast['forecast_vector'])
    labels = ["50ppb-8h", "90ppb", "120ppb", "150ppb"]
    for label, prob in zip(labels, probabilities):
        print(f"   - {label}: {prob*100:.1f}%")
    
    # Obtener pronóstico de PM2.5
    print("\n3. Pronóstico de PM2.5 para MER:")
    pm25_forecast = service.get_last_pollutant_forecast('PM2.5', fecha_actual, station='MER')
    print(f"   - Vector (primeros 5): {pm25_forecast['forecast_vector'][:5]}")
    print(f"   - Unidades: {pm25_forecast['units']}")
    
    # Obtener datos para el mapa
    print("\n4. Datos para mapa (máximos 24h):")
    mapa_data = service.compute_all_stations_max_24h(fecha_actual)
    print(f"   - Estaciones: {len(mapa_data)} registros")
    print(f"   - Columnas: {list(mapa_data.columns)}")
    if not mapa_data.empty:
        print(f"   - Rango de valores: {mapa_data['max_pred'].min():.1f} - {mapa_data['max_pred'].max():.1f} ppb")
    
    print("\n=== LISTO PARA USAR EN DASH ===")
    print("Importa las funciones en tu app:")
    print("from data_service import get_last_otres_forecast, compute_all_stations_max_24h") 

# =====================================
# NUEVAS FUNCIONES EFICIENTES DE PULLING DATA
# =====================================

class EfficientAirQualityDataService(AirQualityDataService):
    """
    Versión optimizada del servicio de datos que reduce significativamente
    el número de queries SQL mediante batch queries y procesamiento inteligente.
    
    PROBLEMA ORIGINAL: 
    - Serie temporal O3: ~60 queries (30 estaciones × 2 queries c/u)
    - Cada estación requiere query histórico + query pronóstico individual
    
    SOLUCIÓN OPTIMIZADA:
    - Serie temporal O3: ~2-3 queries total (1 histórico batch + 1 pronóstico batch + 1 máximos)
    - Reducción de 60→3 queries = 95% menos carga en BD
    """
    
    def __init__(self, use_mock_data: bool = False):
        super().__init__(use_mock_data)
        print(f"🚀 EfficientAirQualityDataService inicializado (modo: {'MOCK' if use_mock_data else 'EFICIENTE REAL'})")
    
    def get_all_stations_historical_batch(self, pollutant_key: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        NUEVA FUNCIÓN EFICIENTE: Obtiene datos históricos de TODAS las estaciones en UN SOLO QUERY.
        
        Reemplaza: 30 calls individuales a get_historical_data()
        Por: 1 call batch que trae todo
        
        Returns:
            DataFrame con columnas: ['fecha', 'val', 'id_est', 'timestamp', 'value']
        """
        if self.use_mock_data:
            # Determinar qué tipo de mock usar
            if self.data_mode and self.data_mode.value == 'mock_historical':
                # Usar datos reales de la fecha de referencia
                try:
                    reference_date = self.mock_reference_date.strftime('%Y-%m-%d %H:%M:%S')
                    # Ajustar las fechas para usar la fecha de referencia
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
                    hours_diff = int((end_dt - start_dt).total_seconds() / 3600)
                    
                    # Calcular fechas relativas a la fecha de referencia
                    ref_start = self.mock_reference_date - timedelta(hours=hours_diff)
                    ref_end = self.mock_reference_date
                    
                    ref_start_str = ref_start.strftime('%Y-%m-%d %H:%M:%S')
                    ref_end_str = ref_end.strftime('%Y-%m-%d %H:%M:%S')
                    
                    print(f"✅ Usando datos históricos reales de {ref_start_str} a {ref_end_str}")
                    
                    # Mapear pollutant_key a tabla de base de datos
                    pollutant_table_map = {
                        'O3': 'cont_otres',
                        'PM10': 'cont_pmdiez', 
                        'PM2.5': 'cont_pmdoscinco',
                        'NO2': 'cont_nodos',
                        'CO': 'cont_co',
                        'SO2': 'cont_sodos'
                    }
                    
                    table_name = pollutant_table_map.get(pollutant_key, 'cont_otres')
                    
                    # QUERY OPTIMIZADO: Traer todas las estaciones de una vez
                    stations_list = list(self.stations_dict.keys())
                    stations_str = "','".join(stations_list)
                    
                    efficient_query = f"""
                        SELECT fecha, val, id_est 
                        FROM {table_name}
                        WHERE fecha BETWEEN '{ref_start_str}' AND '{ref_end_str}'
                        AND id_est IN ('{stations_str}')
                        ORDER BY id_est, fecha;
                    """
                    
                    print(f"🔥 QUERY EFICIENTE HISTÓRICO ({pollutant_key}): 1 query para {len(stations_list)} estaciones")
                    print(f"   Tabla: {table_name}, Período: {ref_start_str} → {ref_end_str}")
                    
                    # Usar PostgreSQL actual (132.248.8.152) para datos históricos
                    try:
                        from postgres_data_service import ForecastDataService
                        postgres_service = ForecastDataService()
                        try:
                            df_batch = postgres_service.connection.execute_query(efficient_query)
                        finally:
                            postgres_service.close()
                            
                    except Exception as e:
                        print(f"❌ Error obteniendo datos históricos reales desde PostgreSQL actual: {e}")
                        df_batch = pd.DataFrame()
                    
                    if not df_batch.empty:
                        # Normalizar columnas para compatibilidad
                        df_batch = df_batch.rename(columns={'fecha': 'timestamp', 'val': 'value'})
                        df_batch['fecha'] = df_batch['timestamp']  # Mantener ambas por compatibilidad
                        df_batch['val'] = df_batch['value']
                        
                        print(f"✅ Datos históricos batch reales: {len(df_batch)} registros de {len(df_batch['id_est'].unique())} estaciones")
                        return df_batch
                    else:
                        print(f"⚠️ No hay datos históricos reales en {ref_start_str} a {ref_end_str}, usando sintéticos")
                        return self._mock_all_stations_historical_batch(pollutant_key, start_date, end_date)
                        
                except Exception as e:
                    print(f"❌ Error obteniendo datos históricos batch reales: {e}, usando sintéticos")
                    return self._mock_all_stations_historical_batch(pollutant_key, start_date, end_date)
            else:
                # Usar datos sintéticos
                return self._mock_all_stations_historical_batch(pollutant_key, start_date, end_date)
        
        try:
            # Mapear pollutant_key a tabla de base de datos
            pollutant_table_map = {
                'O3': 'cont_otres',
                'PM10': 'cont_pmdiez', 
                'PM2.5': 'cont_pmdoscinco',
                'NO2': 'cont_nodos',
                'CO': 'cont_co',
                'SO2': 'cont_sodos'
            }
            
            table_name = pollutant_table_map.get(pollutant_key, 'cont_otres')
            
            # QUERY OPTIMIZADO: Traer todas las estaciones de una vez
            stations_list = list(self.stations_dict.keys())
            stations_str = "','".join(stations_list)
            
            efficient_query = f"""
                SELECT fecha, val, id_est 
                FROM {table_name}
                WHERE fecha BETWEEN '{start_date}' AND '{end_date}'
                AND id_est IN ('{stations_str}')
                ORDER BY id_est, fecha;
            """
            
            print(f"🔥 QUERY EFICIENTE ({pollutant_key}): 1 query para {len(stations_list)} estaciones")
            print(f"   Tabla: {table_name}, Período: {start_date} → {end_date}")
            
            # Usar SQLite si está activado, sino PostgreSQL
            if self.sqlite_mode and SQLITE_AVAILABLE:
                print(f"🔄 Usando SQLite para datos históricos batch")
                try:
                    df_batch = self.sqlite_service.historical_service.get_historical_data(
                        table_name, start_date, end_date, stations_list
                    )
                except Exception as e:
                    print(f"❌ Error obteniendo datos históricos desde SQLite: {e}")
                    return pd.DataFrame()
            else:
                # Usar PostgreSQL actual (132.248.8.152) para datos históricos
                print(f"🔄 Usando PostgreSQL actual para datos históricos batch")
                try:
                    from postgres_data_service import ForecastDataService
                    postgres_service = ForecastDataService()
                    try:
                        df_batch = postgres_service.connection.execute_query(efficient_query)
                    finally:
                        postgres_service.close()
                        
                except Exception as e:
                    print(f"❌ Error obteniendo datos históricos desde PostgreSQL actual: {e}")
                    df_batch = pd.DataFrame()
            
            if df_batch.empty:
                print(f"⚠️ No hay datos históricos batch para {pollutant_key}")
                return pd.DataFrame()
            
            # Verificar y corregir columnas para compatibilidad
            print(f"🔍 Columnas disponibles: {list(df_batch.columns)}")
            
            # Normalizar columnas para compatibilidad
            if 'fecha' in df_batch.columns:
                df_batch = df_batch.rename(columns={'fecha': 'timestamp'})
            if 'val' in df_batch.columns:
                df_batch = df_batch.rename(columns={'val': 'value'})
            
            # Asegurar que tenemos las columnas necesarias
            df_batch['fecha'] = df_batch['timestamp']  # Mantener ambas por compatibilidad
            df_batch['val'] = df_batch['value']
            
            # Verificar que id_est esté presente
            if 'id_est' not in df_batch.columns:
                print(f"❌ ERROR: Columna 'id_est' no encontrada en datos históricos")
                print(f"   Columnas disponibles: {list(df_batch.columns)}")
                return pd.DataFrame()
            
            print(f"✅ Datos históricos batch: {len(df_batch)} registros de {len(df_batch['id_est'].unique())} estaciones")
            return df_batch
            
        except Exception as e:
            print(f"❌ Error en query histórico batch: {e}")
            return pd.DataFrame()
    
    def get_all_stations_forecast_batch(self, fecha: str) -> Dict[str, Any]:
        """
        NUEVA FUNCIÓN EFICIENTE: Obtiene pronósticos de TODAS las estaciones en UN SOLO QUERY.
        
        Reemplaza: 30 calls individuales a get_last_otres_forecast()  
        Por: 1 call batch que trae todo
        
        Returns:
            Dict con estructura: {
                'station_code': {
                    'forecast_vector': [...], 
                    'timestamps': [...], 
                    'metadata': {...}
                }, ...
            }
        """
        if self.use_mock_data:
            # Determinar qué tipo de mock usar
            if self.data_mode and self.data_mode.value == 'mock_historical':
                # Usar datos reales de la fecha de referencia
                try:
                    reference_date = self.mock_reference_date.strftime('%Y-%m-%d %H:%M:%S')
                    print(f"✅ Usando pronósticos reales de {reference_date}")
                    
                    # QUERY OPTIMIZADO: Traer todos los pronósticos de todas las estaciones
                    stations_list = list(self.stations_dict.keys())
                    stations_str = "','".join(stations_list)
                    
                    columnas_hp = ', '.join([f'hour_p{str(i).zfill(2)}' for i in range(1, 25)])
                    
                    efficient_query = f"""
                        SELECT fecha, id_est, {columnas_hp} 
                        FROM forecast_otres 
                        WHERE fecha BETWEEN '{reference_date}' AND '{reference_date}'
                        AND id_tipo_pronostico = 7  
                        AND id_est IN ('{stations_str}')
                        ORDER BY id_est;
                    """
                    # ✅ CORRECTO - busca datos nuevos
                    print(f"🔥 QUERY EFICIENTE (Pronósticos O3 reales): 1 query para {len(stations_list)} estaciones")
                    
                    # Usar PostgreSQL actual (132.248.8.152) para pronósticos
                    try:
                        from postgres_data_service import ForecastDataService
                        postgres_service = ForecastDataService()
                        try:
                            df_batch = postgres_service.connection.execute_query(efficient_query)
                        finally:
                            postgres_service.close()
                    except Exception as e:
                        print(f"❌ Error obteniendo pronósticos desde PostgreSQL actual: {e}")
                        df_batch = pd.DataFrame()
                    
                    if not df_batch.empty:
                        # Procesar datos reales
                        batch_forecasts = {}
                        for _, row in df_batch.iterrows():
                            station_code = row['id_est']
                            forecast_date = pd.to_datetime(row['fecha'])
                            timestamps = [forecast_date + pd.Timedelta(hours=i) for i in range(1, 25)]
                            forecast_vector = row.loc['hour_p01':'hour_p24'].values
                            
                            batch_forecasts[station_code] = {
                                'forecast_vector': forecast_vector,
                                'timestamps': timestamps,
                                'metadata': {
                                    'station': station_code,
                                    'forecast_date': forecast_date,
                                    'data_source': f'Historical_{reference_date}'
                                }
                            }
                        
                        print(f"✅ Pronósticos batch reales: {len(batch_forecasts)} estaciones")
                        return batch_forecasts
                    else:
                        print(f"⚠️ No hay pronósticos reales en {reference_date}, usando sintéticos")
                        return self._mock_all_stations_forecast_batch(fecha)
                        
                except Exception as e:
                    print(f"❌ Error obteniendo pronósticos batch reales: {e}, usando sintéticos")
                    return self._mock_all_stations_forecast_batch(fecha)
            else:
                # Usar datos sintéticos
                return self._mock_all_stations_forecast_batch(fecha)
        
        try:
            # QUERY OPTIMIZADO: Traer todos los pronósticos de todas las estaciones
            stations_list = list(self.stations_dict.keys())
            stations_str = "','".join(stations_list)
            
            columnas_hp = ', '.join([f'hour_p{str(i).zfill(2)}' for i in range(1, 25)])
            
            efficient_query = f"""
                SELECT fecha, id_est, {columnas_hp} 
                FROM forecast_otres 
                WHERE fecha BETWEEN '{fecha}' AND '{fecha}'
                AND id_tipo_pronostico = 7
                AND id_est IN ('{stations_str}')
                ORDER BY id_est;
            """
            
            print(f"🔥 QUERY EFICIENTE (Pronósticos O3): 1 query para {len(stations_list)} estaciones")
            
            # Usar SQLite si está activado, sino PostgreSQL
            if self.sqlite_mode and SQLITE_AVAILABLE:
                print(f"🔄 Usando SQLite para pronósticos batch")
                try:
                    df_batch = self.sqlite_service.forecast_service.get_ozone_forecast(fecha)
                except Exception as e:
                    print(f"❌ Error obteniendo pronósticos desde SQLite: {e}")
                    return {}
            else:
                # Usar PostgreSQL actual (132.248.8.152) para pronósticos
                print(f"🔄 Usando PostgreSQL actual para pronósticos batch")
                try:
                    from postgres_data_service import ForecastDataService
                    postgres_service = ForecastDataService()
                    try:
                        df_batch = postgres_service.connection.execute_query(efficient_query)
                    finally:
                        postgres_service.close()
                except Exception as e:
                    print(f"❌ Error obteniendo pronósticos desde PostgreSQL actual: {e}")
                    df_batch = pd.DataFrame()
            
            if df_batch.empty:
                print(f"⚠️ No hay pronósticos batch para fecha {fecha}")
                return {}
            
            # Convertir DataFrame batch a estructura por estaciones
            forecast_batch = {}
            base_date = pd.to_datetime(df_batch['fecha'].iloc[0])
            
            for _, row in df_batch.iterrows():
                station = row['id_est'].strip()
                
                # Extraer vector de 24 horas
                forecast_vector = row.loc['hour_p01':'hour_p24'].values
                
                # Generar timestamps
                timestamps = [base_date + pd.Timedelta(hours=i) for i in range(1, 25)]
                
                forecast_batch[station] = {
                    'forecast_vector': forecast_vector,
                    'timestamps': timestamps,
                    'metadata': {
                        'station': station,
                        'forecast_date': base_date,
                        'data_source': 'PostgreSQL_Batch'
                    }
                }
            
            print(f"✅ Pronósticos batch: {len(forecast_batch)} estaciones procesadas")
            return forecast_batch
            
        except Exception as e:
            print(f"❌ Error en query pronósticos batch: {e}")
            return {}
    
    def create_o3_comprehensive_series_efficient(self, selected_station: str = 'PED') -> go.Figure:
        """
        NUEVA FUNCIÓN EFICIENTE: Crea serie temporal O3 completa con reducción masiva de queries.
        
        ANTES: ~60 queries SQL (30 estaciones × 2 queries c/u)
        DESPUÉS: ~3 queries SQL total
        
        Returns:
            go.Figure con serie temporal completa
        """
        fig = go.Figure()
        
        # Configurar tiempo usando la nueva configuración
        try:
            from config import get_current_reference_date
            now = get_current_reference_date()
            print(f"📊 Serie O3 EFICIENTE usando fecha: {now}")
        except ImportError:
            # Fallback si no hay configuración
            now = datetime.now().replace(minute=0, second=0, microsecond=0)
            print(f"📊 Serie O3 EFICIENTE usando fecha actual: {now}")
        
        num_hours_past = 48
        start_time = now - timedelta(hours=num_hours_past)
        start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_time_str = now.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"⚡ INICIANDO SERIE TEMPORAL EFICIENTE O3 (reducción de ~60→3 queries)")
        
        # 🔥 QUERY 1: Datos históricos de TODAS las estaciones (antes: 30 queries)
        df_all_historical = self.get_all_stations_historical_batch('O3', start_time_str, end_time_str)
        
        # 🔥 QUERY 2: Pronósticos de TODAS las estaciones (antes: 30 queries)  
        all_forecasts_batch = self.get_all_stations_forecast_batch(end_time_str)
        
        # 🔥 QUERY 3: Máximos para mapa (ya eficiente)
        # df_max = self.compute_max_otres_daily_24h(end_time_str)  # Opcional, no necesario aquí
        
        stations_dict = self.get_all_stations()
        
        # PROCESAMIENTO EFICIENTE EN PYTHON (mucho más rápido que 60 queries)
        
        # PASO 1: Agregar todas las estaciones (excepto seleccionada) - procesamiento local
        all_historical_data = []
        all_forecast_data = []
        
        for station_code, station_info in stations_dict.items():
            if station_code == selected_station:
                continue
                
            # Filtrar datos históricos de esta estación (procesamiento local vs query SQL)
            # Verificar que df_all_historical tenga datos y la columna 'id_est'
            if not df_all_historical.empty and 'id_est' in df_all_historical.columns:
                station_historical = df_all_historical[df_all_historical['id_est'] == station_code].copy()
            else:
                station_historical = pd.DataFrame()  # DataFrame vacío si no hay datos históricos
                
            if not station_historical.empty:
                all_historical_data.append(station_historical)
                
                fig.add_trace(
                    go.Scatter(
                        x=station_historical['timestamp'],
                        y=station_historical['value'],
                        mode='lines',
                        name=station_info['name'],
                        line=dict(width=1, color='rgba(200, 200, 200, 0.75)'),  # Gris claro con 75% de opacidad
                        showlegend=False,
                        hovertemplate='<b>%{x}</b><br>%{y:.1f} ppb<extra></extra>'
                    )
                )
            
            # Usar datos de pronóstico del batch (procesamiento local vs query SQL)
            if station_code in all_forecasts_batch:
                forecast_data = all_forecasts_batch[station_code]
                
                all_forecast_data.append(pd.DataFrame({
                    'timestamp': forecast_data['timestamps'],
                    'value': forecast_data['forecast_vector']
                }))
                
                fig.add_trace(
                    go.Scatter(
                        x=forecast_data['timestamps'],
                        y=forecast_data['forecast_vector'],
                        mode='lines',
                        name=f'Pro {station_info["name"]}',
                        line=dict(width=1, color='rgba(15, 92, 207, 0.3)'),  # Azul con 30% de opacidad
                        showlegend=False,
                        hovertemplate='<b>%{x}</b><br>Pronóstico: %{y:.1f} ppb<extra></extra>'
                    )
                )
        
        # PASO 2: Calcular promedios y máximos (procesamiento pandas vs queries múltiples)
        if all_historical_data:
            df_historical = pd.concat(all_historical_data)
            historical_avg = df_historical.groupby('timestamp')['value'].mean().reset_index()
            historical_max = df_historical.groupby('timestamp')['value'].max().reset_index()

            fig.add_trace(
                go.Scatter(
                    x=historical_avg['timestamp'],
                    y=historical_avg['value'],
                    mode='lines',
                    name='Promedio Observaciones',
                    line=dict(width=2, color='green', dash='dash'),
                    showlegend=True,
                    hovertemplate='<b>%{x}</b><br>Promedio: %{y:.1f} ppb<extra></extra>'
                )
            )

            fig.add_trace(
                go.Scatter(
                    x=historical_max['timestamp'],
                    y=historical_max['value'],
                    mode='lines',
                    name='Máximo Observaciones',
                    line=dict(width=2, color='rgba(255, 0, 0, 0.75)', dash='dash'),  # Rojo con 75% de opacidad
                    showlegend=True,
                    hovertemplate='<b>%{x}</b><br>Máximo: %{y:.1f} ppb<extra></extra>'
                )
            )
        
        # PASO 3: Agregar estación seleccionada con datos completos
        selected_station_info = stations_dict.get(selected_station, {})
        
        # Datos históricos de la estación seleccionada
        # Verificar que df_all_historical tenga datos y la columna 'id_est'
        if not df_all_historical.empty and 'id_est' in df_all_historical.columns:
            selected_historical = df_all_historical[df_all_historical['id_est'] == selected_station].copy()
        else:
            selected_historical = pd.DataFrame()  # DataFrame vacío si no hay datos históricos
            
        if not selected_historical.empty:
            fig.add_trace(
                go.Scatter(
                    x=selected_historical['timestamp'],
                    y=selected_historical['value'],
                    mode='lines+markers',
                    name=f'{selected_station_info.get("name", selected_station)} (Observado)',
                    line=dict(width=3, color='blue'),
                    marker=dict(size=6),
                    showlegend=True,
                    hovertemplate='<b>%{x}</b><br>%{y:.1f} ppb<extra></extra>'
                )
            )
        
        # Pronóstico de la estación seleccionada
        if selected_station in all_forecasts_batch:
            selected_forecast = all_forecasts_batch[selected_station]
            fig.add_trace(
                go.Scatter(
                    x=selected_forecast['timestamps'],
                    y=selected_forecast['forecast_vector'],
                    mode='lines+markers',
                    name=f'{selected_station_info.get("name", selected_station)} (Pronóstico)',
                    line=dict(width=3, color='red'),
                    marker=dict(size=6),
                    showlegend=True,
                    hovertemplate='<b>%{x}</b><br>Pronóstico: %{y:.1f} ppb<extra></extra>'
                )
            )
        
        # PASO 4: Configurar layout
        fig.update_layout(
            title=f'Serie Temporal O3 - Estación {selected_station_info.get("name", selected_station)}',
            xaxis_title='Fecha/Hora',
            yaxis_title='O3 (ppb)',
            height=500,
            showlegend=True,
            hovermode='closest'
        )
        
        print(f"✅ Serie temporal O3 EFICIENTE completada: {len(fig.data)} trazas")
        return fig
    
    # Funciones mock para testing/desarrollo
    def _mock_all_stations_historical_batch(self, pollutant_key: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Mock de datos históricos batch para todas las estaciones"""
        stations_list = list(self.stations_dict.keys())
        mock_data = []
        
        start_dt = datetime.strptime(start_date, '%Y-%m-%d %H:%M:%S')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
        
        current = start_dt
        while current <= end_dt:
            for station in stations_list:
                mock_data.append({
                    'timestamp': current,
                    'value': np.random.uniform(10, 150),
                    'id_est': station,
                    'fecha': current,
                    'val': np.random.uniform(10, 150)
                })
            current += timedelta(hours=1)
        
        return pd.DataFrame(mock_data)
    
    def _mock_all_stations_forecast_batch(self, fecha: str) -> Dict[str, Any]:
        """Mock de pronósticos batch para todas las estaciones"""
        stations_list = list(self.stations_dict.keys())
        base_date = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S')
        
        batch_forecasts = {}
        for station in stations_list:
            timestamps = [base_date + timedelta(hours=i) for i in range(1, 25)]
            forecast_vector = np.random.uniform(20, 180, 24).tolist()
            
            batch_forecasts[station] = {
                'forecast_vector': forecast_vector,
                'timestamps': timestamps,
                'metadata': {
                    'station': station,
                    'forecast_date': base_date,
                    'data_source': 'Mock_Batch'
                }
            }
        
        return batch_forecasts 


# =====================================
# INSTANCIA GLOBAL EFICIENTE Y FUNCIONES DE CONVENIENCIA
# =====================================
# 
# COMENTARIO: Aquí es donde se cambia de una función de pulling data a otra
#
# ANTES (INEFICIENTE): AirQualityDataService 
# - Serie temporal O3: ~60 queries SQL individuales
# - get_historical_data() llamado 30 veces
# - get_last_otres_forecast() llamado 30 veces
# 
# DESPUÉS (EFICIENTE): EfficientAirQualityDataService
# - Serie temporal O3: ~3 queries SQL batch
# - get_all_stations_historical_batch() llamado 1 vez
# - get_all_stations_forecast_batch() llamado 1 vez
# - Reducción del 95% en carga de base de datos
# =====================================

# Instancia global EFICIENTE - USANDO CONFIGURACIÓN DEL SISTEMA
# Se crea al final del archivo para evitar errores de métodos no definidos
data_service = None

def _initialize_data_service():
    """Inicializa la instancia global del servicio de datos"""
    global data_service
    data_service = EfficientAirQualityDataService(use_mock_data=None)  # None = usar configuración del sistema
    print("✅ Instancia global del servicio de datos inicializada")

def cleanup_data_service():
    """Limpia el servicio de datos global y cierra conexiones."""
    global data_service
    
    if data_service is not None:
        # Comentado para evitar cerrar conexiones prematuramente
        # data_service.close_sqlite_connections()
        data_service = None
        print("🧹 Servicio de datos global limpiado")
    
    # Comentado para evitar cerrar conexiones prematuramente
    # if SQLITE_AVAILABLE:
    #     close_sqlite_connections()

# Inicializar la instancia global
_initialize_data_service()

# Comentario: Para volver al approach anterior (ineficiente), descomenta la línea de abajo:
# data_service = AirQualityDataService(use_mock_data=None)

# Funciones de conveniencia que mapean a los métodos de la clase
def get_last_otres_forecast(fecha: str, station: str = None) -> Dict:
    """Función de conveniencia para obtener pronóstico de ozono"""
    return data_service.get_last_otres_forecast(fecha, station)

def get_last_pollutant_forecast(pollutant_key: str, fecha: str, 
                               station: str = None) -> Dict:
    """Función de conveniencia para obtener pronóstico de contaminante"""
    return data_service.get_last_pollutant_forecast(fecha, pollutant_key, station)

def get_historical_data(pollutant_key: str, start_time: str, end_time: str,
                       station: str = None) -> pd.DataFrame:
    """Función de conveniencia para obtener datos históricos"""
    return data_service.get_historical_data(pollutant_key, start_time, end_time, station)

def get_probabilities_from_otres_forecast(fecha: str, station: str = 'MER') -> List[float]:
    """Función de conveniencia para calcular probabilidades"""
    return data_service.get_probabilities_from_otres_forecast(fecha, station)

def compute_max_otres_daily_24h(forecast_vector: np.ndarray) -> float:
    """Función de conveniencia para calcular máximo de 24h"""
    return data_service.compute_max_otres_daily_24h(forecast_vector)

def compute_all_stations_max_24h(fecha: str) -> pd.DataFrame:
    """Función de conveniencia para obtener datos del mapa"""
    return data_service.compute_max_otres_daily_24h(fecha)

def compute_prediction_intervals(forecast_vector: np.ndarray, station: str, pollutant: str = 'O3') -> Optional[List[Dict]]:
    """Función de conveniencia para intervalos de predicción"""
    return data_service.get_prediction_intervals(forecast_vector, station, pollutant) 

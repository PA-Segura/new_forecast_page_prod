"""
Módulo de callbacks para la aplicación de pronóstico de calidad del aire.
Organiza todos los callbacks por funcionalidad y página.
"""

from dash import Output, Input, callback, dcc
from typing import Any

from visualization import create_time_series, create_indicators
from config import config_manager
from components import indicator_components
from pages import get_forecast_datetime_str


class HomePageCallbacks:
    """Callbacks específicos para la página principal"""
    
    @staticmethod
    def register_home_callbacks(app):
        """Registra todos los callbacks de la página principal"""
        
        @app.callback(
            Output("o3-timeseries-home", "figure"),
            Input("station-dropdown-home", "value")
        )
        def update_o3_timeseries_home(station):
            if station is None:
                station = 'MER'
            return create_time_series('O3', station)
        
        
        @app.callback(
            Output("indicators-container", "children"),
            Input("station-dropdown-home", "value")
        )
        def update_indicators_home(station):
            if station is None:
                station = 'MER'
            indicators = create_indicators(station)
            return indicator_components.wrap_indicators_in_columns(indicators)
        
        @app.callback(
            Output("o3-title", "children"),
            Input("station-dropdown-home", "value")
        )
        def update_o3_title(station):
            """Actualiza el título del pronóstico de ozono cuando cambia la estación"""
            print(f"🔄 CALLBACK EJECUTADO - Estación: {station}")
            
            if station is None:
                station = 'MER'
            
            # Obtener la hora del último pronóstico menos 1 hora
            from datetime import datetime, timedelta
            from postgres_data_service import get_last_available_date
            
            try:
                # Obtener la fecha del último pronóstico
                forecast_datetime = get_last_available_date()
                
                if forecast_datetime:
                    # Restar 1 hora al último pronóstico
                    adjusted_datetime = forecast_datetime - timedelta(hours=1)
                    hour_str = adjusted_datetime.strftime('%H:%M')
                    print(f"✅ Usando hora del último pronóstico menos 1h: {hour_str}")
                else:
                    # Fallback: usar hora actual menos 1 hora
                    adjusted_datetime = datetime.now() - timedelta(hours=1)
                    hour_str = adjusted_datetime.strftime('%H:%M')
                    print(f"⚠️ Fallback: usando hora actual menos 1h: {hour_str}")
                    
            except Exception as e:
                print(f"❌ Error obteniendo fecha del pronóstico: {e}")
                # Fallback: usar hora actual menos 1 hora
                adjusted_datetime = datetime.now() - timedelta(hours=1)
                hour_str = adjusted_datetime.strftime('%H:%M')
                print(f"⚠️ Error fallback: usando hora actual menos 1h: {hour_str}")
            
            title = f'Concentraciones de Ozono (ppb) - a las {hour_str} hrs.'
            print(f"✅ Título generado: {title}")
            
            return title


class OtrosContaminantesCallbacks:
    """Callbacks específicos para la página de otros contaminantes"""
    
    @staticmethod
    def register_otros_contaminantes_callbacks(app):
        """Registra todos los callbacks de otros contaminantes"""
        
        @app.callback(
            Output("pm25-timeseries-otros", "figure"),
            Input("station-dropdown-otros", "value")
        )
        def update_pm25_timeseries_otros(station):
            if station is None:
                station = 'MER'
            return create_time_series('PM2.5', station)
        
        @app.callback(
            Output("pm10-timeseries-otros", "figure"),
            Input("station-dropdown-otros", "value")
        )
        def update_pm10_timeseries_otros(station):
            if station is None:
                station = 'MER'
            return create_time_series('PM10', station)


class CallbackManager:
    """Gestor principal de callbacks"""
    
    def __init__(self, app):
        self.app = app
        self.home_callbacks = HomePageCallbacks()
        self.otros_callbacks = OtrosContaminantesCallbacks()
    
    def register_all_callbacks(self):
        """Registra todos los callbacks de la aplicación"""
        self.home_callbacks.register_home_callbacks(self.app)
        self.otros_callbacks.register_otros_contaminantes_callbacks(self.app)
        
        print("✅ Todos los callbacks registrados correctamente")


# Función de conveniencia para inicializar callbacks
def initialize_callbacks(app):
    """Función de conveniencia para inicializar todos los callbacks"""
    callback_manager = CallbackManager(app)
    callback_manager.register_all_callbacks()
    return callback_manager 
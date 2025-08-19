"""
Módulo de callbacks para la aplicación de pronóstico de calidad del aire.
Organiza todos los callbacks por funcionalidad y página.
"""

from dash import Output, Input, callback, dcc
from typing import Any

from visualization import create_time_series, create_indicators
from config import config_manager
from components import indicator_components


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
            Output("pm25-timeseries-home", "figure"),
            Input("station-dropdown-home", "value")
        )
        def update_pm25_timeseries_home(station):
            if station is None:
                station = 'MER'
            return create_time_series('PM2.5', station)
        
        @app.callback(
            Output("pm10-timeseries-home", "figure"),
            Input("station-dropdown-home", "value")
        )
        def update_pm10_timeseries_home(station):
            if station is None:
                station = 'MER'
            return create_time_series('PM10', station)
        
        @app.callback(
            Output("indicators-container", "children"),
            Input("station-dropdown-home", "value")
        )
        def update_indicators_home(station):
            if station is None:
                station = 'MER'
            indicators = create_indicators(station)
            return indicator_components.wrap_indicators_in_columns(indicators)


class OtrosContaminantesCallbacks:
    """Callbacks específicos para la página de otros contaminantes"""
    
    @staticmethod
    def register_otros_contaminantes_callbacks(app):
        """Registra todos los callbacks de otros contaminantes"""
        
        @app.callback(
            Output("pollutant-timeseries-container", "children"),
            [Input("pollutant-dropdown", "value"),
             Input("station-dropdown-otros", "value")]
        )
        def update_pollutant_timeseries(pollutant, station):
            if pollutant is None or station is None:
                return [
                    dcc.Graph(
                        id="pollutant-timeseries",
                        figure={
                            'data': [],
                            'layout': {
                                'title': 'Selecciona un contaminante y estación',
                                'xaxis': {'visible': False},
                                'yaxis': {'visible': False},
                                'annotations': [{
                                    'text': 'Esperando selección...',
                                    'xref': 'paper',
                                    'yref': 'paper',
                                    'x': 0.5,
                                    'y': 0.5,
                                    'xanchor': 'center',
                                    'yanchor': 'middle',
                                    'showarrow': False,
                                    'font': {'size': 16, 'color': 'gray'}
                                }]
                            }
                        },
                        config={'responsive': True, 'displayModeBar': False}
                    )
                ]
            
            # Crear gráfico con los datos seleccionados
            figure = create_time_series(pollutant, station)
            return [
                dcc.Graph(
                    id="pollutant-timeseries",
                    figure=figure,
                    config={'responsive': True, 'displayModeBar': False}
                )
            ]
        
        @app.callback(
            Output("pollutant-info-text", "children"),
            Input("pollutant-dropdown", "value")
        )
        def update_pollutant_info(pollutant):
            if pollutant is None:
                return "Selecciona un contaminante para ver información específica."
            
            pollutant_info = config_manager.get_pollutant_info(pollutant)
            
            if pollutant == 'O3':
                return f"{pollutant_info['name']}: Pronósticos específicos por estación. Cambiar estación afecta observaciones y pronósticos."
            else:
                return f"{pollutant_info['name']}: Observaciones específicas por estación + Pronóstico regional (mean/min/max) igual para todas las estaciones."


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
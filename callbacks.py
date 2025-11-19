"""
Módulo de callbacks para la aplicación de pronóstico de calidad del aire.
Organiza todos los callbacks por funcionalidad y página.
"""

from dash import Output, Input, callback, dcc
from typing import Any
from datetime import datetime

from visualization import create_time_series, create_indicators, create_historical_time_series
from config import config_manager, DEFAULT_DATE_CONFIG
from components import indicator_components
from pages import get_forecast_datetime_str
from data_service import data_service
from dash import html


class HomePageCallbacks:
    """Callbacks específicos para la página principal"""
    
    @staticmethod
    def register_home_callbacks(app):
        """Registra todos los callbacks de la página principal"""
        
        @app.callback(
            [Output("o3-timeseries-home", "figure"),
             Output("ozone-max-summary-content", "children")],
            Input("station-dropdown-home", "value")
        )
        def update_o3_timeseries_and_summary(station):
            """Actualiza la serie temporal de ozono Y el resumen usando los mismos datos"""
            if station is None:
                station = 'MER'
            
            # Crear el gráfico (que ya consulta todos los datos de pronóstico)
            fig = create_time_series('O3', station)
            
            # Calcular el resumen usando los datos que ya se consultaron para el gráfico
            try:
                from data_service import data_service
                from datetime import datetime, timedelta
                
                # Obtener la fecha actual del pronóstico
                if DEFAULT_DATE_CONFIG['use_specific_date']:
                    fecha_str = DEFAULT_DATE_CONFIG['specific_date']
                else:
                    from postgres_data_service import get_last_available_date
                    latest_date = get_last_available_date()
                    if latest_date:
                        fecha_str = latest_date.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        fecha_str = None
                
                if not fecha_str:
                    summary_html = html.P(
                        "No hay datos de pronóstico disponibles",
                        style={
                            'font-size': '18px',
                            'font-family': 'Helvetica',
                            'color': '#666',
                            'margin': '0',
                            'text-align': 'center'
                        }
                    )
                    return fig, summary_html
                
                # Obtener los pronósticos batch (los mismos que usa la serie temporal)
                all_forecasts_batch = data_service.get_all_stations_forecast_batch(fecha_str)
                
                if not all_forecasts_batch:
                    summary_html = html.P(
                        "No hay datos de pronóstico disponibles",
                        style={
                            'font-size': '18px',
                            'font-family': 'Helvetica',
                            'color': '#666',
                            'margin': '0',
                            'text-align': 'center'
                        }
                    )
                    return fig, summary_html
                
                # Calcular el máximo entre todas las estaciones y todas las horas
                max_value = None
                max_station = None
                max_hour_number = None
                fecha_base = datetime.strptime(fecha_str, '%Y-%m-%d %H:%M:%S')
                
                for station_code, forecast_data in all_forecasts_batch.items():
                    if 'forecast_vector' in forecast_data:
                        forecast_vector = forecast_data['forecast_vector']
                        for hour_idx, value in enumerate(forecast_vector, start=1):
                            if max_value is None or value > max_value:
                                max_value = value
                                max_station = station_code
                                max_hour_number = hour_idx
                
                if max_value is not None and max_station is not None:
                    # Calcular la hora real (fecha_base + max_hour_number - 1 hora de corrección)
                    max_hour_datetime = fecha_base + timedelta(hours=max_hour_number) - timedelta(hours=1)
                    max_hour_str = max_hour_datetime.strftime('%H:%M')
                    
                    # Obtener nombre de la estación
                    stations_dict = data_service.get_all_stations()
                    station_info = stations_dict.get(max_station, {})
                    station_name = station_info.get('name', max_station)
                    
                    summary_text = f"Máxima concentración pronosticada: {max_value:.1f} ppb en {station_name}, a las {max_hour_str} hrs."
                    
                    print(f"✅ Resumen calculado desde datos de serie temporal: {max_value:.1f} ppb en {max_station} a las {max_hour_str}")
                    
                    summary_html = html.P(
                        summary_text,
                        style={
                            'font-size': '18px',
                            'font-family': 'Helvetica',
                            'color': '#1a1a1a',
                            'margin': '0',
                            'text-align': 'center',
                            'font-weight': '500'
                        }
                    )
                else:
                    summary_html = html.P(
                        "No hay datos de pronóstico disponibles",
                        style={
                            'font-size': '18px',
                            'font-family': 'Helvetica',
                            'color': '#666',
                            'margin': '0',
                            'text-align': 'center'
                        }
                    )
                
                return fig, summary_html
                
            except Exception as e:
                print(f"⚠️ Error calculando resumen desde datos de serie temporal: {e}")
                import traceback
                traceback.print_exc()
                
                summary_html = html.P(
                    "Error al cargar el resumen del pronóstico",
                    style={
                        'font-size': '18px',
                        'font-family': 'Helvetica',
                        'color': '#d32f2f',
                        'margin': '0',
                        'text-align': 'center'
                    }
                )
                return fig, summary_html
        
        
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
                    # Formatear fecha y hora de manera más clara
                    day_str = adjusted_datetime.strftime('%d')
                    month_names = {
                        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
                        7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
                    }
                    month_str = month_names[adjusted_datetime.month]
                    year_str = adjusted_datetime.strftime('%Y')
                    hour_str = adjusted_datetime.strftime('%H:%M')
                    datetime_str = f"a las {hour_str} hrs. del {day_str} de {month_str} de {year_str}"
                    print(f"✅ Usando fecha del último pronóstico menos 1h: {datetime_str}")
                else:
                    # Fallback: usar hora actual menos 1 hora
                    adjusted_datetime = datetime.now() - timedelta(hours=1)
                    day_str = adjusted_datetime.strftime('%d')
                    month_names = {
                        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
                        7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
                    }
                    month_str = month_names[adjusted_datetime.month]
                    year_str = adjusted_datetime.strftime('%Y')
                    hour_str = adjusted_datetime.strftime('%H:%M')
                    datetime_str = f"a las {hour_str} hrs. del {day_str} de {month_str} de {year_str}"
                    print(f"⚠️ Fallback: usando fecha actual menos 1h: {datetime_str}")
                    
            except Exception as e:
                print(f"❌ Error obteniendo fecha del pronóstico: {e}")
                # Fallback: usar hora actual menos 1 hora
                adjusted_datetime = datetime.now() - timedelta(hours=1)
                day_str = adjusted_datetime.strftime('%d')
                month_names = {
                    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
                    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
                }
                month_str = month_names[adjusted_datetime.month]
                year_str = adjusted_datetime.strftime('%Y')
                hour_str = adjusted_datetime.strftime('%H:%M')
                datetime_str = f"a las {hour_str} hrs. del {day_str} de {month_str} de {year_str}"
                print(f"⚠️ Error fallback: usando fecha actual menos 1h: {datetime_str}")
            
            title = f'Concentraciones de Ozono (ppb) - {datetime_str}'
            print(f"✅ Título generado: {title}")
            
            return title


class OtrosContaminantesCallbacks:
    """Callbacks específicos para la página de otros contaminantes"""
    
    @staticmethod
    def register_otros_contaminantes_callbacks(app):
        """Registra todos los callbacks de otros contaminantes"""
        
        # CALLBACKS COMENTADOS - Selector dinámico de contaminantes (para uso futuro)
        # @app.callback(
        #     Output("pollutant-timeseries-container", "children"),
        #     [Input("pollutant-dropdown", "value"),
        #      Input("station-dropdown-otros", "value")]
        # )
        # def update_pollutant_timeseries(pollutant, station):
        #     if pollutant is None or station is None:
        #         return [
        #             dcc.Graph(
        #                 id="pollutant-timeseries",
        #                 figure={
        #                     'data': [],
        #                     'layout': {
        #                         'title': 'Selecciona un contaminante y estación',
        #                         'xaxis': {'visible': False},
        #                         'yaxis': {'visible': False},
        #                         'annotations': [{
        #                             'text': 'Esperando selección...',
        #                             'xref': 'paper',
        #                             'yref': 'paper',
        #                             'x': 0.5,
        #                             'y': 0.5,
        #                             'xanchor': 'center',
        #                             'yanchor': 'middle',
        #                             'showarrow': False,
        #                             'font': {'size': 16, 'color': 'gray'}
        #                         }]
        #                     }
        #                 },
        #                 config={'responsive': True, 'displayModeBar': False}
        #             )
        #         ]
        #     
        #     # Crear gráfico con los datos seleccionados
        #     figure = create_time_series(pollutant, station)
        #     return [
        #         dcc.Graph(
        #             id="pollutant-timeseries",
        #             figure=figure,
        #             config={'responsive': True, 'displayModeBar': False}
        #         )
        #     ]
        # 
        # @app.callback(
        #     Output("pollutant-info-text", "children"),
        #     Input("pollutant-dropdown", "value")
        # )
        # def update_pollutant_info(pollutant):
        #     if pollutant is None:
        #         return "Selecciona un contaminante para ver información específica."
        #     
        #     pollutant_info = config_manager.get_pollutant_info(pollutant)
        #     
        #     if pollutant == 'O3':
        #         return f"{pollutant_info['name']}: Pronósticos específicos por estación. Cambiar estación afecta observaciones y pronósticos."
        #     else:
        #         return f"{pollutant_info['name']}: Observaciones específicas por estación + Pronóstico regional (mean/min/max) igual para todas las estaciones."
        
        # CALLBACKS ACTIVOS - Series de tiempo fijas de PM2.5 y PM10
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


class HistoricosCallbacks:
    """Callbacks específicos para la página de pronósticos históricos"""
    
    @staticmethod
    def register_historicos_callbacks(app):
        """Registra todos los callbacks de pronósticos históricos"""
        
        @app.callback(
            Output("pollutant-timeseries-historicos", "figure"),
            [Input("date-picker-historicos", "date"),
             Input("hour-picker-historicos", "value"),
             Input("pollutant-dropdown-historicos", "value"),
             Input("station-dropdown-historicos", "value")]
        )
        def update_pollutant_timeseries_historicos(date, hour, pollutant, station):
            if date is None:
                from datetime import datetime, timedelta
                date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            if hour is None:
                hour = 9
            if pollutant is None:
                pollutant = 'O3'
            if station is None:
                station = 'MER'
            # Combinar fecha y hora
            forecast_datetime_str = f"{date} {hour:02d}:00:00"
            return create_historical_time_series(pollutant, station, forecast_datetime_str)
        
        @app.callback(
            Output("pollutant-title-historicos", "children"),
            [Input("date-picker-historicos", "date"),
             Input("hour-picker-historicos", "value"),
             Input("pollutant-dropdown-historicos", "value"),
             Input("station-dropdown-historicos", "value")]
        )
        def update_pollutant_title_historicos(date, hour, pollutant, station):
            """Actualiza el título del pronóstico histórico"""
            if date is None:
                from datetime import datetime, timedelta
                date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            if hour is None:
                hour = 9
            if pollutant is None:
                pollutant = 'O3'
            if station is None:
                station = 'MER'
            
            # Obtener información del contaminante
            pollutant_info = config_manager.get_pollutant_info(pollutant)
            pollutant_name = pollutant_info['name']
            units = pollutant_info['units']
            
            # Formatear fecha
            try:
                forecast_date = datetime.strptime(date, '%Y-%m-%d')
                day_str = forecast_date.strftime('%d')
                month_names = {
                    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
                    7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
                }
                month_str = month_names[forecast_date.month]
                year_str = forecast_date.strftime('%Y')
                date_str = f"{day_str} de {month_str} de {year_str}"
            except:
                date_str = date
            
            stations_dict = data_service.get_all_stations()
            station_name = stations_dict.get(station, {}).get('name', station)
            
            return f'Concentraciones de {pollutant_name} ({units}) - Pronóstico del {date_str} a las {hour:02d}:00 hrs. - {station_name}'


class CallbackManager:
    """Gestor principal de callbacks"""
    
    def __init__(self, app):
        self.app = app
        self.home_callbacks = HomePageCallbacks()
        self.otros_callbacks = OtrosContaminantesCallbacks()
        self.historicos_callbacks = HistoricosCallbacks()
    
    def register_all_callbacks(self):
        """Registra todos los callbacks de la aplicación"""
        self.home_callbacks.register_home_callbacks(self.app)
        self.otros_callbacks.register_otros_contaminantes_callbacks(self.app)
        self.historicos_callbacks.register_historicos_callbacks(self.app)
        
        print("✅ Todos los callbacks registrados correctamente")


# Función de conveniencia para inicializar callbacks
def initialize_callbacks(app):
    """Función de conveniencia para inicializar todos los callbacks"""
    callback_manager = CallbackManager(app)
    callback_manager.register_all_callbacks()
    return callback_manager 
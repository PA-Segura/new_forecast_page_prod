"""
Módulo de callbacks para la aplicación de pronóstico de calidad del aire.
Organiza todos los callbacks por funcionalidad y página.
"""

from dash import Output, Input, State, callback, dcc
from typing import Any
from datetime import datetime

from visualization import create_time_series, create_indicators, create_historical_time_series, get_historical_data_for_csv
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
            
            # Calcular el resumen usando la API externa
            try:
                import requests
                from datetime import datetime
                from data_service import data_service
                
                # Para la API, usar la fecha actual (hoy) en lugar de la fecha del último pronóstico en BD
                # Esto asegura que siempre consultemos el pronóstico más reciente disponible en la API
                fecha_date = datetime.now()
                
                # Formatear fecha para la API (YYYY-MM-DD)
                fecha_api = fecha_date.strftime('%Y-%m-%d')
                
                # Construir URL de la API
                api_url = f"http://132.248.8.98:58888/ai_vi_transformer01/ozono/CDMX/{fecha_api}"
                
                print(f"🔍 [HOME] Consultando API: {api_url}")
                
                # Hacer petición a la API
                response = requests.get(api_url, timeout=10)
                response.raise_for_status()
                
                # Parsear JSON
                data = response.json()
                
                # Verificar que hay datos
                if not data or 'pronos' not in data or not data['pronos']:
                    summary_html = html.P(
                        "No hay datos de pronóstico disponibles en la API",
                        style={
                            'font-size': '18px',
                            'font-family': 'Helvetica',
                            'color': '#666',
                            'margin': '0',
                            'text-align': 'center'
                        }
                    )
                    return fig, summary_html
                
                # Obtener fecha y hora del pronóstico desde la respuesta de la API
                fecha_pron_str = data.get('fecha_pron', fecha_api)
                
                # Intentar parsear la fecha con hora, si no tiene hora usar 7 AM por defecto
                try:
                    # Intentar parsear con hora
                    if 'T' in fecha_pron_str or ' ' in fecha_pron_str:
                        # Formato con hora (ISO o con espacio)
                        if 'T' in fecha_pron_str:
                            fecha_pron_dt = datetime.fromisoformat(fecha_pron_str.replace('Z', '+00:00'))
                        else:
                            fecha_pron_dt = datetime.strptime(fecha_pron_str, '%Y-%m-%d %H:%M:%S')
                    else:
                        # Solo fecha, agregar 7 AM
                        fecha_pron_dt = datetime.strptime(fecha_pron_str, '%Y-%m-%d')
                        fecha_pron_dt = fecha_pron_dt.replace(hour=7, minute=0, second=0)
                except:
                    # Si falla el parsing, usar la fecha de la consulta con 7 AM
                    try:
                        fecha_pron_dt = datetime.strptime(fecha_pron_str, '%Y-%m-%d')
                        fecha_pron_dt = fecha_pron_dt.replace(hour=7, minute=0, second=0)
                    except:
                        fecha_pron_dt = fecha_date.replace(hour=7, minute=0, second=0)
                
                # Formatear fecha y hora para mostrar
                hora_formateada = fecha_pron_dt.strftime('%H:%M')
                
                # Formatear fecha en español manualmente
                meses_esp = {
                    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
                    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
                    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
                }
                dia = fecha_pron_dt.day
                mes = meses_esp[fecha_pron_dt.month]
                año = fecha_pron_dt.year
                fecha_formateada = f"{dia} de {mes} de {año}"
                
                # Encontrar el máximo valor en el array pronos
                max_pron = None
                max_value = None
                
                for pron in data['pronos']:
                    valor = pron.get('valor')
                    if valor is not None:
                        if max_value is None or valor > max_value:
                            max_value = valor
                            max_pron = pron
                
                if max_pron and max_value is not None:
                    # Obtener información del máximo
                    id_est = max_pron.get('id_est', 'N/A')
                    hora = max_pron.get('hora', 'N/A')
                    
                    # Obtener nombre de la estación si está disponible
                    try:
                        stations_dict = data_service.get_all_stations()
                        station_info = stations_dict.get(id_est, {})
                        station_name = station_info.get('name', id_est)
                    except:
                        station_name = id_est
                    
                    print(f"✅ [HOME] Resumen desde API: {max_value:.1f} ppb en {id_est} a las {hora} (Pronóstico: {fecha_formateada} {hora_formateada})")
                    
                    summary_html = html.P([
                        f"Máxima concentración pronosticada: {max_value:.1f} ppb en {station_name}, a las {hora} hrs.",
                        html.Br(),
                        html.Span(
                            f"(Pronóstico del {fecha_formateada} a las {hora_formateada} hrs.)",
                            style={'font-style': 'italic'}
                        )
                    ], style={
                        'font-size': '18px',
                        'font-family': 'Helvetica',
                        'color': '#1a1a1a',
                        'margin': '0',
                        'text-align': 'center',
                        'font-weight': '500'
                    })
                else:
                    summary_html = html.P(
                        "No se encontró valor máximo en los datos de la API",
                        style={
                            'font-size': '18px',
                            'font-family': 'Helvetica',
                            'color': '#666',
                            'margin': '0',
                            'text-align': 'center'
                        }
                    )
                
                return fig, summary_html
                
            except requests.exceptions.RequestException as e:
                print(f"⚠️ [HOME] Error de conexión con API: {e}")
                summary_html = html.P(
                    f"Error al conectar con la API: {str(e)}",
                    style={
                        'font-size': '18px',
                        'font-family': 'Helvetica',
                        'color': '#d32f2f',
                        'margin': '0',
                        'text-align': 'center'
                    }
                )
                return fig, summary_html
            except Exception as e:
                print(f"⚠️ [HOME] Error calculando resumen desde API: {e}")
                import traceback
                traceback.print_exc()
                
                summary_html = html.P(
                    f"Error al procesar datos de la API: {str(e)}",
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
        
        # Callbacks para navegación de fecha (anterior/siguiente)
        @app.callback(
            Output("date-picker-historicos", "date"),
            Input("date-picker-historicos-prev", "n_clicks"),
            Input("date-picker-historicos-next", "n_clicks"),
            State("date-picker-historicos", "date"),
            prevent_initial_call=True
        )
        def navigate_date(prev_clicks, next_clicks, current_date):
            """Navega a la fecha anterior o siguiente"""
            from dash import callback_context
            from datetime import datetime, timedelta
            
            if current_date is None:
                current_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Determinar qué botón se presionó
            ctx = callback_context
            if not ctx.triggered:
                return current_date
            
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            current_dt = datetime.strptime(current_date, '%Y-%m-%d')
            
            if button_id == 'date-picker-historicos-prev':
                # Día anterior
                new_date = (current_dt - timedelta(days=1)).strftime('%Y-%m-%d')
            elif button_id == 'date-picker-historicos-next':
                # Día siguiente
                new_date = (current_dt + timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                return current_date
            
            return new_date
        
        # Callbacks para navegación de hora (anterior/siguiente)
        @app.callback(
            Output("hour-picker-historicos", "value"),
            Input("hour-picker-historicos-prev", "n_clicks"),
            Input("hour-picker-historicos-next", "n_clicks"),
            State("hour-picker-historicos", "value"),
            prevent_initial_call=True
        )
        def navigate_hour(prev_clicks, next_clicks, current_hour):
            """Navega a la hora anterior o siguiente"""
            from dash import callback_context
            
            if current_hour is None:
                current_hour = 9
            
            # Determinar qué botón se presionó
            ctx = callback_context
            if not ctx.triggered:
                return current_hour
            
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            if button_id == 'hour-picker-historicos-prev':
                # Hora anterior (circular: 23 -> 22 -> ... -> 0 -> 23)
                new_hour = (current_hour - 1) % 24
            elif button_id == 'hour-picker-historicos-next':
                # Hora siguiente (circular: 0 -> 1 -> ... -> 23 -> 0)
                new_hour = (current_hour + 1) % 24
            else:
                return current_hour
            
            return new_hour

        @app.callback(
            Output("download-csv-historicos", "data"),
            Input("btn-download-csv-historicos", "n_clicks"),
            [State("date-picker-historicos", "date"),
             State("hour-picker-historicos", "value"),
             State("pollutant-dropdown-historicos", "value"),
             State("station-dropdown-historicos", "value")],
            prevent_initial_call=True
        )
        def download_csv_historicos(n_clicks, date, hour, pollutant, station):
            """Genera y descarga CSV con datos de pronóstico y observaciones"""
            if not n_clicks:
                return None

            from datetime import timedelta
            if date is None:
                date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            if hour is None:
                hour = 9
            if pollutant is None:
                pollutant = 'O3'
            if station is None:
                station = 'MER'

            forecast_datetime_str = f"{date} {hour:02d}:00:00"
            df = get_historical_data_for_csv(pollutant, station, forecast_datetime_str)

            if df.empty:
                return None

            filename = f"historico_{pollutant}_{station}_{date}_{hour:02d}h.csv"
            return dcc.send_data_frame(df.to_csv, filename, index=False)


class DebugResumenCallbacks:
    """Callbacks específicos para la página de debug resumen"""
    
    @staticmethod
    def register_debug_resumen_callbacks(app):
        """Registra todos los callbacks de la página de debug resumen"""
        
        @app.callback(
            Output("ozone-max-summary-content-debug", "children"),
            Input("debug-resumen-location", "pathname")
        )
        def update_debug_summary(pathname):
            """Actualiza el resumen del pronóstico para la página de debug"""
            try:
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
                    return html.P(
                        "No hay datos de pronóstico disponibles",
                        style={
                            'font-size': '18px',
                            'font-family': 'Helvetica',
                            'color': '#666',
                            'margin': '0',
                            'text-align': 'center'
                        }
                    )
                
                # Obtener los pronósticos batch
                all_forecasts_batch = data_service.get_all_stations_forecast_batch(fecha_str)
                
                if not all_forecasts_batch:
                    return html.P(
                        "No hay datos de pronóstico disponibles",
                        style={
                            'font-size': '18px',
                            'font-family': 'Helvetica',
                            'color': '#666',
                            'margin': '0',
                            'text-align': 'center'
                        }
                    )
                
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
                    
                    print(f"✅ [DEBUG] Resumen calculado: {max_value:.1f} ppb en {max_station} a las {max_hour_str}")
                    
                    return html.P(
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
                    return html.P(
                        "No hay datos de pronóstico disponibles",
                        style={
                            'font-size': '18px',
                            'font-family': 'Helvetica',
                            'color': '#666',
                            'margin': '0',
                            'text-align': 'center'
                        }
                    )
                
            except Exception as e:
                print(f"⚠️ [DEBUG] Error calculando resumen: {e}")
                import traceback
                traceback.print_exc()
                
                return html.P(
                    "Error al cargar el resumen del pronóstico",
                    style={
                        'font-size': '18px',
                        'font-family': 'Helvetica',
                        'color': '#d32f2f',
                        'margin': '0',
                        'text-align': 'center'
                    }
                )
        
        @app.callback(
            Output("ozone-max-summary-api-debug", "children"),
            Input("debug-resumen-location", "pathname")
        )
        def update_debug_summary_api(pathname):
            """Actualiza el resumen del pronóstico desde la API externa"""
            try:
                import requests
                from datetime import datetime
                
                # Para la API, usar la fecha actual (hoy) en lugar de la fecha del último pronóstico en BD
                # Esto asegura que siempre consultemos el pronóstico más reciente disponible en la API
                fecha_date = datetime.now()
                
                # Formatear fecha para la API (YYYY-MM-DD)
                fecha_api = fecha_date.strftime('%Y-%m-%d')
                
                # Construir URL de la API
                api_url = f"http://132.248.8.98:58888/ai_vi_transformer01/ozono/CDMX/{fecha_api}"
                
                print(f"🔍 [DEBUG API] Consultando: {api_url}")
                
                # Hacer petición a la API
                response = requests.get(api_url, timeout=10)
                response.raise_for_status()
                
                # Parsear JSON
                data = response.json()
                
                # Verificar que hay datos
                if not data or 'pronos' not in data or not data['pronos']:
                    return html.P(
                        "No hay datos de pronóstico disponibles en la API",
                        style={
                            'font-size': '18px',
                            'font-family': 'Helvetica',
                            'color': '#666',
                            'margin': '0',
                            'text-align': 'center'
                        }
                    )
                
                # Obtener fecha y hora del pronóstico desde la respuesta de la API
                fecha_pron_str = data.get('fecha_pron', fecha_api)
                
                # Intentar parsear la fecha con hora, si no tiene hora usar 7 AM por defecto
                try:
                    # Intentar parsear con hora
                    if 'T' in fecha_pron_str or ' ' in fecha_pron_str:
                        # Formato con hora (ISO o con espacio)
                        if 'T' in fecha_pron_str:
                            fecha_pron_dt = datetime.fromisoformat(fecha_pron_str.replace('Z', '+00:00'))
                        else:
                            fecha_pron_dt = datetime.strptime(fecha_pron_str, '%Y-%m-%d %H:%M:%S')
                    else:
                        # Solo fecha, agregar 7 AM
                        fecha_pron_dt = datetime.strptime(fecha_pron_str, '%Y-%m-%d')
                        fecha_pron_dt = fecha_pron_dt.replace(hour=7, minute=0, second=0)
                except:
                    # Si falla el parsing, usar la fecha de la consulta con 7 AM
                    try:
                        fecha_pron_dt = datetime.strptime(fecha_pron_str, '%Y-%m-%d')
                        fecha_pron_dt = fecha_pron_dt.replace(hour=7, minute=0, second=0)
                    except:
                        fecha_pron_dt = fecha_date.replace(hour=7, minute=0, second=0)
                
                # Formatear fecha y hora para mostrar
                hora_formateada = fecha_pron_dt.strftime('%H:%M')
                
                # Formatear fecha en español manualmente
                meses_esp = {
                    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
                    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
                    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
                }
                dia = fecha_pron_dt.day
                mes = meses_esp[fecha_pron_dt.month]
                año = fecha_pron_dt.year
                fecha_formateada = f"{dia} de {mes} de {año}"
                
                # Encontrar el máximo valor en el array pronos
                max_pron = None
                max_value = None
                
                for pron in data['pronos']:
                    valor = pron.get('valor')
                    if valor is not None:
                        if max_value is None or valor > max_value:
                            max_value = valor
                            max_pron = pron
                
                if max_pron and max_value is not None:
                    # Obtener información del máximo
                    id_est = max_pron.get('id_est', 'N/A')
                    hora = max_pron.get('hora', 'N/A')
                    dia = max_pron.get('dia', fecha_api)
                    
                    # Obtener nombre de la estación si está disponible
                    try:
                        stations_dict = data_service.get_all_stations()
                        station_info = stations_dict.get(id_est, {})
                        station_name = station_info.get('name', id_est)
                    except:
                        station_name = id_est
                    
                    summary_text = f"Máxima concentración pronosticada: {max_value:.1f} ppb en {station_name}, a las {hora} hrs. (Pronóstico del {fecha_formateada} a las {hora_formateada} hrs.)"
                    
                    print(f"✅ [DEBUG API] Resumen calculado: {max_value:.1f} ppb en {id_est} a las {hora} (Pronóstico: {fecha_formateada} {hora_formateada})")
                    
                    return html.P([
                        f"Máxima concentración pronosticada: {max_value:.1f} ppb en {station_name}, a las {hora} hrs.",
                        html.Br(),
                        html.Span(
                            f"(Pronóstico del {fecha_formateada} a las {hora_formateada} hrs.)",
                            style={'font-style': 'italic'}
                        )
                    ], style={
                        'font-size': '18px',
                        'font-family': 'Helvetica',
                        'color': '#1a1a1a',
                        'margin': '0',
                        'text-align': 'center',
                        'font-weight': '500'
                    })
                else:
                    return html.P(
                        "No se encontró valor máximo en los datos de la API",
                        style={
                            'font-size': '18px',
                            'font-family': 'Helvetica',
                            'color': '#666',
                            'margin': '0',
                            'text-align': 'center'
                        }
                    )
                
            except requests.exceptions.RequestException as e:
                print(f"⚠️ [DEBUG API] Error de conexión: {e}")
                return html.P(
                    f"Error al conectar con la API: {str(e)}",
                    style={
                        'font-size': '18px',
                        'font-family': 'Helvetica',
                        'color': '#d32f2f',
                        'margin': '0',
                        'text-align': 'center'
                    }
                )
            except Exception as e:
                print(f"⚠️ [DEBUG API] Error calculando resumen: {e}")
                import traceback
                traceback.print_exc()
                
                return html.P(
                    f"Error al procesar datos de la API: {str(e)}",
                    style={
                        'font-size': '18px',
                        'font-family': 'Helvetica',
                        'color': '#d32f2f',
                        'margin': '0',
                        'text-align': 'center'
                    }
                )


class CallbackManager:
    """Gestor principal de callbacks"""
    
    def __init__(self, app):
        self.app = app
        self.home_callbacks = HomePageCallbacks()
        self.otros_callbacks = OtrosContaminantesCallbacks()
        self.historicos_callbacks = HistoricosCallbacks()
        self.debug_resumen_callbacks = DebugResumenCallbacks()
    
    def register_all_callbacks(self):
        """Registra todos los callbacks de la aplicación"""
        self.home_callbacks.register_home_callbacks(self.app)
        self.otros_callbacks.register_otros_contaminantes_callbacks(self.app)
        self.historicos_callbacks.register_historicos_callbacks(self.app)
        self.debug_resumen_callbacks.register_debug_resumen_callbacks(self.app)
        
        print("✅ Todos los callbacks registrados correctamente")


# Función de conveniencia para inicializar callbacks
def initialize_callbacks(app):
    """Función de conveniencia para inicializar todos los callbacks"""
    callback_manager = CallbackManager(app)
    callback_manager.register_all_callbacks()
    return callback_manager 
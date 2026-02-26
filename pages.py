"""
Módulo de páginas de la aplicación.
Contiene los layouts para cada página de la aplicación.
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
from typing import Any, List
from datetime import datetime

from components import (
    header_components,
    selector_components,
    card_components,
    alert_components,
    layout_containers,
    indicator_components,
    summary_components
)
from visualization import create_indicators, create_professional_map
from config import DEFAULT_DATE_CONFIG, STYLES, COLORS
from data_service import data_service


def get_forecast_datetime_str() -> str:
    """Obtiene la fecha/hora del pronóstico formateada para mostrar en el título"""
    from datetime import timedelta
    
    if DEFAULT_DATE_CONFIG['use_specific_date']:
        # Usar fecha específica configurada
        forecast_datetime = datetime.strptime(DEFAULT_DATE_CONFIG['specific_date'], '%Y-%m-%d %H:%M:%S')
    else:
        # Usar la fecha del último pronóstico disponible en la base de datos
        try:
            from postgres_data_service import get_last_available_date
            forecast_datetime = get_last_available_date()
            print(f"✅ Usando fecha del último pronóstico: {forecast_datetime}")
        except Exception as e:
            print(f"⚠️ Error obteniendo fecha del último pronóstico: {e}, usando fecha actual")
            # Fallback: usar fecha actual
            forecast_datetime = datetime.now().replace(minute=0, second=0, microsecond=0)
    
    # Restar 1 hora al último pronóstico
    adjusted_datetime = forecast_datetime - timedelta(hours=1)
    print(f"✅ Fecha ajustada (último pronóstico - 1h): {adjusted_datetime}")
    
    # Formatear de manera más clara y legible
    # Ejemplo: "a las 13:00 hrs. del 15 de Mayo de 2023"
    hour_str = adjusted_datetime.strftime('%H:%M')
    day_str = adjusted_datetime.strftime('%d')
    month_names = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
        7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    month_str = month_names[adjusted_datetime.month]
    year_str = adjusted_datetime.strftime('%Y')
    
    return f"a las {hour_str} hrs. del {day_str} de {month_str} de {year_str}"


class HomePage:
    """Página principal de la aplicación con estilo profesional vdev8"""
    
    @staticmethod
    def layout(**kwargs) -> List[Any]:
        """Layout para la página principal que acepta parámetros de URL"""
        # Extraer parámetros si existen, usar configuración por defecto para datos reales
        id_est = kwargs.get('id_est', DEFAULT_DATE_CONFIG['station_default'])
        fecha = kwargs.get('fecha', None)
        
        # Crear indicadores para la estación por defecto
        indicators = create_indicators(id_est)
        wrapped_indicators = indicator_components.wrap_indicators_in_columns(indicators)
        
        # Obtener fecha/hora del pronóstico para mostrar en el título
        forecast_time_str = get_forecast_datetime_str()
        
        return [
            # Header solo con logos (sin selector de estación)
            header_components.create_logo_header(),
            
            # Título fusionado con cintillo - COMENTADO (ahora está en el navbar)
            # header_components.create_fused_title_header(),
            
            # Mapa de estaciones - Inicializado directamente (estilo vdev8)
            html.Div([
                html.H3('Pronóstico de Concentración Máxima de Ozono en Próximas 24 horas', style=STYLES['title']),
                dcc.Graph(
                    id="stations-map",
                    figure=create_professional_map(),  # Inicializar directamente
                    style={'height': '400px'},
                    config={
                        'scrollZoom': True, 
                        'displayModeBar': True,
                        'displaylogo': False,  # Ocultar logo de Plotly
                        'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d', 'autoScale2d', 'resetScale2d'],  # Remover botones innecesarios
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': 'pronostico_ozono',
                            'height': 800,
                            'width': 1200,
                            'scale': 2
                        }
                    }
                )
            ], style=STYLES['container']),
            
            # Resumen del máximo pronóstico de ozono
            summary_components.create_ozone_max_summary(),
            
            # Serie temporal de Ozono (estilo vdev8) - CON FECHA/HORA DEL PRONÓSTICO
            html.Div([
                # Título y selector de estación en la misma línea
                html.Div([
                    html.H3(f'Concentraciones de Ozono (ppb) - {forecast_time_str}', 
                            id='o3-title', 
                            style={**STYLES['title'], 'margin': '0', 'flex': '1'}),
                    html.Div([
                        html.Label('Seleccionar estación:', style={
                            'font-family': 'Helvetica',
                            'font-size': '16px',
                            'font-weight': 'bold',
                            'color': COLORS['text'],
                            'margin-right': '10px',
                            'display': 'inline-block',
                            'vertical-align': 'middle'
                        }),
                        dcc.Dropdown(
                            id='station-dropdown-home',
                            options=[{'label': station_info['name'], 'value': code}
                                    for code, station_info in data_service.get_all_stations().items()],
                            value=id_est,
                            style={
                                'width': '300px',
                                'font-family': 'Helvetica',
                                'font-size': '14px',
                                'border-radius': '8px',
                                'box-shadow': '0 2px 4px rgba(0,0,0,0.05)',
                                'display': 'inline-block',
                                'vertical-align': 'middle'
                            }
                        )
                    ], style={
                        'display': 'flex',
                        'align-items': 'center',
                        'justify-content': 'flex-end'
                    })
                ], style={
                    'display': 'flex',
                    'align-items': 'center',
                    'justify-content': 'space-between',
                    'margin-bottom': '15px',
                    'gap': '20px'
                }),
                dcc.Graph(
                    id="o3-timeseries-home", 
                    config={
                        'scrollZoom': True, 
                        'displayModeBar': True,
                        'displaylogo': False,  # Ocultar logo de Plotly
                        'modeBarButtonsToRemove': ['pan2d', 'lasso2d', 'select2d', 'autoScale2d', 'resetScale2d'],  # Remover botones innecesarios
                        'toImageButtonOptions': {
                            'format': 'png',
                            'filename': 'serie_tiempo_ozono',
                            'height': 800,
                            'width': 1200,
                            'scale': 2
                        }
                    }
                )
            ], style=STYLES['container']),
            
            
            # Grid de diales al final (estilo vdev8)
            html.Div([
                html.H3('Probabilidades de superar umbrales de ozono', style=STYLES['title']),
                html.Div(id="indicators-container", children=wrapped_indicators)
            ], style=STYLES['container']),
            
            # Enlaces y créditos
            HomePage._create_footer_cards()
        ]
    
    @staticmethod
    def _create_footer_cards() -> dbc.Row:
        """Crea las tarjetas del pie de página"""
        explore_card = card_components.create_action_card(
            title="Explorar Más",
            description="Visualiza otros contaminantes y opciones avanzadas",
            button_text="Ver Otros Contaminantes",
            button_href="/otros-contaminantes",
            button_color="primary",
            button_size="lg"
        )
        
        credits_card = card_components.create_info_card(
            title="Créditos",
            content="Autores: Olmo Zavala, Pedro Segura, Pablo Camacho, Jorge Zavala, Pavel Oropeza, Rosario Romero, Octavio Gómez",
            is_small=True
        )
        
        return layout_containers.create_action_cards_row([explore_card, credits_card])


class OtrosContaminantesPage:
    """Página de otros contaminantes con estilo profesional vdev8"""
    
    @staticmethod
    def layout(**kwargs) -> List[Any]:
        """Layout para otros contaminantes que acepta parámetros de URL"""
        # Extraer parámetros si existen, usar configuración por defecto para datos reales
        id_est = kwargs.get('id_est', DEFAULT_DATE_CONFIG['station_default'])
        pollutant = kwargs.get('pollutant', 'O3')
        
        return [
            # Encabezado
            header_components.create_page_title("Otros Contaminantes"),
            
            # Selector de estación
            layout_containers.create_responsive_selector_row(
                left_component=selector_components.create_station_dropdown(
                    dropdown_id='station-dropdown-otros',
                    default_value=id_est
                ),
                right_component=html.Div()  # Componente vacío para mantener el layout
            ),
            
            # CÓDIGO COMENTADO - Selectores originales para otros contaminantes
            # layout_containers.create_responsive_selector_row(
            #     left_component=selector_components.create_pollutant_dropdown(
            #         dropdown_id='pollutant-dropdown',
            #         default_value=pollutant
            #     ),
            #     right_component=selector_components.create_station_dropdown(
            #         dropdown_id='station-dropdown-otros',
            #         default_value=id_est
            #     )
            # ),
            # 
            # # Nota explicativa sobre tipos de pronóstico
            # dbc.Row([
            #     dbc.Col([
            #         alert_components.create_pollutant_info_alert()
            #     ], width=12)
            # ]),
            # 
            # # Gráfico principal dinámico
            # dbc.Row([
            #     dbc.Col([
            #         html.Div(id="pollutant-timeseries-container", children=[
            #             html.Div("Selecciona un contaminante y estación para ver los datos", 
            #                    className="text-center text-muted p-4")
            #         ])
            #     ], width=12)
            # ], className="mb-4"),
            
            # Material particulado (PM2.5 y PM10) - estilo vdev8
            html.Div([
                # PM10
                html.Div([
                    html.H3(f'Concentraciones de PM10 (µg/m³) {get_forecast_datetime_str()}', style=STYLES['title']),
                    dcc.Graph(id="pm10-timeseries-otros", config={'displayModeBar': False})
                ], style=STYLES['container']),
                
                # PM2.5
                html.Div([
                    html.H3(f'Concentraciones de PM2.5 (µg/m³) - {get_forecast_datetime_str()}', style=STYLES['title']),
                    dcc.Graph(id="pm25-timeseries-otros", config={'displayModeBar': False})
                ], style=STYLES['container'])
            ]),
            
            # Navegación de regreso
            OtrosContaminantesPage._create_navigation_cards()
        ]
    
    @staticmethod
    def _create_navigation_cards() -> dbc.Row:
        """Crea las tarjetas de navegación"""
        back_card = card_components.create_action_card(
            title="Volver al Inicio",
            description="Regresa a la página principal con todos los contaminantes",
            button_text="Página Principal",
            button_href="/",
            button_color="secondary",
            button_size="lg"
        )
        
        return layout_containers.create_action_cards_row([back_card])


class HistoricosPage:
    """Página de pronósticos históricos con estilo profesional vdev8"""
    
    @staticmethod
    def layout(**kwargs) -> List[Any]:
        """Layout para pronósticos históricos que acepta parámetros de URL"""
        # Extraer parámetros si existen, usar configuración por defecto para datos reales
        id_est = kwargs.get('id_est', DEFAULT_DATE_CONFIG['station_default'])
        
        return [
            # Encabezado
            header_components.create_page_title("Pronósticos Históricos"),
            
            # Selectores: Estación y Hora
            layout_containers.create_responsive_selector_row(
                left_component=selector_components.create_station_dropdown(
                    dropdown_id='station-dropdown-historicos',
                    default_value=id_est
                ),
                right_component=selector_components.create_hour_picker(
                    hour_picker_id='hour-picker-historicos',
                    default_hour=9
                )
            ),
            
            # Selectores: Contaminante y Fecha
            layout_containers.create_responsive_selector_row(
                left_component=selector_components.create_pollutant_dropdown(
                    dropdown_id='pollutant-dropdown-historicos',
                    default_value='O3',
                    only_main_pollutants=True  # Solo O3, PM2.5 y PM10 en históricos
                ),
                right_component=selector_components.create_date_picker(
                    date_picker_id='date-picker-historicos',
                    default_date=None
                )
            ),
            
            # Serie temporal histórica (única, dinámica)
            html.Div([
                html.H3('Pronóstico Histórico', 
                        id='pollutant-title-historicos', 
                        style=STYLES['title']),
                dcc.Graph(id="pollutant-timeseries-historicos", config={'displayModeBar': False}),
                html.Div([
                    dbc.Button(
                        [html.I(className="fas fa-download me-2"), "Descargar CSV"],
                        id="btn-download-csv-historicos",
                        color="primary",
                        outline=True,
                        size="sm",
                        className="mt-2"
                    ),
                    dcc.Download(id="download-csv-historicos")
                ], style={'textAlign': 'right', 'padding': '0 10px 10px 0'})
            ], style=STYLES['container']),
            
            # Navegación de regreso
            HistoricosPage._create_navigation_cards()
        ]
    
    @staticmethod
    def _create_navigation_cards() -> dbc.Row:
        """Crea las tarjetas de navegación"""
        back_card = card_components.create_action_card(
            title="Volver al Inicio",
            description="Regresa a la página principal con todos los contaminantes",
            button_text="Página Principal",
            button_href="/",
            button_color="secondary",
            button_size="lg"
        )
        
        return layout_containers.create_action_cards_row([back_card])


class AcercaPage:
    """Página 'Acerca de este pronóstico' con información del sistema"""
    
    @staticmethod
    def layout(**kwargs) -> List[Any]:
        """Layout para la página de información del sistema"""
        return [
            # Header con logo
            header_components.create_logo_header(),
            
            # Título de la página
            header_components.create_page_title("Acerca de este Pronóstico"),
            
            # Contenido principal
            AcercaPage._create_main_content(),
            
            # Sección de créditos y contacto
            AcercaPage._create_credits_section(),
            
            # Tarjetas de navegación
            AcercaPage._create_navigation_cards()
        ]
    
    @staticmethod
    def _create_main_content() -> html.Div:
        """Crea el contenido principal de la página"""
        return html.Div([
            # Sección: Cómo usar el sistema
            dbc.Card([
                dbc.CardHeader([
                    html.H4("Componentes del visualizador de pronóstico", className="mb-0")
                ], style={'background-color': COLORS['gradient_start'], 'color': 'white'}),
                dbc.CardBody([
                    html.Div([
                        html.H5("Selección de Estación"),
                        html.P([
                            "En menu desplegable se puede seleccionar la estación de la que se quiera consultar el pronóstico",
                            #"Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
                        ]),
                        html.Div([
                            html.Img(
                                src="assets/sel_est_dropmenu.png",
                                alt="Menú desplegable para selección de estación",
                                style={
                                    'width': '100%',
                                    'max-width': '400px',
                                    'height': 'auto',
                                    'border-radius': '8px',
                                    'box-shadow': '0 2px 8px rgba(0,0,0,0.1)',
                                    'margin': '15px 0',
                                    'display': 'block',
                                    'margin-left': 'auto',
                                    'margin-right': 'auto'
                                }
                            )
                        ], style={'text-align': 'center'}),
                        html.H5("Mapa"),
                        html.P([
                            "Mapa interactivo de visualización de calidad del aire por ozono, presenta el valor de concentración máxima de ozono pronosticada para las próximas 24 horas. Se muestran clasificación de pronóstico con base en indicadores de calidad del aire (Buena, Aceptable, Mala, Muy Mala, Extremadamente Mala). Al posicionar el puntero sobre una estación se despliega un cuadro de información con el valor de concentración esperada, clave y nombre de la estación correspondiente.",
                            #"Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
                        ]),
                        html.Div([
                            html.Img(
                                src="assets/mapa_forecast.png",
                                alt="Mapa de pronóstico de calidad del aire",
                                style={
                                    'width': '100%',
                                    'max-width': '500px',
                                    'height': 'auto',
                                    'border-radius': '8px',
                                    'box-shadow': '0 2px 8px rgba(0,0,0,0.1)',
                                    'margin': '15px 0',
                                    'display': 'block',
                                    'margin-left': 'auto',
                                    'margin-right': 'auto'
                                }
                            )
                        ], style={'text-align': 'center'}),
                        html.H5("Series de tiempo de ozono"),
                        html.P([
                            "Serie de tiempo de concentraciones horarias de ozono. La estación seleccionada se muestra en el encabezado de la serie de tiempo (en este caso la estación Villa de las Flores), se muestra en rojo las concentraciones pronosticadas para las próximas 24 horas, y en azul marino se muestran las concentraciones de 48 horas de observaciones registradas en la estación seleccionada, en gris claro, y azul claro se muestran pronósticos y observaciones de las otras estaciones de monitoreo.",
                            #"totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae dicta sunt explicabo."
                        ]),  #En la parte superior se muestra la fecha y hora del pronóstico.
                        html.Div([
                            html.Img(
                                src="assets/serie_tiempo_ozono.png",
                                alt="Serie de tiempo de concentraciones de ozono",
                                style={
                                    'width': '100%',
                                    'max-width': '500px',
                                    'height': 'auto',
                                    'border-radius': '8px',
                                    'box-shadow': '0 2px 8px rgba(0,0,0,0.1)',
                                    'margin': '15px 0',
                                    'display': 'block',
                                    'margin-left': 'auto',
                                    'margin-right': 'auto'
                                }
                            )
                        ], style={'text-align': 'center'}),
                        html.H5("Series de tiempo de materiales particulados"),
                        html.P([
                            "Los contenedores de series de tiempo de contaminantes por material particulado, PM10,  y PM2.5 (en µg/m³), despliegan las últimas observaciones disponibles para estos contaminantes, así como un pronóstico regional para las siguientes 24 horas. En los pronósticos de cada contaminante se muestran 3 series de tiempo principales que corresponde a los valores mínimos, promedio y máximos pronosticados para toda la región. En la figura se resalta la estación PED (Pedregal). Los valores pronosticados corresponden a los valores mínimos, promdedio y máximos regionales generados por el modelo. ",
                            #Serie de tiempo de concentraciones horarias de partículas PM₁₀ y PM₂.₅. Similar a la serie de ozono, se muestran las concentraciones pronosticadas para las próximas 24 horas y las observaciones históricas de la estación seleccionada y otras estaciones de monitoreo."
                        ]),
                        html.Div([
                            html.Img(
                                src="assets/series_tiempo_pms.png",
                                alt="Serie de tiempo de concentraciones de partículas",
                                style={
                                    'width': '100%',
                                    'max-width': '500px',
                                    'height': 'auto',
                                    'border-radius': '8px',
                                    'box-shadow': '0 2px 8px rgba(0,0,0,0.1)',
                                    'margin': '15px 0',
                                    'display': 'block',
                                    'margin-left': 'auto',
                                    'margin-right': 'auto'
                                }
                            )
                        ], style={'text-align': 'center'}),
                    ])
                ])
            ], className="mb-4"),
            
            # Sección: Metodología del pronóstico
            dbc.Card([
                dbc.CardHeader([
                    html.H4("🔬 Metodología del Pronóstico", className="mb-0")
                ], style={'background-color': COLORS['gradient_end'], 'color': 'white'}),
                dbc.CardBody([
                    html.Div([
                        #html.H5("Redes Neuronales"),
                        html.P([
                            "El pronóstico basado en aprendizaje automático integra observaciones recientes de calidad del aire con el pronóstico meteorológico generado con el modelo físico WRF-ARW. El modelo de pronóstico usa una arquitectura híbrida basada en un módulo autorregresivo para series temporales y un módulo para la asimilación de pronósticos meteorológicos mediante Vision Transformers y redes neuronales densas implementado en Pytorch. ",
                            html.Br(),
                            html.Br(),
                            "Datos de series de datos de contaminantes: ozono troposférico (O₃), monóxido de carbono (CO), dióxido de nitrógeno (NO₂), partículas menores a 10 micrómetros (PM₁₀), partículas menores a 2.5 micrómetros (PM₂.₅), óxidos de nitrógeno (NOₓ), óxido nítrico (NO) y dióxido de azufre (SO₂), y salidas de modelo WRF desarrollado por el grupo Interacción Océano Atmósfera del ICAyCC y disponible en el siguiente ",
                            html.A("link", href="http://grupo-ioa.atmosfera.unam.mx/pronosticos/index.php/meteorologia", target="_blank", style={'color': '#007bff', 'text-decoration': 'underline'}),
                            "."
                        ])
                    ])
                ])
            ], className="mb-4"),
            
            # Sección: Espacios para imágenes explicativas (COMENTADA)
            # dbc.Card([
            #     dbc.CardHeader([
            #         html.H4("📊 Visualizaciones Explicativas", className="mb-0")
            #     ], style={'background-color': COLORS['card'], 'color': COLORS['text']}),
            #     dbc.CardBody([
            #         dbc.Row([
            #             dbc.Col([
            #             html.Div([
            #                 html.H5("Diagrama del Modelo"),
            #             html.Div([
            #                     html.Div([
            #                         "📊 Diagrama del Modelo Neural",
            #                         html.Br(),
            #                         html.Small("(Imagen en desarrollo)", style={'color': '#666'})
            #                     ], style={
            #                         'width': '100%',
            #                         'height': '200px',
            #                         'border': '2px dashed #ccc',
            #                         'border-radius': '8px',
            #                         'display': 'flex',
            #                         'align-items': 'center',
            #                         'justify-content': 'center',
            #                         'flex-direction': 'column',
            #                         'text-align': 'center',
            #                         'background-color': '#f8f9fa',
            #                         'color': '#6c757d'
            #                     }),
            #                     html.P("Espacio para diagrama explicativo del modelo de pronóstico", 
            #                            style={'text-align': 'center', 'color': '#666', 'margin-top': '10px'})
            #                 ])
            #             ])
            #         ], width=6),
            #         dbc.Col([
            #             html.Div([
            #                 html.H5("Flujo de Datos"),
            #             html.Div([
            #                     html.Div([
            #                         "🔄 Diagrama de Flujo de Datos",
            #                         html.Br(),
            #                         html.Small("(Imagen en desarrollo)", style={'color': '#666'})
            #                     ], style={
            #                         'width': '100%',
            #                         'height': '200px',
            #                         'border': '2px dashed #ccc',
            #                         'border-radius': '8px',
            #                         'background-color': '#f8f9fa',
            #                         'color': '#6c757d',
            #                         'display': 'flex',
            #                         'align-items': 'center',
            #                         'justify-content': 'center',
            #                         'flex-direction': 'column',
            #                         'text-align': 'center'
            #                     }),
            #                     html.P("Espacio para diagrama del flujo de datos", 
            #                            style={'color': '#666', 'margin-top': '10px'})
            #                 ])
            #             ])
            #         ], width=6)
            #     ])
            # ], className="mb-4")
        ], style=STYLES['container'])
    
    @staticmethod
    def _create_credits_section() -> html.Div:
        """Crea la sección de créditos y contacto"""
        return html.Div([
            dbc.Card([
                dbc.CardHeader([
                    html.H4("👥 Créditos y Contacto", className="mb-0")
                ], style={'background-color': COLORS['success'], 'color': 'white'}),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H5("Autores"),
                            html.P([
                                "Olmo Zavala-Romero, Pedro A. Segura-Chavez, Pablo Camacho-Gonzalez, Jorge Zavala-Hidalgo, ",
                                "Pavel Oropeza-Alfaro, Rosario Romero-Centeno, Octavio Gomez-Ramos"
                            ]),
                            html.H5("Contacto"),
                            html.P([
                                html.Strong("Pedro A. Segura-Chavez: "),
                                html.A("psegura@atmosfera.unam.mx", href="mailto:psegura@atmosfera.unam.mx", style={'color': '#007bff'})
                            ])
                        ], width=6),
                        dbc.Col([
                            html.H5("Instituciones Participantes"),
                            html.P([
                                html.Strong("Universidad Nacional Autónoma de México"), html.Br(),
                                "Instituto de Ciencias de la Atmósfera y Cambio Climático", html.Br(),
                                "Coyoacán, Ciudad de México 04510, México", html.Br(),
                                html.Br(),
                                html.Strong("Florida State University"), html.Br(),
                                "Department of Scientific Computing", html.Br(),
                                "Tallahassee, FL 32306, USA"
                            ]),
                            html.H5("Financiamiento"),
                            html.P([
                                "PROYECTO FINANCIADO CON RECURSOS DEL FIDEICOMISO 1490 PARA APOYAR LOS PROGRAMAS, PROYECTOS Y ACCIONES AMBIENTALES DE LA MEGALÓPOLIS.", html.Br(),
                                html.Br(),
                                "Estancia posdoctoral realizada gracias al Programa de Becas Posdoctorales en la Universidad Nacional Autónoma de México (Pedro A. Segura Chávez)"
                            ])
                        ], width=6)
                    ])
                ])
            ], className="mb-4")
        ], style=STYLES['container'])
    
    @staticmethod
    def _create_navigation_cards() -> dbc.Row:
        """Crea tarjetas de navegación para la página de acerca"""
        return layout_containers.create_action_cards_row([
            card_components.create_action_card(
                title="Volver al Inicio",
                description="Regresar a la página principal con mapa y pronósticos",
                button_text="Ir al Inicio",
                button_href="/",
                button_color="primary"
            ),
            card_components.create_action_card(
                title="Otros Contaminantes",
                description="Ver pronósticos de PM2.5, PM10 y otros contaminantes",
                button_text="Ver Contaminantes",
                button_href="/otros-contaminantes",
                button_color="success"
            )
        ])


class DebugResumenPage:
    """Página de debug para el resumen del pronóstico de ozono"""
    
    @staticmethod
    def layout(**kwargs) -> List[Any]:
        """Layout para la página de debug que solo muestra el cuadro de resumen"""
        return [
            # Header con título
            header_components.create_page_title("Debug - Resumen de Pronóstico"),
            
            # Cuadro de resumen desde base de datos (original)
            html.Div([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Resumen desde Base de Datos", style={
                            'font-size': '16px',
                            'font-weight': 'bold',
                            'margin-bottom': '10px',
                            'text-align': 'center',
                            'color': COLORS['text']
                        }),
                        html.Div(
                            id='ozone-max-summary-content-debug',
                            children=[  
                                html.P(
                                    "Cargando resumen del pronóstico...",
                                    style={
                                        'font-size': '18px',
                                        'font-family': 'Helvetica',
                                        'color': COLORS['text'],
                                        'margin': '0',
                                        'text-align': 'center'
                                    }
                                )
                            ],
                            style={
                                'padding': '15px',
                                'text-align': 'center'
                            }
                        )
                    ])
                ], style={
                    'background-color': COLORS['card'],
                    'border': f'2px solid {COLORS.get("border", "#e0e0e0")}',
                    'border-radius': '8px',
                    'box-shadow': '0 2px 8px rgba(0,0,0,0.1)',
                    'margin': '20px 0'
                })
            ], style=STYLES['container']),
            
            # Cuadro de resumen desde API externa
            html.Div([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Resumen desde API Externa", style={
                            'font-size': '16px',
                            'font-weight': 'bold',
                            'margin-bottom': '10px',
                            'text-align': 'center',
                            'color': COLORS['text']
                        }),
                        html.Div(
                            id='ozone-max-summary-api-debug',
                            children=[
                                html.P(
                                    "Cargando datos de la API...",
                                    style={
                                        'font-size': '18px',
                                        'font-family': 'Helvetica',
                                        'color': COLORS['text'],
                                        'margin': '0',
                                        'text-align': 'center'
                                    }
                                )
                            ],
                            style={
                                'padding': '15px',
                                'text-align': 'center'
                            }
                        )
                    ])
                ], style={
                    'background-color': COLORS['card'],
                    'border': f'2px solid {COLORS.get("border", "#e0e0e0")}',
                    'border-radius': '8px',
                    'box-shadow': '0 2px 8px rgba(0,0,0,0.1)',
                    'margin': '20px 0'
                })
            ], style=STYLES['container']),
            
            # Componente oculto para disparar el callback al cargar la página
            dcc.Location(id='debug-resumen-location', refresh=False)
        ]


# Instancias globales de las páginas
home_page = HomePage()
otros_contaminantes_page = OtrosContaminantesPage()
historicos_page = HistoricosPage()
acerca_page = AcercaPage()
debug_resumen_page = DebugResumenPage()

# Funciones de conveniencia para compatibilidad
def layout_home(**kwargs):
    """Función de conveniencia para layout de página principal"""
    return home_page.layout(**kwargs)

def layout_otros_contaminantes(**kwargs):
    """Función de conveniencia para layout de otros contaminantes"""
    return otros_contaminantes_page.layout(**kwargs)

def layout_historicos(**kwargs):
    """Función de conveniencia para layout de página históricos"""
    return historicos_page.layout(**kwargs)

def layout_acerca(**kwargs):
    """Función de conveniencia para layout de página acerca"""
    return acerca_page.layout(**kwargs)

def layout_debugresumen(**kwargs):
    """Función de conveniencia para layout de página debug resumen"""
    return debug_resumen_page.layout(**kwargs) 
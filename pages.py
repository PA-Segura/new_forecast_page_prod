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
    indicator_components
)
from visualization import create_indicators, create_professional_map
from config import DEFAULT_DATE_CONFIG, STYLES, COLORS


def get_forecast_datetime_str() -> str:
    """Obtiene la fecha/hora del pronóstico formateada para mostrar en el título"""
    if DEFAULT_DATE_CONFIG['use_specific_date']:
        # Usar fecha específica configurada
        forecast_datetime = datetime.strptime(DEFAULT_DATE_CONFIG['specific_date'], '%Y-%m-%d %H:%M:%S')
    else:
        # Usar fecha actual
        forecast_datetime = datetime.now().replace(minute=0, second=0, microsecond=0)
    
    # Formatear de manera más clara y legible
    # Ejemplo: "a las 14:00 hrs. del 15 de Mayo de 2023"
    hour_str = forecast_datetime.strftime('%H:%M')
    day_str = forecast_datetime.strftime('%d')
    month_names = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
        7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }
    month_str = month_names[forecast_datetime.month]
    year_str = forecast_datetime.strftime('%Y')
    
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
            # Header fusionado con logo y selector de estación
            header_components.create_logo_with_station_selector(
                dropdown_id='station-dropdown-home',
                default_value=id_est
            ),
            
            # Título fusionado con cintillo - COMENTADO (ahora está en el navbar)
            # header_components.create_fused_title_header(),
            
            # Mapa de estaciones - Inicializado directamente (estilo vdev8)
            html.Div([
                html.H3('Pronóstico de Concentración Máxima en Próximas 24 horas', style=STYLES['title']),
                dcc.Graph(
                    id="stations-map",
                    figure=create_professional_map(),  # Inicializar directamente
                    style={'height': '400px'},
                    config={'scrollZoom': False, 'displayModeBar': False}
                )
            ], style=STYLES['container']),
            
            # Serie temporal de Ozono (estilo vdev8) - CON FECHA/HORA DEL PRONÓSTICO
            html.Div([
                html.H3(f'Concentraciones de Ozono (ppb) - {forecast_time_str}', style=STYLES['title']),
                dcc.Graph(id="o3-timeseries-home", config={'displayModeBar': False})
            ], style=STYLES['container']),
            
            # Material particulado (PM2.5 y PM10) - estilo vdev8
            html.Div([
                # PM10
                html.Div([
                    html.H3(f'Concentraciones de PM10 (µg/m³) {forecast_time_str}', style=STYLES['title']),
                    dcc.Graph(id="pm10-timeseries-home", config={'displayModeBar': False})
                ], style=STYLES['container']),
                
                # PM2.5
                html.Div([
                    html.H3(f'Concentraciones de PM2.5 (µg/m³) - {forecast_time_str}', style=STYLES['title']),
                    dcc.Graph(id="pm25-timeseries-home", config={'displayModeBar': False})
                ], style=STYLES['container'])
            ]),
            
            # Grid de diales al final (estilo vdev8)
            html.Div([
                html.H3('Probabilidades de superar umbrales', style=STYLES['title']),
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
            
            # Selectores
            layout_containers.create_responsive_selector_row(
                left_component=selector_components.create_pollutant_dropdown(
                    dropdown_id='pollutant-dropdown',
                    default_value=pollutant
                ),
                right_component=selector_components.create_station_dropdown(
                    dropdown_id='station-dropdown-otros',
                    default_value=id_est
                )
            ),
            
            # Nota explicativa sobre tipos de pronóstico
            dbc.Row([
                dbc.Col([
                    alert_components.create_pollutant_info_alert()
                ], width=12)
            ]),
            
            # Gráfico principal
            dbc.Row([
                dbc.Col([
                    html.Div(id="pollutant-timeseries-container", children=[
                        html.Div("Selecciona un contaminante y estación para ver los datos", 
                               className="text-center text-muted p-4")
                    ])
                ], width=12)
            ], className="mb-4"),
            
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
                    html.H4("📖 Cómo usar el sistema", className="mb-0")
                ], style={'background-color': COLORS['gradient_start'], 'color': 'white'}),
                dbc.CardBody([
                    html.Div([
                        html.H5("Selección de Estación"),
                        html.P([
                            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. ",
                            "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat."
                        ]),
                        html.H5("Interpretación del Mapa"),
                        html.P([
                            "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur. ",
                            "Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia deserunt mollit anim id est laborum."
                        ]),
                        html.H5("Lectura de Gráficos"),
                        html.P([
                            "Sed ut perspiciatis unde omnis iste natus error sit voluptatem accusantium doloremque laudantium, ",
                            "totam rem aperiam, eaque ipsa quae ab illo inventore veritatis et quasi architecto beatae vitae dicta sunt explicabo."
                        ])
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
                        html.H5("Redes Neuronales"),
                        html.P([
                            "Nemo enim ipsam voluptatem quia voluptas sit aspernatur aut odit aut fugit, ",
                            "sed quia consequuntur magni dolores eos qui ratione voluptatem sequi nesciunt."
                        ]),
                        html.H5("Datos de Entrada"),
                        html.P([
                            "Neque porro quisquam est, qui dolorem ipsum quia dolor sit amet, consectetur, adipisci velit, ",
                            "sed quia non numquam eius modi tempora incidunt ut labore et dolore magnam aliquam quaerat voluptatem."
                        ]),
                        html.H5("Validación del Modelo"),
                        html.P([
                            "Ut enim ad minima veniam, quis nostrum exercitationem ullam corporis suscipit laboriosam, ",
                            "nisi ut aliquid ex ea commodi consequatur? Quis autem vel eum iure reprehenderit."
                        ])
                    ])
                ])
            ], className="mb-4"),
            
            # Sección: Espacios para imágenes explicativas
            dbc.Card([
                dbc.CardHeader([
                    html.H4("📊 Visualizaciones Explicativas", className="mb-0")
                ], style={'background-color': COLORS['card'], 'color': COLORS['text']}),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.H5("Diagrama del Modelo"),
                                html.Div([
                                    html.Div([
                                        "📊 Diagrama del Modelo Neural",
                                        html.Br(),
                                        html.Small("(Imagen en desarrollo)", style={'color': '#666'})
                                    ], style={
                                        'width': '100%',
                                        'height': '200px',
                                        'border': '2px dashed #ccc',
                                        'border-radius': '8px',
                                        'display': 'flex',
                                        'align-items': 'center',
                                        'justify-content': 'center',
                                        'flex-direction': 'column',
                                        'text-align': 'center',
                                        'background-color': '#f8f9fa',
                                        'color': '#6c757d'
                                    }),
                                    html.P("Espacio para diagrama explicativo del modelo de pronóstico", 
                                           style={'text-align': 'center', 'color': '#666', 'margin-top': '10px'})
                                ])
                            ])
                        ], width=6),
                        dbc.Col([
                            html.Div([
                                html.H5("Flujo de Datos"),
                                html.Div([
                                    html.Div([
                                        "🔄 Diagrama de Flujo de Datos",
                                        html.Br(),
                                        html.Small("(Imagen en desarrollo)", style={'color': '#666'})
                                    ], style={
                                        'width': '100%',
                                        'height': '200px',
                                        'border': '2px dashed #ccc',
                                        'border-radius': '8px',
                                        'background-color': '#f8f9fa',
                                        'color': '#6c757d',
                                        'display': 'flex',
                                        'align-items': 'center',
                                        'justify-content': 'center',
                                        'flex-direction': 'column',
                                        'text-align': 'center'
                                    }),
                                    html.P("Espacio para diagrama del flujo de datos", 
                                           style={'text-align': 'center', 'color': '#666', 'margin-top': '10px'})
                                ])
                            ])
                        ], width=6)
                    ])
                ])
            ], className="mb-4")
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
                            html.H5("Desarrollo"),
                            html.P([
                                "Lorem ipsum dolor sit amet, consectetur adipiscing elit. ",
                                "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
                            ]),
                            html.H5("Contacto"),
                            html.P([
                                "Email: contacto@pronostico-aire.com",
                                html.Br(),
                                "Teléfono: +52 55 1234 5678"
                            ])
                        ], width=6),
                        dbc.Col([
                            html.H5("Instituciones Participantes"),
                            html.P([
                                "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris ",
                                "nisi ut aliquip ex ea commodo consequat."
                            ]),
                            html.H5("Financiamiento"),
                            html.P([
                                "Duis aute irure dolor in reprehenderit in voluptate velit esse ",
                                "cillum dolore eu fugiat nulla pariatur."
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


# Instancias globales de las páginas
home_page = HomePage()
otros_contaminantes_page = OtrosContaminantesPage()
acerca_page = AcercaPage()

# Funciones de conveniencia para compatibilidad
def layout_home(**kwargs):
    """Función de conveniencia para layout de página principal"""
    return home_page.layout(**kwargs)

def layout_otros_contaminantes(**kwargs):
    """Función de conveniencia para layout de otros contaminantes"""
    return otros_contaminantes_page.layout(**kwargs)

def layout_acerca(**kwargs):
    """Función de conveniencia para layout de página acerca"""
    return acerca_page.layout(**kwargs) 
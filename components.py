"""
Módulo de componentes UI reutilizables para la aplicación.
Incluye navbar, tarjetas, selectores y otros elementos de interfaz.
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
from typing import List, Dict, Any, Optional

from config import RESPONSIVE_CONFIG, POLLUTANT_CONFIG, STYLES, COLORS
from data_service import data_service


class NavigationComponents:
    """Componentes de navegación"""
    
    @staticmethod
    def create_navbar() -> html.Div:
        """Crea barra de navegación fusionada con título completo y fondo verde profesional"""
        return html.Div([
            # Navbar superior con menú - completamente transparente
            dbc.NavbarSimple(
                children=[
                    dbc.NavItem(dbc.NavLink("Página Principal", href="/", active="exact", 
                                          style={'color': 'white', 'font-weight': 'bold', 'background': 'transparent'})),
                    dbc.NavItem(dbc.NavLink("Otros Contaminantes", href="/otros-contaminantes", active="exact",
                                          style={'color': 'white', 'font-weight': 'bold', 'background': 'transparent'})),
                    dbc.NavItem(dbc.NavLink("Acerca del Pronóstico", href="/acerca", active="exact",
                                          style={'color': 'white', 'font-weight': 'bold', 'background': 'transparent'})),
                ],
                brand="Pronóstico de Calidad del Aire Basado en Redes Neuronales:",
                brand_href="/",
                dark=True,
                color="",  # Sin color para evitar fondo por defecto
                style={
                    'background-color': 'transparent !important',
                    'background': 'none !important',
                    'margin-bottom': '0',
                    'padding': '10px 20px',
                    'border': 'none'
                },
                brand_style={
                    'font-family': 'Helvetica',
                    'color': 'white',
                    'font-size': '24px',
                    'font-weight': 'bold',
                    'text-shadow': '2px 2px 4px rgba(0,0,0,0.3)',
                    'background': 'transparent'
                }
            ),
            
            # Título completo en nueva línea
            html.Div([
                html.H1("Concentraciones de Ozono, PM10 y PM2.5", 
                        style={
                            'font-family': 'Helvetica',
                            'color': 'white',
                            'font-size': '20px',
                            'font-weight': 'bold',
                            'text-shadow': '2px 2px 4px rgba(0,0,0,0.3)',
                            'margin': '0',
                            'padding': '0 20px 15px 20px',
                            'text-align': 'center'  # Centrar el texto
                        })
            ])
        ], style={
            'background-color': COLORS["header"],  # Verde sólido en lugar de gradiente
            'box-shadow': '0 4px 6px rgba(0,0,0,0.1)',
            'border-radius': '15px',
            'margin': '20px',
            'min-height': '80px',  # Asegurar altura mínima para que se vea el fondo
            'padding': '15px'  # Agregar padding para mejor espaciado
        })


class HeaderComponents:
    """Componentes de encabezado"""
    
    @staticmethod
    def create_logo_header() -> html.Div:
        """Crea header con logo (estilo vdev8)"""
        return html.Div([
            # Logo principal (izquierda)
            html.Img(
                src='/assets/logo-mobile-icaycc.png',
                style={
                    'width': 'auto', 
                    'height': '100px',
                    'display': 'inline-block', 
                    'margin': '10px'
                }
            ),
            
            # Logo institución 2 (centro-derecha)
            html.Img(
                src='/assets/came_logo.png',
                style={
                    'width': 'auto', 
                    'height': '100px',
                    'display': 'inline-block', 
                    'margin': '10px',
                    'float': 'right'
                }
            ),
            
            # Logo institución 3 (derecha) - COMENTADO TEMPORALMENTE
            # html.Img(
            #     src='/assets/logo-mobile-icaycc.png',
            #     style={
            #         'width': '200px', 
            #         'height': 'auto',
            #         'display': 'inline-block', 
            #         'margin': '10px',
            #         'float': 'right'
            #     }
            # )
        ], style={
            'text-align': 'left', 
            'margin-top': '20px', 
            'background-color': COLORS['card'], 
            'padding': '15px', 
            'border-radius': '15px',
            'box-shadow': '0 4px 6px rgba(0,0,0,0.1)',
            'overflow': 'hidden'  # Para contener los floats
        })
    
    @staticmethod
    def create_page_title(title: str) -> html.Div:
        """Crea título de página con estilo profesional (vdev8)"""
        return html.Div([
            html.H1(title, style=STYLES['header'])
        ], style={'margin': '20px'})
    
    @staticmethod
    def create_logo_with_station_selector(dropdown_id: str = 'station-dropdown-home', default_value: str = 'PED') -> html.Div:
        """Crea header fusionado con logo y selector de estación"""
        return html.Div([
            # Logo principal a la izquierda
            html.Div([
                html.Img(
                    src='/assets/logo-mobile-icaycc.png',
                    style={
                        'width': 'auto', 
                        'height': '100px',
                        'display': 'inline-block', 
                        'margin': '10px'
                    }
                ),
            ], style={'display': 'inline-block', 'vertical-align': 'middle'}),
            
            # Logo institución 2 (centro)
            html.Div([
                html.Img(
                    src='/assets/came_logo.png',  #logo-institucion2.png
                    style={
                        'width': 'auto', 
                        'height': '100px',
                        'display': 'inline-block', 
                        'margin': '10px'
                    }
                ),
            ], style={'display': 'inline-block', 'vertical-align': 'middle', 'margin-left': '20px'}),
            
            # Logo institución 3 (derecha) - COMENTADO TEMPORALMENTE
            # html.Div([
            #     html.Img(
            #         src='/assets/logo-mobile-icaycc.png',  # Usando logo por defecto
            #         style={
            #             'width': 'auto', 
            #             'height': '100px',
            #             'display': 'inline-block', 
            #             'margin': '10px'
            #         }
            #     ),
            # ], style={'display': 'inline-block', 'vertical-align': 'middle', 'margin-left': '20px'}),
            
            # Selector de estación a la derecha
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
                    id=dropdown_id,
                    options=[{'label': station_info['name'], 'value': code}
                            for code, station_info in data_service.get_all_stations().items()],
                    value=default_value,
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
                'display': 'inline-block', 
                'float': 'right',
                'margin-top': '15px',
                'margin-right': '20px'
            }),
            
            # Espacio adicional para mejorar estética del contenedor
            html.Div([
                html.Span("", style={'color': 'transparent'})  # Texto invisible para alargar
            ], style={
                'clear': 'both',
                'height': '15px',
                'width': '100%'
            })
        ], style={
            'text-align': 'left', 
            'margin-top': '20px', 
            'background-color': COLORS['card'], 
            'padding': '15px', 
            'border-radius': '15px',
            'box-shadow': '0 4px 6px rgba(0,0,0,0.1)',
            'overflow': 'visible'
        })
    
    @staticmethod
    def create_fused_title_header() -> html.Div:
        """Crea header fusionado con cintillo y título completo"""
        return html.Div([
            html.H1("Pronóstico de Calidad del Aire Basado en Redes Neuronales: Concentraciones de Ozono, PM10 y PM2.5", 
                    style={
                        'font-family': 'Helvetica',
                        'color': 'white',
                        'padding': '20px',
                        'font-size': '28px',
                        'font-weight': 'bold',
                        'text-shadow': '2px 2px 4px rgba(0,0,0,0.3)',
                        'background': f'linear-gradient(135deg, {COLORS["gradient_start"]}, {COLORS["gradient_end"]})',
                        'border-radius': '15px',
                        'box-shadow': '0 4px 6px rgba(0,0,0,0.1)',
                        'margin': '0',
                        'text-align': 'center'
                    })
        ], style={'margin': '20px'})


class SelectorComponents:
    """Componentes de selectores"""
    
    @staticmethod
    def create_station_dropdown(dropdown_id: str = 'station-dropdown', default_value: str = 'PED') -> html.Div:
        """Crea selector de estación con estilo profesional (vdev8)"""
        return html.Div([
            html.Label('Seleccionar estación:', style=STYLES['label']),
            dcc.Dropdown(
                id=dropdown_id,
                options=[{'label': station_info['name'], 'value': code}
                        for code, station_info in data_service.get_all_stations().items()],
                value=default_value,
                style=STYLES['dropdown']
            )
        ], style={
            'width': '100%', 
            'margin': '20px', 
            'padding': '25px', 
            'background-color': COLORS['card'], 
            'border-radius': '15px',
            'box-shadow': '0 4px 6px rgba(0,0,0,0.1)'
        })
    
    @staticmethod
    def create_pollutant_dropdown(dropdown_id: str = 'pollutant-dropdown', default_value: str = 'O3') -> html.Div:
        """Crea selector de contaminante con estilo profesional"""
        return html.Div([
            html.Label('Seleccionar contaminante:', style=STYLES['label']),
            dcc.Dropdown(
                id=dropdown_id,
                options=[{'label': config['name'], 'value': key}
                        for key, config in POLLUTANT_CONFIG.items()],
                value=default_value,
                style=STYLES['dropdown']
            )
        ], style={
            'width': '100%', 
            'margin': '20px', 
            'padding': '25px', 
            'background-color': COLORS['card'], 
            'border-radius': '15px',
            'box-shadow': '0 4px 6px rgba(0,0,0,0.1)'
        })


class CardComponents:
    """Componentes de tarjetas"""
    
    @staticmethod
    def create_info_card(title: str, content: str, is_small: bool = False) -> dbc.Card:
        """Crea tarjeta de información con estilo profesional"""
        return dbc.Card([
            dbc.CardBody([
                html.H5(title, className="card-title"),
                html.P(content, className="card-text")
            ])
        ], style=STYLES['container'] if not is_small else {
            'margin': '10px',
            'padding': '15px',
            'border-radius': '10px',
            'box-shadow': '0 4px 8px rgba(0,0,0,0.1)',
            'background-color': COLORS['card']
        })
    
    @staticmethod
    def create_action_card(title: str, description: str, button_text: str, 
                          button_href: str, button_color: str = "primary", 
                          button_size: str = "md") -> dbc.Card:
        """Crea tarjeta de acción con estilo profesional"""
        return dbc.Card([
            dbc.CardBody([
                html.H5(title, className="card-title"),
                html.P(description, className="card-text"),
                dbc.Button(button_text, href=button_href, color=button_color, 
                          size=button_size, className="mt-3")
            ])
        ], style=STYLES['container'])


class AlertComponents:
    """Componentes de alertas"""
    
    @staticmethod
    def create_pollutant_info_alert() -> dbc.Alert:
        """Crea alerta informativa sobre tipos de pronóstico"""
        return dbc.Alert([
            html.H6("ℹ️ Información sobre pronósticos:", className="alert-heading"),
            html.P([
                "• O₃: Pronósticos por estación con intervalos de predicción",
                html.Br(),
                "• Otros contaminantes: Valores regionales (promedio, mínimo, máximo) + observaciones por estación"
            ])
        ], color="info", style={
            'border-radius': '10px',
            'box-shadow': '0 2px 4px rgba(0,0,0,0.1)'
        })


class LayoutContainers:
    """Contenedores de layout"""
    
    @staticmethod
    def create_responsive_selector_row(left_component: Any, right_component: Any) -> dbc.Row:
        """Crea fila responsiva de selectores"""
        return dbc.Row([
            dbc.Col(left_component, xs=12, sm=12, md=6, lg=6),
            dbc.Col(right_component, xs=12, sm=12, md=6, lg=6)
        ], className="mb-4")
    
    @staticmethod
    def create_timeseries_and_indicators_row(timeseries_title: str, timeseries_id: str,
                                           indicators_title: str, indicators_content: List[Any]) -> dbc.Row:
        """Crea fila con serie temporal e indicadores"""
        return dbc.Row([
            # Serie temporal
            dbc.Col([
                html.Div([
                    html.H3(timeseries_title, style=STYLES['title']),
                    dcc.Graph(id=timeseries_id, config={'displayModeBar': False})
                ], style=STYLES['container'])
            ], width=12, className="mb-4"),
            
            # Indicadores
            dbc.Col([
                html.Div([
                    html.H3(indicators_title, style=STYLES['title']),
                    indicators_content
                ], style=STYLES['container'])
            ], width=12)
        ])
    
    @staticmethod
    def create_dual_chart_row(left_title: str, left_graph_id: str,
                             right_title: str, right_graph_id: str) -> dbc.Row:
        """Crea fila con dos gráficos lado a lado"""
        return dbc.Row([
            dbc.Col([
                html.Div([
                    html.H4(left_title, style=STYLES['title']),
                    dcc.Graph(id=left_graph_id, config={'displayModeBar': False})
                ], style=STYLES['container'])
            ], xs=12, md=6),
            dbc.Col([
                html.Div([
                    html.H4(right_title, style=STYLES['title']),
                    dcc.Graph(id=right_graph_id, config={'displayModeBar': False})
                ], style=STYLES['container'])
            ], xs=12, md=6)
        ])
    
    @staticmethod
    def create_action_cards_row(cards: List[Any]) -> dbc.Row:
        """Crea fila de tarjetas de acción"""
        return dbc.Row([
            dbc.Col(card, xs=12, md=6) for card in cards
        ], className="mb-4")


class IndicatorComponents:
    """Componentes de indicadores"""
    
    @staticmethod
    def wrap_indicators_in_columns(indicators: List[Any]) -> html.Div:
        """Envuelve indicadores en columnas responsivas"""
        return html.Div([
            html.Div([
                dcc.Graph(
                    id=f'dial_{i}', 
                    figure=indicators[i], 
                    config={'displayModeBar': False}
                )
            ], style={
                'width': '50%', 
                'height': '90%', 
                'display': 'inline-block',
                'min-width': '300px',
                'margin-bottom': '20px'
            }) 
            for i in range(len(indicators))
        ], style={
            'width': '100%',
            'display': 'flex',
            'flex-wrap': 'wrap',
            'justify-content': 'center',
            'gap': '20px'
        })


# Instancias globales de los componentes para fácil acceso
nav_components = NavigationComponents()
selector_components = SelectorComponents()
card_components = CardComponents()
alert_components = AlertComponents()
header_components = HeaderComponents()
layout_containers = LayoutContainers()
indicator_components = IndicatorComponents()

# Funciones de conveniencia
def create_navbar():
    """Función de conveniencia para crear navbar"""
    return nav_components.create_navbar() 

"""
Aplicación principal refactorizada de pronóstico de calidad del aire.
Versión modular y profesional de dash_multipage_prototype.py

Esta aplicación mantiene todas las funcionalidades originales pero con una
arquitectura modular que facilita el mantenimiento y extensión.

🔒 CONFIGURACIÓN DE SEGURIDAD PARA PRODUCCIÓN:
- Debug mode: DESACTIVADO por defecto
- Host binding: 127.0.0.1 (solo localhost) por defecto
- Configuración desde .netrc para personalización segura
- Validación automática de configuración de seguridad
"""

import dash
from dash import Dash, html
import dash_bootstrap_components as dbc
import os
import netrc

# Importar módulos refactorizados
from config import config_manager, COLORS, is_sqlite_mode, get_sqlite_config, is_postgresql_mode, get_postgresql_config
from components import create_navbar
from pages import layout_home, layout_otros_contaminantes, layout_historicos, layout_acerca
from callbacks import initialize_callbacks

# Importar servicio PostgreSQL (sistema principal)
try:
    from postgres_data_service import initialize_postgres_system
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

# Importar servicio SQLite (fallback)
try:
    from sqlite_data_service import get_sqlite_service, close_sqlite_connections
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

# Configuración simple de la aplicación
APP_CONFIG = {
    'title': 'Pronóstico de Calidad del Aire Mediante Redes Neuronales: Nivel de Ozono de la RAMA',
    'suppress_callback_exceptions': True,
    'debug': False,  # Debug desactivado por seguridad
    'host': '127.0.0.1',  # Solo localhost por seguridad
    'port': 6006  # Puerto para debug en localhost
    # 'port': 8888  # Puerto original comentado como referencia
}

class AirQualityApp:
    """Aplicación principal de pronóstico de calidad del aire"""
    
    def __init__(self):
        self.app = None
        self.callback_manager = None
        self._load_secure_config()  # Cargar configuración segura
        self._validate_security_config()  # Validar configuración de seguridad
        self._initialize_app()
        self._setup_pages()
        self._setup_layout()
        self._initialize_callbacks()
    
    def _load_secure_config(self):
        """Carga configuración segura desde .netrc si está disponible"""
        try:
            n = netrc.netrc()
            
            # Intentar leer configuración de app desde .netrc
            try:
                login, account, password = n.authenticators('APP-CONFIG')
                if account:  # account puede contener host
                    APP_CONFIG['host'] = account
                if password:  # password puede contener port
                    try:
                        port_from_netrc = int(password)
                        # Si el puerto en .netrc es 8888, usar 6006 en su lugar
                        if port_from_netrc == 8888:
                            APP_CONFIG['port'] = 6006
                            print("✅ Puerto cambiado de 8888 a 6006 (puerto 8888 en uso)")
                        else:
                            APP_CONFIG['port'] = port_from_netrc
                    except ValueError:
                        pass  # Mantener puerto por defecto si no es válido
                print("✅ Configuración de app cargada desde .netrc")
            except:
                # No hay configuración de app en .netrc, usar valores por defecto
                pass
                
        except (FileNotFoundError, netrc.NetrcParseError):
            # No hay archivo .netrc, usar valores por defecto
            pass
        
        # Asegurar que el puerto sea 6006 (sobrescribir cualquier valor anterior si es 8888)
        if APP_CONFIG.get('port') == 8888:
            APP_CONFIG['port'] = 6006
            print("✅ Puerto forzado a 6006 (puerto 8888 en uso)")
    
    def _validate_security_config(self):
        """Valida la configuración de seguridad de la aplicación."""
        security_warnings = []
        
        # Verificar debug mode en producción
        if APP_CONFIG['debug']:
            security_warnings.append("⚠️ DEBUG MODE ACTIVADO - RIESGO DE SEGURIDAD")
        
        # Verificar host binding inseguro (pero permitir para nginx)
        if APP_CONFIG['host'] == '0.0.0.0':
            security_warnings.append("⚠️ HOST 0.0.0.0 - Solo usar si tienes nginx configurado")
            print("ℹ️ Configuración para nginx (proxy reverso) detectada")
        elif APP_CONFIG['host'] == '127.0.0.1':
            print("✅ Configuración segura para desarrollo local")
        
        # Mostrar advertencias si las hay
        if security_warnings:
            print("🚨 ADVERTENCIAS DE SEGURIDAD:")
            for warning in security_warnings:
                print(f"   {warning}")
        else:
            print("✅ Configuración de seguridad válida")
    
    def _initialize_app(self):
        """Inicializa la aplicación Dash con configuración"""
        
        # Mostrar configuración actual
        print(f"🎯 Configuración de la aplicación:")
        print(f"   - Debug: {APP_CONFIG['debug']}")
        print(f"   - Host: {APP_CONFIG['host']}")
        print(f"   - Puerto: {APP_CONFIG['port']}")
        print(f"   - Assets: usando directorio ./assets")
        
        # Mostrar información de seguridad
        print(f"🔒 Configuración de seguridad:")
        print(f"   - Debug mode: {'❌ ACTIVADO' if APP_CONFIG['debug'] else '✅ DESACTIVADO'}")
        if APP_CONFIG['host'] == '0.0.0.0':
            print(f"   - Host binding: {'⚠️ 0.0.0.0 (para nginx)'}")
        elif APP_CONFIG['host'] == '127.0.0.1':
            print(f"   - Host binding: {'✅ SEGURO (localhost)'}")
        else:
            print(f"   - Host binding: {'ℹ️ PERSONALIZADO'}")
        
        # Mostrar información de bases de datos
        postgresql_mode = is_postgresql_mode()
        sqlite_mode = is_sqlite_mode()
        
        print(f"   - PostgreSQL: {'ACTIVADO' if postgresql_mode else 'DESACTIVADO'}")
        print(f"   - SQLite: {'ACTIVADO' if sqlite_mode else 'DESACTIVADO'}")
        
        # Inicializar sistema PostgreSQL si está activado
        if postgresql_mode and POSTGRES_AVAILABLE:
            try:
                if initialize_postgres_system():
                    print("   ✅ Sistema PostgreSQL de producción inicializado correctamente")
                    postgres_config = get_postgresql_config()
                    print(f"   - BD PostgreSQL: {postgres_config['database']}@{postgres_config['host']}")
                    print(f"   - ID Pronóstico: {postgres_config.get('forecast_id', 7)}")
                    
                    # Obtener última fecha de pronóstico disponible
                    try:
                        from postgres_data_service import get_last_available_date
                        last_forecast_date = get_last_available_date()
                        if last_forecast_date:
                            print(f"   - Último pronóstico: {last_forecast_date}")
                        else:
                            print(f"   - Último pronóstico: No disponible")
                    except Exception as e:
                        print(f"   - Error obteniendo último pronóstico PostgreSQL: {e}")
                else:
                    print("   ⚠️ Sistema PostgreSQL no pudo inicializarse")
            except Exception as e:
                print(f"   ❌ Error inicializando PostgreSQL: {e}")
        
        # Información SQLite (fallback)
        elif sqlite_mode and SQLITE_AVAILABLE:
            sqlite_config = get_sqlite_config()
            print(f"   - BD Pronósticos: {sqlite_config['forecast_db_path']}")
            print(f"   - BD Históricos: {sqlite_config['historical_db_path']}")
            
            # Obtener última fecha de pronóstico disponible
            try:
                sqlite_service = get_sqlite_service()
                last_forecast_date = sqlite_service.get_last_forecast_date()
                if last_forecast_date:
                    print(f"   - Último pronóstico: {last_forecast_date}")
                else:
                    print(f"   - Último pronóstico: No disponible")
            except Exception as e:
                print(f"   - Error obteniendo último pronóstico SQLite: {e}")
        else:
            print("   ⚠️ Ningún sistema de base de datos activo - usando modo mock")
        
        # assets_folder se usa por defecto como "./assets"
        self.app = Dash(
            __name__, 
            use_pages=True,
            pages_folder="",
            external_stylesheets=[dbc.themes.BOOTSTRAP],
            title=APP_CONFIG['title'],
            suppress_callback_exceptions=APP_CONFIG['suppress_callback_exceptions']
        )
        
        # Configurar CSS personalizado para responsividad
        self._setup_custom_css()
        
        # Configurar favicon usando assets
        self._setup_favicon()
        
        print("✅ Aplicación Dash inicializada")
    
    def _setup_favicon(self):
        """Configura el favicon de la aplicación"""
        # El favicon se configura automáticamente si existe en assets/favicon.ico
        # Dash busca automáticamente este archivo
        print("✅ Favicon configurado (assets/favicon.ico)")
    
    def _setup_pages(self):
        """Configura las páginas de la aplicación"""
        # Registrar página principal
        dash.register_page(
            "home",
            path="/",
            title="Home - Calidad del Aire",
            name="Home",
            layout=layout_home
        )
        
        # Registrar página de otros contaminantes
        dash.register_page(
            "otros_contaminantes", 
            path="/otros-contaminantes",
            title="Otros Contaminantes - Calidad del Aire",
            name="Otros Contaminantes",
            layout=layout_otros_contaminantes
        )
        
        # Registrar página de pronósticos históricos
        dash.register_page(
            "historicos", 
            path="/historicos",
            title="Pronósticos Históricos - Calidad del Aire",
            name="Históricos",
            layout=layout_historicos
        )
        
        # Registrar página de información del sistema
        dash.register_page(
            "acerca", 
            path="/acerca",
            title="Acerca del Pronóstico - Calidad del Aire",
            name="Acerca del Pronóstico",
            layout=layout_acerca
        )
        
        print("✅ Páginas registradas correctamente")
    
    def _setup_layout(self):
        """Configura el layout principal de la aplicación con estilo vdev8"""
        self.app.layout = html.Div([
            create_navbar(),
            
            # Banner de mantenimiento
            html.Div([
                html.Div([
                    html.Span("🚧", style={'font-size': '24px', 'margin-right': '10px'}),
                    html.Span("Sitio en fase de pruebas y depuración.", 
                             style={'font-size': '16px', 'font-weight': 'bold'})
                ], style={
                    'background-color': '#FFF3CD',
                    'color': '#856404',
                    'border': '1px solid #FFEAA7',
                    'padding': '15px 20px',
                    'text-align': 'center',
                    'border-radius': '8px',
                    'margin': '20px',
                    'box-shadow': '0 2px 4px rgba(0,0,0,0.1)',
                    'font-family': 'Helvetica, Arial, sans-serif'   
                })
            ]),
            
            # Contenedor para las páginas con fondo
            dash.page_container
        ], style={
            'background-color': COLORS['background'],
            'min-height': '100vh',
            'padding': '20px'
        })
        
        print("✅ Layout principal configurado con estilo vdev8")
    
    def _initialize_callbacks(self):
        """Inicializa todos los callbacks"""
        self.callback_manager = initialize_callbacks(self.app)
    
    def _setup_custom_css(self):
        """Configura CSS personalizado para responsividad"""
        self.app.index_string = '''
        <!DOCTYPE html>
        <html>
            <head>
                {%metas%}
                <title>{%title%}</title>
                {%favicon%}
                {%css%}
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    /* Estilos responsivos personalizados */
                    @media (max-width: 768px) {
                        .dash-graph {
                            height: 300px !important;
                        }
                        h1 {
                            font-size: 1.5rem !important;
                        }
                        h3, h4 {
                            font-size: 1.2rem !important;
                        }
                        h5 {
                            font-size: 1rem !important;
                        }
                    }
                    
                    @media (max-width: 576px) {
                        .dash-graph {
                            height: 250px !important;
                        }
                        .card-body {
                            padding: 0.75rem !important;
                        }
                    }
                    
                    /* Mejorar espaciado en móviles */
                    @media (max-width: 768px) {
                        .container-fluid {
                            padding-left: 1rem !important;
                            padding-right: 1rem !important;
                        }
                    }
                    
                    /* Estilos adicionales para mejor UX */
                    .card {
                        transition: transform 0.2s ease-in-out;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }
                    
                    .card:hover {
                        transform: translateY(-2px);
                        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
                    }
                    
                    .btn {
                        transition: all 0.2s ease-in-out;
                    }
                    
                    .btn:hover {
                        transform: translateY(-1px);
                    }
                    
                    /* Mejorar legibilidad de dropdowns */
                    .Select-value-label {
                        color: #2c3e50 !important;
                    }
                    
                    /* Solucionar problema de z-index del dropdown con mapas */
                    .Select-menu-outer {
                        z-index: 9999 !important;
                    }
                    
                    .Select--is-open .Select-menu-outer {
                        z-index: 9999 !important;
                    }
                    
                    /* Asegurar que todos los dropdowns estén encima de mapas */
                    .dash-dropdown .Select-menu {
                        z-index: 9999 !important;
                    }
                    
                    .dash-dropdown .Select-menu-outer {
                        z-index: 9999 !important;
                    }
                    
                    /* Mejorar z-index general de dropdowns */
                    .dash-dropdown {
                        z-index: 1000 !important;
                        position: relative !important;
                    }
                    
                    /* Solucionar problema de recorte del dropdown */
                    .dash-dropdown .Select-menu-outer {
                        position: absolute !important;
                        top: 100% !important;
                        left: 0 !important;
                        right: 0 !important;
                        max-height: 200px !important;
                        overflow-y: auto !important;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.15) !important;
                        border: 1px solid #ccc !important;
                        border-radius: 4px !important;
                        background-color: white !important;
                    }
                    
                    /* Asegurar que el contenedor padre no recorte el dropdown */
                    .dash-dropdown .Select {
                        position: relative !important;
                    }
                    
                    /* Permitir overflow visible en contenedores de dropdowns */
                    .dash-dropdown {
                        overflow: visible !important;
                    }
                    
                    /* Estilizar la barra de herramientas del mapa y gráficos */
                    #stations-map .modebar,
                    #o3-timeseries-home .modebar {
                        background-color: rgba(128, 128, 128, 0.7) !important;
                        border-radius: 8px !important;
                        padding: 4px !important;
                        backdrop-filter: blur(10px) !important;
                        -webkit-backdrop-filter: blur(10px) !important;
                    }
                    
                    #stations-map .modebar-group,
                    #o3-timeseries-home .modebar-group {
                        background-color: transparent !important;
                    }
                    
                    #stations-map .modebar-btn,
                    #o3-timeseries-home .modebar-btn {
                        color: rgba(255, 255, 255, 0.9) !important;
                        background-color: rgba(255, 255, 255, 0.1) !important;
                        border-radius: 4px !important;
                        margin: 0 2px !important;
                        transition: all 0.2s ease !important;
                    }
                    
                    #stations-map .modebar-btn:hover,
                    #o3-timeseries-home .modebar-btn:hover {
                        background-color: rgba(255, 255, 255, 0.2) !important;
                        color: white !important;
                    }
                    
                    #stations-map .modebar-btn:active,
                    #o3-timeseries-home .modebar-btn:active {
                        background-color: rgba(255, 255, 255, 0.3) !important;
                    }
                </style>
            </head>
            <body>
                {%app_entry%}
                <footer>
                    {%config%}
                    {%scripts%}
                    {%renderer%}
                </footer>
            </body>
        </html>
        '''
    
    def run(self, debug=None, host=None, port=None):
        """Ejecuta la aplicación"""
        # Usar configuraciones por defecto si no se especifican
        debug = debug if debug is not None else APP_CONFIG['debug']
        host = host if host is not None else APP_CONFIG['host']
        port = port if port is not None else APP_CONFIG['port']
        
        print(f"🚀 Iniciando aplicación en http://{host}:{port}")
        print(f"📁 Directorio de trabajo: {config_manager.geojson is not None}")
        print(f"🎯 Debug mode: {debug}")
        print(f"🔒 Host binding: {host}")
        
        # Mostrar información de configuración
        if host == '127.0.0.1':
            print("✅ Configuración segura: Solo accesible desde localhost")
        elif host == '0.0.0.0':
            print("⚠️ Configuración para nginx: Accesible desde red (asegúrate de tener nginx configurado)")
        else:
            print(f"ℹ️ Host personalizado: {host}")
        
        try:
            self.app.run_server(debug=debug, host=host, port=port)
        except KeyboardInterrupt:
            print("\n🛑 Aplicación interrumpida por el usuario")
        except Exception as e:
            print(f"❌ Error en la aplicación: {e}")
        finally:
            # Cerrar conexiones cuando la aplicación termine
            if SQLITE_AVAILABLE and is_sqlite_mode():
                try:
                    close_sqlite_connections()
                    print("🔌 Conexiones SQLite cerradas al terminar aplicación")
                except Exception as e:
                    print(f"⚠️ Error cerrando conexiones SQLite: {e}")
            
            # PostgreSQL se cierra automáticamente con su context manager
    
    def cleanup(self):
        """Limpia recursos de la aplicación"""
        # Solo cerrar conexiones SQLite cuando realmente se necesite
        # (por ejemplo, al terminar la aplicación completamente)
        pass
    
    @property
    def server(self):
        """Propiedad para acceder al servidor Flask subyacente"""
        return self.app.server


def create_app():
    """Función factory para crear la aplicación"""
    return AirQualityApp()


# Punto de entrada principal
if __name__ == '__main__':
    # Crear y ejecutar la aplicación
    app_instance = create_app()
    try:
        app_instance.run()
    except KeyboardInterrupt:
        print("\n🛑 Aplicación interrumpida")
    except Exception as e:
        print(f"❌ Error en la aplicación: {e}")
    finally:
        # Cerrar conexiones cuando la aplicación termine
        if SQLITE_AVAILABLE and is_sqlite_mode():
            try:
                close_sqlite_connections()
                print("🔌 Conexiones SQLite cerradas al terminar aplicación")
            except Exception as e:
                print(f"⚠️ Error cerrando conexiones SQLite: {e}")
        
        # PostgreSQL se cierra automáticamente con su context manager 

# Instancias globales para Gunicorn
app_instance = create_app()
app = app_instance.app
server = app_instance.server 
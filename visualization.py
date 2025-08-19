"""
Módulo de visualización para la aplicación de pronóstico de calidad del aire.
Contiene funciones para crear mapas, gráficos de series temporales e indicadores.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os
import sys

# Agregar el directorio raíz al path para importar el sistema de configuración centralizado
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar el sistema de configuración centralizado
from config import app_config, DataMode, Environment

from config import (
    COLORS, OZONE_THRESHOLDS, MAP_CONFIG, CHART_CONFIG, 
    INDICATOR_CONFIG, PROBABILITY_LABELS, config_manager, DEFAULT_DATE_CONFIG
)
from data_service import (
    get_last_otres_forecast,
    get_last_pollutant_forecast,
    get_historical_data,
    get_probabilities_from_otres_forecast,
    compute_all_stations_max_24h,
    compute_prediction_intervals,
    data_service
)

class MapVisualizer:
    """Visualizador de mapas"""
    
    @staticmethod
    def create_professional_map() -> go.Figure:
        """
        Crea mapa profesional con colores estándar de calidad del aire y máximos de 24h
        Basado en la implementación del dash_ozono_vdev8.py
        """
        # Usar fecha específica para datos reales
        if DEFAULT_DATE_CONFIG['use_specific_date']:
            fecha_actual = DEFAULT_DATE_CONFIG['specific_date']
            print(f"🗺️ Mapa usando fecha específica: {fecha_actual}")
        else:
            fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Obtener datos de máximos para todas las estaciones
        df_max_preds_db = compute_all_stations_max_24h(fecha_actual)
        
        # Crear figura con scatter mapbox
        fig_mapa = px.scatter_mapbox(
            df_max_preds_db, 
            lat='lat', 
            lon='lon', 
            color='max_pred',
            color_continuous_scale=config_manager.get_colorscale_for_map(),
            range_color=[0, MAP_CONFIG['max_value']],
            size_max=15,
            zoom=MAP_CONFIG['zoom'],
            mapbox_style=MAP_CONFIG['mapbox_style'],
            center={"lat": MAP_CONFIG['center_lat'], "lon": MAP_CONFIG['center_lon']},
            hover_name='name',
            custom_data=['id_est', 'max_pred'],
            hover_data={'id_est': False, 'lat': False, 'lon': False}
        )
        
        # Actualizar trazas con hover template personalizado
        fig_mapa.update_traces(
            marker=dict(
                size=MAP_CONFIG['marker_size'],
                symbol='circle',
                opacity=1.0
            ),
            hovertemplate='<b>%{text}</b><br>' +
                         'Máximo: %{customdata[1]:.1f} ppb<br>' +
                         '<extra></extra>',
            text=df_max_preds_db['name']  # Usar directamente la columna name
        )
        
        # Configurar layout del mapa
        mapbox_layers = MapVisualizer._get_mapbox_layers()
        
        fig_mapa.update_layout(
            mapbox_layers=mapbox_layers,
            margin={"r": 0, "t": 0, "l": 0, "b": 40},
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            hoverlabel=dict(
                bgcolor='white',
                font_size=14,
                font_family='Helvetica',
                bordercolor='rgba(0,0,0,0.1)'
            ),
            coloraxis_colorbar=MapVisualizer._get_colorbar_config(),
            annotations=MapVisualizer._get_legend_annotations(),
            autosize=True,
            height=MAP_CONFIG['height']
        )
        
        return fig_mapa
    
    @staticmethod
    def _get_mapbox_layers() -> List[Dict]:
        """Obtiene las capas del mapa (GeoJSON y fondo)"""
        mapbox_layers = []
        
        if config_manager.geojson:
            mapbox_layers.extend([
                # Fondo de la región metropolitana
                {
                    "sourcetype": "geojson",
                    "source": {
                        "type": "Feature",
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[
                                [-99.5, 19.0],  # Esquina inferior izquierda
                                [-99.5, 19.7],  # Esquina superior izquierda
                                [-98.8, 19.7],  # Esquina superior derecha
                                [-98.8, 19.0],  # Esquina inferior derecha
                                [-99.5, 19.0]   # Cerrar el polígono
                            ]]
                        }
                    },
                    "type": "fill",
                    "color": "#f5f5f0",  # Color papiro grisáceo
                    "below": "traces",
                    "opacity": 0
                },
                # Límites de la Ciudad de México
                {
                    "sourcetype": "geojson",
                    "source": config_manager.geojson,
                    "type": "fill",
                    "color": "rgba(65,144,253,0.25)",
                    "below": "traces"
                }
            ])
        
        return mapbox_layers
    
    @staticmethod
    def _get_colorbar_config() -> Dict:
        """Configuración de la barra de colores del mapa"""
        return dict(
            title=dict(
                text='Calidad del Aire',
                side='right',
                font=dict(size=14, family='Helvetica')
            ),
            tickmode='array',
            tickvals=[0, OZONE_THRESHOLDS['buena'], OZONE_THRESHOLDS['aceptable'], 
                     OZONE_THRESHOLDS['mala'], OZONE_THRESHOLDS['muy_mala']],
            ticktext=['', '', '', '', ''],  # Sin labels en la barra
            tickfont=dict(size=12, family='Helvetica'),
            len=0.6,
            thickness=15,
            outlinewidth=1,
            outlinecolor='rgba(0,0,0,0.2)',
            y=0.5,
            yanchor='middle',
            x=1.02,
            xanchor='left'
        )
    
    @staticmethod
    def _get_legend_annotations() -> List[Dict]:
        """Anotaciones de la leyenda profesional"""
        return [
            dict(
                x=0.1, y=-0.05,
                xref='paper', yref='paper',
                text='<span style="color:{}">●</span> Buena'.format(COLORS['aire_buena']),
                showarrow=False,
                font=dict(size=14, family='Helvetica'),
                xanchor='left'
            ),
            dict(
                x=0.3, y=-0.05,
                xref='paper', yref='paper',
                text='<span style="color:{}">●</span> Aceptable'.format(COLORS['aire_aceptable']),
                showarrow=False,
                font=dict(size=14, family='Helvetica'),
                xanchor='left'
            ),
            dict(
                x=0.5, y=-0.05,
                xref='paper', yref='paper',
                text='<span style="color:{}">●</span> Mala'.format(COLORS['aire_mala']),
                showarrow=False,
                font=dict(size=14, family='Helvetica'),
                xanchor='left'
            ),
            dict(
                x=0.7, y=-0.05,
                xref='paper', yref='paper',
                text='<span style="color:{}">●</span> Muy Mala'.format(COLORS['aire_muy_mala']),
                showarrow=False,
                font=dict(size=14, family='Helvetica'),
                xanchor='left'
            ),
            dict(
                x=0.9, y=-0.05,
                xref='paper', yref='paper',
                text='<span style="color:{}">●</span> Extremadamente Mala'.format(COLORS['aire_extremadamente_mala']),
                showarrow=False,
                font=dict(size=14, family='Helvetica'),
                xanchor='left'
            )
        ]


class TimeSeriesVisualizer:
    """Responsable de crear gráficos de series temporales"""
    
    @staticmethod
    def get_combined_data(pollutant: str = 'O3', station: str = 'MER', hours_back: int = 24) -> pd.DataFrame:
        """Obtiene datos históricos y de pronóstico combinados"""
        # Usar fecha dinámica cuando SQLite está activado
        from config import is_sqlite_mode, get_current_reference_date
        
        if is_sqlite_mode():
            # Usar fecha real del último pronóstico SQLite
            now = get_current_reference_date()
        elif DEFAULT_DATE_CONFIG['use_specific_date']:
            now = datetime.strptime(DEFAULT_DATE_CONFIG['specific_date'], '%Y-%m-%d %H:%M:%S')
        else:
            now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        start_time = now - timedelta(hours=hours_back)
        
        start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')
        
        stations_dict = data_service.get_all_stations()
        
        if pollutant == 'O3':
            # OZONO: Datos por estación (estructura original)
            historical_df = get_historical_data('O3', start_time_str, now_str, station=station)
            historical_df = historical_df.rename(columns={'fecha': 'timestamp', 'val': 'value'})
            
            forecast_data = get_last_otres_forecast(now_str, station=station)
            
            forecast_df = pd.DataFrame({
                'timestamp': forecast_data['timestamps'],
                'station': [station] * len(forecast_data['forecast_vector']),
                'station_name': [stations_dict[station]['name']] * len(forecast_data['forecast_vector']),
                'value': forecast_data['forecast_vector'],
                'pollutant': [pollutant] * len(forecast_data['forecast_vector']),
                'is_forecast': [True] * len(forecast_data['forecast_vector'])
            })
            
            combined_df = pd.concat([historical_df, forecast_df], ignore_index=True)
            combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
            
            return combined_df
            
        else:
            # OTROS CONTAMINANTES: Observaciones por estación + Pronósticos regionales
            historical_df = get_historical_data(pollutant, start_time_str, now_str, station=station)
            historical_df = historical_df.rename(columns={'fecha': 'timestamp', 'val': 'value'})
            historical_df['subtype'] = 'historical'
            
            # Pronóstico regional con mean/min/max (NO depende de estación)
            forecast_data = get_last_pollutant_forecast(pollutant, now_str)
            
            # Crear DataFrame para cada subtipo de pronóstico regional
            forecast_dfs = []
            for subtype in ['mean', 'min', 'max']:
                forecast_df = pd.DataFrame({
                    'timestamp': forecast_data['timestamps'],
                    'station': ['REGIONAL'] * 24,
                    'station_name': ['Pronóstico Regional'] * 24,
                    'value': forecast_data['subtypes'][subtype],
                    'pollutant': [pollutant] * 24,
                    'subtype': [subtype] * 24,
                    'is_forecast': [True] * 24
                })
                forecast_dfs.append(forecast_df)
            
            # Combinar todo
            all_forecast = pd.concat(forecast_dfs, ignore_index=True)
            combined_df = pd.concat([historical_df, all_forecast], ignore_index=True)
            combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
            
            return combined_df
    
    @staticmethod
    def create_time_series(pollutant: str = 'O3', station: str = 'MER') -> go.Figure:
        """Crea gráfico de serie temporal para un contaminante y estación"""
        
        if pollutant == 'O3':
            # =====================================
            # CAMBIO DE FUNCIÓN PULLING DATA: INEFICIENTE → EFICIENTE
            # =====================================
            #
            # COMENTARIO: Aquí es donde se cambia de una función de pulling data a otra
            #
            # ANTES (INEFICIENTE): _create_o3_comprehensive_series()
            # - Usa 30 queries individuales a get_historical_data() y get_last_otres_forecast()
            # - Total: ~60 queries SQL por carga de página
            # - Tiempo de carga: lento, alta carga en BD
            #
            # DESPUÉS (EFICIENTE): create_o3_comprehensive_series_efficient()
            # - Usa 2 queries batch: get_all_stations_historical_batch() + get_all_stations_forecast_batch()
            # - Total: ~3 queries SQL por carga de página
            # - Tiempo de carga: rápido, baja carga en BD
            # - Reducción del 95% en queries
            # =====================================
            
            # FUNCIÓN EFICIENTE: Usar la nueva implementación optimizada
            return data_service.create_o3_comprehensive_series_efficient(station)
            
            # Comentario: Para volver al approach anterior (ineficiente), descomenta la línea de abajo:
            # return TimeSeriesVisualizer._create_o3_comprehensive_series(station)
        elif pollutant in ['PM2.5', 'PM10']:
            # NUEVOS CONTAMINANTES: Usar función comprehensiva con todas las estaciones
            return TimeSeriesVisualizer._create_comprehensive_series(pollutant, station)
        else:
            # Para otros contaminantes: usar la lógica simple regional (ya eficiente)
            return TimeSeriesVisualizer._create_simple_series(pollutant, station)
    
    @staticmethod
    def _create_comprehensive_series(pollutant: str, selected_station: str = 'MER') -> go.Figure:
        """
        Crea serie temporal completa mostrando todas las estaciones históricas + pronósticos regionales
        Funciona para PM2.5, PM10 y otros contaminantes
        """
        fig = go.Figure()
        
        # Configurar tiempo usando fecha dinámica cuando SQLite está activado
        from config import is_sqlite_mode, get_current_reference_date
        
        if is_sqlite_mode():
            # Usar fecha real del último pronóstico SQLite
            now = get_current_reference_date()
            print(f"📊 Serie temporal {pollutant} completa usando fecha SQLite: {now}")
        elif DEFAULT_DATE_CONFIG['use_specific_date']:
            now = datetime.strptime(DEFAULT_DATE_CONFIG['specific_date'], '%Y-%m-%d %H:%M:%S')
            print(f"📊 Serie temporal {pollutant} completa usando fecha específica: {now}")
        else:
            now = datetime.now().replace(minute=0, second=0, microsecond=0)
        
        num_hours_past = 48
        start_time = now - timedelta(hours=num_hours_past)
        start_time_str = start_time.strftime('%Y-%m-%d %H:%M:%S')
        end_time_str = now.strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"⚡ SERIE TEMPORAL COMPREHENSIVA {pollutant}: mostrando todas las estaciones")
        
        # 🔥 QUERY EFICIENTE: Datos históricos de TODAS las estaciones
        df_all_historical = data_service.get_all_stations_historical_batch(pollutant, start_time_str, end_time_str)
        
        stations_dict = data_service.get_all_stations()
        pollutant_info = config_manager.get_pollutant_info(pollutant)
        units = pollutant_info['units']
        
        # Listas para almacenar datos de todas las estaciones
        all_historical_data = []
        
        # PASO 1: Agregar todas las estaciones (excepto la seleccionada) en gris
        for station_code, station_info in stations_dict.items():
            if station_code == selected_station:
                continue  # La estación seleccionada se agrega al final
                
            # Filtrar datos históricos de esta estación
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
                        hovertemplate=f'<b>%{{x}}</b><br>%{{y:.1f}} {units}<extra></extra>'
                    )
                )
        
        # PASO 2: Calcular y agregar promedios y máximos históricos
        if all_historical_data:
            df_historical = pd.concat(all_historical_data)
            historical_avg = df_historical.groupby('timestamp')['value'].mean().reset_index()
            historical_max = df_historical.groupby('timestamp')['value'].max().reset_index()
            
            # Promedio histórico (verde, línea punteada)
            fig.add_trace(
                go.Scatter(
                    x=historical_avg['timestamp'],
                    y=historical_avg['value'],
                    mode='lines',
                    name='Promedio Observaciones',
                    line=dict(width=2, color='green', dash='dash'),
                    showlegend=True,
                    hovertemplate=f'<b>%{{x}}</b><br>Promedio: %{{y:.1f}} {units}<extra></extra>'
                )
            )
            
            # Máximo histórico (rojo, línea punteada)
            fig.add_trace(
                go.Scatter(
                    x=historical_max['timestamp'],
                    y=historical_max['value'],
                    mode='lines',
                    name='Máximo Observaciones',
                    line=dict(width=2, color='rgba(255, 0, 0, 0.45)', dash='dash'),
                    showlegend=False,
                    hovertemplate=f'<b>%{{x}}</b><br>Máximo: %{{y:.1f}} {units}<extra></extra>'
                )
            )
        
        # PASO 3: Agregar estación seleccionada resaltada
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
                    name=f'Estación {stations_dict[selected_station]["name"]}',
                    line=dict(width=3, color='black'),
                    showlegend=True,
                    hovertemplate=f'<b>%{{x}}</b><br>%{{y:.1f}} {units}<extra></extra>'
                )
            )
        
        # PASO 4: Agregar pronósticos regionales (mean/min/max)
        forecast_data = get_last_pollutant_forecast(pollutant, end_time_str)
        
        if forecast_data and 'subtypes' in forecast_data:
            colors = {'mean': 'red', 'min': 'orange', 'max': 'darkred'}
            line_styles = {'mean': 'solid', 'min': 'dash', 'max': 'dash'}
            
            for subtype in ['mean', 'min', 'max']:
                if subtype in forecast_data['subtypes']:
                    fig.add_trace(
                        go.Scatter(
                            x=forecast_data['timestamps'],
                            y=forecast_data['subtypes'][subtype],
                            mode='lines+markers',
                            name=f'Pronóstico Regional {subtype.upper()}',
                            line=dict(
                                color=colors[subtype], 
                                width=3 if subtype == 'mean' else 2,
                                dash=line_styles[subtype]
                            ),
                            showlegend=True,
                            hovertemplate=f'<b>%{{x}}</b><br>Regional {subtype.upper()}: %{{y:.1f}} {units}<extra></extra>'
                        )
                    )
        
        # PASO 5: Configurar layout
        fig.update_layout(
            title=f'Concentraciones de {pollutant} - Todas las estaciones (Estación {stations_dict[selected_station]["name"]} resaltada)',
            xaxis_title='Tiempo',
            yaxis_title=f'Concentración ({units})',
            height=CHART_CONFIG['height'],
            autosize=True,
            margin=CHART_CONFIG['margin'],
            plot_bgcolor=COLORS['grid'],
            paper_bgcolor=COLORS['card'],
            showlegend=True,
            hovermode='closest',
            legend=dict(
                orientation='v',
                yanchor='top',
                y=1,
                xanchor='left',
                x=1.02
            )
        )
        
        print(f"🎯 Serie temporal {pollutant} comprehensiva completada: {len(all_historical_data)} estaciones históricas")
        
        return fig
    
    @staticmethod
    def _create_simple_series(pollutant: str, station: str) -> go.Figure:
        """Crea serie temporal simple para otros contaminantes (lógica original)"""
        df_station = TimeSeriesVisualizer.get_combined_data(pollutant, station, hours_back=24)
        
        fig = go.Figure()
        pollutant_info = config_manager.get_pollutant_info(pollutant)
        units = pollutant_info['units']
        stations_dict = data_service.get_all_stations()
        
        # OTROS CONTAMINANTES: Observaciones por estación + Pronósticos regionales
        historical = df_station[df_station['is_forecast'] == False]
        forecast = df_station[df_station['is_forecast'] == True]
        
        # Añadir datos históricos de la estación seleccionada
        if len(historical) > 0:
            station_name = stations_dict.get(station, {}).get('name', station)
            fig.add_trace(go.Scatter(
                x=historical['timestamp'],
                y=historical['value'],
                mode='lines+markers',
                name=f'Observaciones {station_name}',
                line=dict(color='blue', width=2),
                hovertemplate=f'<b>%{{x}}</b><br>Observado en {station_name}: %{{y:.1f}} {units}<extra></extra>'
            ))
        
        # Añadir pronósticos regionales: mean, min, max
        if len(forecast) > 0:
            colors = {'mean': 'red', 'min': 'orange', 'max': 'darkred'}
            line_styles = {'mean': 'solid', 'min': 'dash', 'max': 'dash'}
            
            for subtype in ['mean', 'min', 'max']:
                subtype_data = forecast[forecast['subtype'] == subtype]
                if len(subtype_data) > 0:
                    fig.add_trace(go.Scatter(
                        x=subtype_data['timestamp'],
                        y=subtype_data['value'],
                        mode='lines+markers',
                        name=f'Pronóstico Regional {subtype.upper()}',
                        line=dict(
                            color=colors[subtype], 
                            width=3 if subtype == 'mean' else 2,
                            dash=line_styles[subtype]
                        ),
                        hovertemplate=f'<b>%{{x}}</b><br>Regional {subtype.upper()}: %{{y:.1f}} {units}<extra></extra>'
                    ))
        
        station_name = stations_dict.get(station, {}).get('name', station)
        title = f'{pollutant} - Observaciones {station_name} + Pronóstico Regional'
        
        # Configurar layout
        fig.update_layout(
            title=title,
            xaxis_title='Tiempo',
            yaxis_title=f'Concentración ({units})',
            hovermode='closest',
            height=CHART_CONFIG['height'],
            autosize=True,
            margin=CHART_CONFIG['margin'],
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            )
        )
        
        return fig


class IndicatorVisualizer:
    """Responsable de crear indicadores (diales) de probabilidades"""
    
    @staticmethod
    def create_indicators(station: str = 'MER') -> List[Any]:
        """Crea indicadores de probabilidades con estilo profesional vdev8"""
        # Usar fecha dinámica cuando SQLite está activado
        from config import is_sqlite_mode, get_current_reference_date
        
        if is_sqlite_mode():
            # Usar fecha real del último pronóstico SQLite
            fecha_actual = get_current_reference_date().strftime('%Y-%m-%d %H:%M:%S')
            print(f"📊 Indicadores usando fecha SQLite: {fecha_actual}")
        elif DEFAULT_DATE_CONFIG['use_specific_date']:
            fecha_actual = DEFAULT_DATE_CONFIG['specific_date']
            print(f"📊 Indicadores usando fecha específica: {fecha_actual}")
        else:
            fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print(f"📊 Indicadores usando fecha actual: {fecha_actual}")
        
        # Obtener probabilidades
        probabilities = get_probabilities_from_otres_forecast(fecha_actual, station)
        
        # Labels exactos de vdev8
        labels = [
            "Media de más de 50 ppb en 8hrs",
            "Umbral de 90 ppb", 
            "Umbral de 120 ppb",
            "Umbral de 150 ppb"
        ]
        
        dial_figs = []
        for i, prob in enumerate(probabilities):
            dial_fig = IndicatorVisualizer._create_single_indicator(prob, labels[i])
            dial_figs.append(dial_fig)
        
        return dial_figs
    
    @staticmethod
    def _create_single_indicator(probability: float, label: str) -> go.Figure:
        """Crea un indicador individual con estilo profesional vdev8"""
        # Determinar color basado en probabilidad
        if probability < 0.3:
            color = COLORS['success']
        elif probability < 0.7:
            color = COLORS['warning']
        else:
            color = COLORS['danger']
        
        dial_fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=probability * 100,
                gauge={
                    'axis': {'range': [None, 100], 'tickcolor': '#333333', 'tickwidth': 2},
                    'shape': 'angular',
                    'bar': {'color': color},
                    'bgcolor': 'white',  # Fondo blanco limpio
                    'borderwidth': 2,  # Contorno oscuro
                    'bordercolor': '#333333',  # Color del contorno
                    'steps': [
                        {'range': [0, 30], 'color': '#fafbfc'},  # Gris muy muy claro para los pasos
                        {'range': [30, 70], 'color': '#f5f6f7'},  # Gris muy claro para los pasos
                        {'range': [70, 100], 'color': '#f0f1f2'}  # Gris claro para los pasos
                    ],
                    'threshold': {
                        'line': {'color': 'red', 'width': 4},
                        'thickness': 0.75,
                        'value': 100
                    }
                }
            )
        )
        
        # Estilo exacto de vdev8
        dial_fig.update_traces(
            number={'suffix': '%', 'font': {'size': 28, 'family': 'Helvetica', 'color': COLORS['text']}},
            title={'font': {'size': 18, 'family': 'Helvetica', 'color': COLORS['text']}}
        )
        
        dial_fig.update_layout(
            margin=dict(t=60, b=25, l=25, r=25),
            height=230,  # Exactamente como vdev8
            title_text=f'<b>{label}</b>',
            title_x=0.5,
            title_y=0.95,
            title_xanchor='center',
            title_yanchor='top',
            title_font=dict(family='Helvetica', size=20, color=COLORS['text']),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        return dial_fig


# Instancias globales de los visualizadores
map_visualizer = MapVisualizer()
timeseries_visualizer = TimeSeriesVisualizer()
indicator_visualizer = IndicatorVisualizer()

# Funciones de conveniencia para mantener compatibilidad con el código existente
def create_professional_map() -> go.Figure:
    """Función de conveniencia para crear mapa profesional"""
    return map_visualizer.create_professional_map()

def create_time_series(pollutant: str = 'O3', station: str = 'MER') -> go.Figure:
    """Función de conveniencia para crear serie temporal"""
    return timeseries_visualizer.create_time_series(pollutant, station)

def create_indicators(station: str = 'MER') -> List[Any]:
    """Función de conveniencia para crear indicadores"""
    return indicator_visualizer.create_indicators(station)

def get_combined_data(pollutant: str = 'O3', station: str = 'MER', hours_back: int = 24) -> pd.DataFrame:
    """Función de conveniencia para obtener datos combinados"""
    return timeseries_visualizer.get_combined_data(pollutant, station, hours_back) 
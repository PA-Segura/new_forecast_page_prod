# Instalación de Página de Visualización del Pronóstico Operativo de Calidad del Aire

## Prerrequisitos

Es necesario tener instalado un gestor de paquetes Conda/Mamba en tu sistema. Para instrucciones de instalación, visita [Mamba Installation](https://mamba.readthedocs.io/en/latest/installation/mamba-installation.html).

## Estructura del Proyecto

Este proyecto consta de dos componentes principales:

1. **Aplicación Dash** (`app.py`): Página web de visualización de pronósticos de calidad del aire
2. **API FastAPI** (`api_service.py`): Servicio REST para consultar predicciones de la base de datos

Cada componente requiere su propio entorno Conda independiente.

## Instrucciones de Instalación

### 1. Clonar el Repositorio

Clona este repositorio en tu máquina local usando `git clone`, seguido de la URL del repositorio.

```bash
git clone https://github.com/PA-Segura/new_forecast_page_prod.git
cd new_forecast_page_prod
```

### 2. Crear Entornos Conda

El proyecto utiliza dos entornos separados:

#### 2.1. Entorno para la Aplicación Dash (`forecast_dash`)

Crea el entorno para la aplicación de visualización desde el archivo `forecast_dash_env_clean.yaml`:

```bash
mamba env create -f forecast_dash_env_clean.yaml
```

#### 2.2. Entorno para la API (`forecast_api`)

Crea el entorno para el servicio API desde el archivo `environment_api.yml`:

```bash
mamba env create -f environment_api.yml
```

### 3. Activar Entornos

Dependiendo del componente que quieras ejecutar, activa el entorno correspondiente:

**Para la aplicación Dash:**
```bash
mamba activate forecast_dash
```

**Para la API:**
```bash
mamba activate forecast_api
```

### 4. Configurar Archivos de Configuración

#### 4.1. Configuración de la Aplicación Dash

Asegúrate de configurar el archivo `.netrc` con las credenciales de acceso a la base de datos de pronósticos. El archivo `.netrc` debe contener:

```
machine AMATE-SOLOREAD
login TU_USUARIO
password TU_PASSWORD
account TU_HOST

machine APP-CONFIG
login app
password 6006
account 127.0.0.1
```

Si se necesita usar Gunicorn para producción, configura el archivo `gunicorn_config.py` con el puerto, recursos y configuración apropiados.

#### 4.2. Configuración de la API

La API también utiliza el archivo `.netrc` para obtener las credenciales de la base de datos. Asegúrate de que la entrada `AMATE-SOLOREAD` esté configurada correctamente.

El archivo `gunicorn_config_api.py` ya está configurado para ejecutar la API en el puerto 8888.

### 5. Ejecución

#### 5.1. Ejecutar la Aplicación Dash

Una vez configurado el entorno y el archivo `.netrc`, puedes iniciar la aplicación Dash de las siguientes maneras:

**Modo desarrollo (directo):**
```bash
mamba activate forecast_dash
python app.py
```

**Modo producción (con Gunicorn):**
```bash
mamba activate forecast_dash
gunicorn -c gunicorn_config.py app:server
```

La aplicación estará disponible en `http://127.0.0.1:6006` (o el puerto configurado en `.netrc`), consulta con tu administrador de sistemas. 

#### 5.2. Ejecutar la API

Para ejecutar el servicio API:

**Modo desarrollo (directo):**
```bash
mamba activate forecast_api
python api_service.py
```

**Modo producción (con Gunicorn):**
```bash
mamba activate forecast_api
gunicorn -c gunicorn_config_api.py api_service:app
```

La API estando disponible en `http://0.0.0.0:8888` (o el puerto configurado).

### 6. Documentación de la API
Ejemplo de consultas:

http://0.0.0.0:8888/ai_vi_transformer01/ozono/CDMX/2025-10-21

http://0.0.0.0:8888/comp6/CDMX/0/2026-01-23/2026-01-30


## Notas

- **Seguridad**: Por defecto, la aplicación Dash está configurada para ejecutarse en `localhost` (127.0.0.1) con el modo debug desactivado.
- **Puertos**: 
  - Aplicación Dash: Puerto 6006 (desarrollo) o según configuración en `.netrc`
  - API: Puerto 8888
- **Bases de Datos**: El proyecto soporta tanto PostgreSQL (modo producción). La configuración se determina automáticamente según la disponibilidad de credenciales en `.netrc`.

## Solución de Problemas

### Error de conexión a la base de datos

Verifica que el archivo `.netrc` esté configurado correctamente y que las credenciales `AMATE-SOLOREAD` sean válidas.

### Puerto ya en uso

Si recibes un error de puerto en uso, verifica qué proceso está usando el puerto:
```bash
lsof -i :6006  # Para la app Dash
lsof -i :8888  # Para la API
```

### Problemas con entornos Conda

Si tienes problemas al crear los entornos, intenta actualizar Conda/Mamba:
```bash
conda update conda
# o
mamba update mamba
```

## Estructura de Archivos

```
new_forecast_page_prod/
├── app.py                          # Aplicación principal Dash
├── api_service.py                  # Servicio API FastAPI
├── forecast_dash_env_clean.yaml    # Entorno Conda para Dash
├── environment_api.yml             # Entorno Conda para API
├── gunicorn_config_api.py          # Configuración Gunicorn para API
├── config.py                       # Configuración general
├── components.py                   # Componentes Dash
├── pages.py                        # Páginas de la aplicación
├── callbacks.py                    # Callbacks de Dash
├── postgres_data_service.py        # Servicio de datos PostgreSQL
└── assets/                         # Archivos estáticos (imágenes, JSON, etc.)
```

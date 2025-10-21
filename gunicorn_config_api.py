"""
Configuración de Gunicorn para API FastAPI (api_service.py)
Diferente a gunicorn_config.py (Dash app) porque FastAPI usa ASGI

⚙️ CONFIGURACIÓN: Uso interno, 1 vez al día
   - 1 worker es suficiente (bajo tráfico)
   - Puerto 8888 (debe ser diferente al 8080 del Dash)
   - Solo accesible internamente (127.0.0.1)
"""

import multiprocessing
import os

# ====== CONFIGURACIÓN BÁSICA ======
# Puerto diferente al Dash app (que usa 8080)
# 0.0.0.0 → Accesible desde otras máquinas en la red interna
bind = "0.0.0.0:8888"

# Workers: 1 es suficiente para uso interno de baja frecuencia (1 vez al día)
workers = 1

# Worker class CRÍTICO: FastAPI requiere ASGI (uvicorn)
worker_class = "uvicorn.workers.UvicornWorker"

# Timeout para requests largos
timeout = 120

# ====== CONFIGURACIÓN DE CONEXIONES ======
# Keepalive para conexiones persistentes
keepalive = 5

# Graceful timeout para shutdown limpio
graceful_timeout = 30

# Máximo de conexiones simultáneas por worker
worker_connections = 1000

# ====== RESTART DE WORKERS ======
# Reiniciar workers después de X requests (previene memory leaks)
max_requests = 1000
max_requests_jitter = 50

# ====== LOGGING ======
accesslog = "-"  # stdout
errorlog = "-"   # stderr
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# ====== PERFORMANCE ======
# Usar memoria compartida en vez de disco (mejora performance)
worker_tmp_dir = "/dev/shm"

# Preload: False es mejor para apps async con asyncpg
preload_app = False

# ====== LÍMITES DE REQUEST ======
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# ====== CALLBACKS ======
def when_ready(server):
    """Cuando el servidor está listo"""
    server.log.info("🚀 API de Pronósticos iniciada en puerto 8888")

def on_exit(server):
    """Al apagar el servidor"""
    server.log.info("🔌 API de Pronósticos detenida")

def worker_int(worker):
    """Cuando un worker es interrumpido"""
    worker.log.info(f"⚠️  Worker {worker.pid} interrumpido")

def post_fork(server, worker):
    """Después de crear un worker"""
    server.log.info(f"✅ Worker {worker.pid} creado")


#!/usr/bin/env python3
"""
Script para reiniciar el servidor cada hora a la media hora.
"""

import schedule
import time
import subprocess
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('server_restart.log'),
        logging.StreamHandler()
    ]
)

def restart_server():
    """Función para reiniciar el servidor."""
    try:
        logging.info("Iniciando reinicio del servidor...")
        
        # Detener el servidor actual (ajusta el comando según tu configuración)
        subprocess.run(['pkill', '-f', 'python.*app.py'], check=False)
        time.sleep(2)  # Esperar a que se detenga completamente
        
        # Iniciar el servidor nuevamente (ajusta la ruta según tu configuración)
        subprocess.Popen(['python3', 'app.py'])
        
        logging.info("Servidor reiniciado exitosamente")
        
    except Exception as e:
        logging.error(f"Error al reiniciar el servidor: {e}")

def main():
    """Función principal del script."""
    logging.info("Iniciando script de reinicio automático del servidor")
    
    # Lanzar el servidor inmediatamente al inicio
    logging.info("Lanzando servidor por primera vez...")
    restart_server()
    
    # Programar el reinicio cada hora a la media hora (XX:30)
    schedule.every().hour.at(":45").do(restart_server)
    
    logging.info("Servidor programado para reiniciarse cada hora a la media hora")
    
    # Bucle principal
    while True:
        schedule.run_pending()
        time.sleep(60)  # Verificar cada minuto

if __name__ == "__main__":
    main() 

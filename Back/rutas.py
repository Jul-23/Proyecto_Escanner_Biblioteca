import os
import sys

def obtener_ruta_recurso(ruta_relativa):
    """Obtiene la ruta absoluta de un archivo, funcione en Python o en el .exe"""
    try:
        # PyInstaller crea una carpeta temporal y guarda la ruta en _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, ruta_relativa)
import sys, os

def resource_path(relative_path):
    """Obtiene la ruta correcta tanto en desarrollo como en el .exe empaquetado."""
    if hasattr(sys, '_MEIPASS'):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.join(os.path.dirname(__file__), '..', '..')
    return os.path.abspath(os.path.join(base_path, relative_path))
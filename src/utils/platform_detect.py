"""
Detección de plataforma para ProyectSurvivor.
Permite activar comportamientos específicos de Android/móvil.
"""
import sys


def is_android() -> bool:
    """
    Retorna True si el juego está corriendo en Android.

    Métodos de detección (de más confiable a fallback):
      1. sys.platform == 'android'   → establecido por pygame-for-android / Buildozer
      2. Módulo 'android' disponible → presente solo en entornos Kivy/p4a
      3. Variable de entorno ANDROID_ARGUMENT → inyectada por python-for-android
    """

    if sys.platform == 'android':
        return True

    try:
        import android
        return True
    except ImportError:
        pass

    import os
    if os.environ.get('ANDROID_ARGUMENT') is not None:
        return True
    if os.environ.get('ANDROID_ENTRYPOINT') is not None:
        return True

    return False


def is_mobile() -> bool:
    """
    Retorna True en Android o en cualquier plataforma considerada móvil.
    Ampliar aquí si se añade soporte para iOS en el futuro.
    """
    return is_android()
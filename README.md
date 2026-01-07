# ProyectSurvivor
Bienvenido a **ProyectSurvivor**. Sigue estas instrucciones para configurar el entorno de desarrollo y ejecutar el juego en tu máquina local.

## Prerrequisitos
* **Python 3.12** instalado en tu sistema.
    * Puedes verificar tu versión ejecutando: `python --version`

## Instalación y Configuración
Sigue estos pasos para crear un entorno virtual aislado y preparar el juego.

1. **Clonar o Descargar el proyecto:**
```bash
git clone https://github.com/elJulioDev/ProyectSurvivor.git
cd ProyectSurvivor
```

2. **Crear el Entorno Virtual (Python 3.12):**
```bash
python3.12 -m venv .venv
```

3. **Activar el Entorno Virtual:**
- Windows CMD
```bash
.venv\Scripts\activate.bat
```

4. **Instalar Dependencias:**
Con el entorno activo, instala las librerías necesarias.
```bash
pip install -r requirements.txt
```

5. **Ejecutar el Juego**
Para iniciar el juego, asegúrate de estar en la carpeta raíz del proyecto y tener el entorno virtual activado. Luego ejecuta el archivo principal que se encuentra dentro de la carpeta src.
```bash
python src/main.py
```

# ProyectSurvivor
Bienvenido a **ProyectSurvivor**. Sigue estas instrucciones para configurar el entorno de desarrollo y ejecutar el juego en tu máquina local.

## Prerrequisitos
* **[uv](https://docs.astral.sh/uv/)** instalado (gestiona solo el Python del proyecto, no hace falta instalar Python a mano).
    * Puedes verificarlo ejecutando: `uv --version`

## Instalación y Configuración
Sigue estos pasos para crear un entorno virtual aislado y preparar el juego.

1. **Clonar o Descargar el proyecto:**
```bash
git clone https://github.com/elJulioDev/ProyectSurvivor.git
cd ProyectSurvivor
```

2. **Instalar dependencias:**
`uv` crea el `.venv` (Python 3.12) y lo sincroniza con `uv.lock`.
```bash
uv sync
```

3. **Ejecutar el Juego**
Desde la raíz del proyecto:
```bash
uv run src/main.py
```

## Gestión de dependencias
`pyproject.toml` es la fuente de verdad y `uv.lock` fija las versiones exactas.
```bash
uv add <paquete>     # añade una dependencia
uv remove <paquete>  # la elimina
```

"""
Grid Espacial para optimizar colisiones de O(N*M) a O(1)
"""
from collections import defaultdict

class SpatialGrid:
    """
    Divide el mundo en celdas para acelerar búsquedas de colisiones.
    En lugar de verificar todos los enemigos contra todos los proyectiles,
    solo verificamos los que están en la misma celda.
    """
    def __init__(self, world_width, world_height, cell_size=100):
        self.cell_size = cell_size
        self.world_width = world_width
        self.world_height = world_height
        self.grid = defaultdict(list)  # {(cell_x, cell_y): [enemies]}
        
    def clear(self):
        """Limpia el grid (llamar cada frame antes de repoblar)"""
        self.grid.clear()
    
    def _get_cell(self, x, y):
        """Convierte posición mundial a coordenadas de celda"""
        cell_x = int(x // self.cell_size)
        cell_y = int(y // self.cell_size)
        return (cell_x, cell_y)
    
    def insert(self, entity):
        """Inserta entidad en su celda correspondiente"""
        cell = self._get_cell(entity.x, entity.y)
        self.grid[cell].append(entity)
    
    def get_nearby(self, x, y, radius=1):
        """
        Obtiene todas las entidades en la celda actual y las vecinas.
        radius=1 verifica 9 celdas (3x3), radius=0 solo la celda actual.
        """
        entities = []
        center_cell = self._get_cell(x, y)
        
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                cell = (center_cell[0] + dx, center_cell[1] + dy)
                entities.extend(self.grid.get(cell, []))
        
        return entities
    
    def query_rect(self, rect):
        """Obtiene todas las entidades que PODRÍAN colisionar con un rectángulo"""
        min_cell = self._get_cell(rect.left, rect.top)
        max_cell = self._get_cell(rect.right, rect.bottom)
        
        entities = []
        for cell_x in range(min_cell[0], max_cell[0] + 1):
            for cell_y in range(min_cell[1], max_cell[1] + 1):
                cell = (cell_x, cell_y)
                entities.extend(self.grid.get(cell, []))
        
        # Eliminar duplicados (una entidad grande puede estar en varias celdas)
        return list(set(entities))
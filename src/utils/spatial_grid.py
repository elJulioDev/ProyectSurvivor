"""
SpatialGrid optimizada.
- Usa dict estándar con clave int combinada (evita tuple-hash overhead).
- Separación de listas reutilizables por celda para reducir allocations.
- get_nearby() devuelve iterador directo sin list-concat intermedio.
"""

class SpatialGrid:
    def __init__(self, world_width, world_height, cell_size=100):
        self.cell_size  = cell_size
        self._inv_cell  = 1.0 / cell_size
        self.world_width  = world_width
        self.world_height = world_height
        # Clave int = cx * STRIDE + cy  (evita tuple hashing)
        self._STRIDE = (world_height // cell_size) + 2
        self.grid: dict[int, list] = {}

    def clear(self):
        # Reutilizar listas en lugar de borrarlas — reduce GC
        for lst in self.grid.values():
            lst.clear()

    def _key(self, x: float, y: float) -> int:
        return int(x * self._inv_cell) * self._STRIDE + int(y * self._inv_cell)

    def insert(self, entity):
        k = self._key(entity.x, entity.y)
        try:
            self.grid[k].append(entity)
        except KeyError:
            self.grid[k] = [entity]

    def get_nearby(self, x: float, y: float, radius: int = 1):
        cx = int(x * self._inv_cell)
        cy = int(y * self._inv_cell)
        stride = self._STRIDE
        grid   = self.grid
        result = []
        ra = range(-radius, radius + 1)
        for dx in ra:
            base = (cx + dx) * stride
            for dy in ra:
                lst = grid.get(base + cy + dy)
                if lst:
                    result.extend(lst)
        return result

    # radio=0 — solo la celda actual (más rápido para separación)
    def get_cell(self, x: float, y: float) -> list:
        return self.grid.get(self._key(x, y)) or []

    def query_rect(self, rect):
        inv = self._inv_cell
        stride = self._STRIDE
        grid = self.grid
        min_cx = int(rect.left  * inv)
        max_cx = int(rect.right * inv)
        min_cy = int(rect.top   * inv)
        max_cy = int(rect.bottom * inv)
        seen   = set()
        result = []
        for cx in range(min_cx, max_cx + 1):
            base = cx * stride
            for cy in range(min_cy, max_cy + 1):
                k = base + cy
                if k in seen:
                    continue
                seen.add(k)
                lst = grid.get(k)
                if lst:
                    result.extend(lst)
        return result
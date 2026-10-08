from tiendas_sm.repositorio import RepositorioSqlite
from tiendas_sm.servicios import (ServicioDeProductos, ServicioDeClientes,
                                  ControlCredito, ServicioDeVentas)


class Aplicacion:
    def __init__(self, ruta=":memory:"):
        self.repo = RepositorioSqlite(ruta)
        self.conexion = self.repo.conexion
        self.productos = ServicioDeProductos(self.repo)
        self.clientes = ServicioDeClientes(self.repo)
        self.credito = ControlCredito(self.repo)
        self.ventas = ServicioDeVentas(self.repo)

    def cantidad_en_inventario(self, id_producto):
        return self.repo.obtener_existencia(id_producto).cantidad_actual

    def numero_de_ventas(self):
        return self.conexion.execute("SELECT COUNT(*) FROM ventas").fetchone()[0]

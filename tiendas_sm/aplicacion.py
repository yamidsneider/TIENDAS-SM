from tiendas_sm.base_de_datos import BaseDeDatos
from tiendas_sm.repositorios import RepositorioDeProductos, RepositorioDeClientes, RepositorioDeVentasSqlite
from tiendas_sm.servicios import (ServicioDeProductos, ServicioDeClientes, ControlInventario,
                                  ControlCredito, ServicioDeVentas)


class Aplicacion:
    """Punto único donde se arma el sistema (se crean los objetos y se conectan)."""

    def __init__(self, ruta=":memory:"):
        base = BaseDeDatos(ruta)
        self.conexion = base.conexion
        self.repo_productos = RepositorioDeProductos(self.conexion)
        repo_clientes = RepositorioDeClientes(self.conexion)
        repo_ventas = RepositorioDeVentasSqlite(self.conexion)
        control_inventario = ControlInventario(self.repo_productos)
        self.credito = ControlCredito(repo_ventas)
        self.productos = ServicioDeProductos(self.repo_productos)
        self.clientes = ServicioDeClientes(repo_clientes)
        self.ventas = ServicioDeVentas(self.repo_productos, repo_clientes, repo_ventas,
                                       control_inventario, self.credito)

    def cantidad_en_inventario(self, id_producto):
        return self.repo_productos.obtener_existencia(id_producto).cantidad_actual

    def numero_de_ventas(self):
        return self.conexion.execute("SELECT COUNT(*) FROM ventas").fetchone()[0]

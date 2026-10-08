from abc import ABC, abstractmethod
from datetime import datetime

from tiendas_sm.dominio import Producto, Existencia, Cliente, CuentaPorCobrar, EstadoCuenta


def _ahora():
    return datetime.now().isoformat()


class RepositorioDeProductos:
    def __init__(self, conexion):
        self.conexion = conexion

    def guardar(self, producto):
        with self.conexion:
            if producto.id_producto is None:
                self._insertar(producto)
            else:
                self._actualizar(producto)
        return producto.id_producto

    def _insertar(self, producto):
        cursor = self.conexion.execute(
            "INSERT INTO productos (nombre, precio_compra, precio_venta, stock_minimo) VALUES (?,?,?,?)",
            (producto.nombre, producto.precio_compra, producto.precio_venta, producto.stock_minimo))
        producto.id_producto = cursor.lastrowid
        self.conexion.execute("INSERT INTO existencias (id_producto, cantidad_actual) VALUES (?, 0)",
                              (producto.id_producto,))

    def _actualizar(self, producto):
        self.conexion.execute(
            "UPDATE productos SET nombre=?, precio_compra=?, precio_venta=?, stock_minimo=? WHERE id_producto=?",
            (producto.nombre, producto.precio_compra, producto.precio_venta, producto.stock_minimo,
             producto.id_producto))

    def obtener(self, id_producto):
        fila = self.conexion.execute("SELECT * FROM productos WHERE id_producto=?", (id_producto,)).fetchone()
        return self._a_producto(fila) if fila else None

    def listar(self):
        filas = self.conexion.execute("SELECT * FROM productos ORDER BY nombre").fetchall()
        return [self._a_producto(fila) for fila in filas]

    @staticmethod
    def _a_producto(fila):
        return Producto(fila["id_producto"], fila["nombre"], fila["precio_compra"],
                        fila["precio_venta"], fila["stock_minimo"])

    def obtener_existencia(self, id_producto):
        fila = self.conexion.execute("SELECT * FROM existencias WHERE id_producto=?", (id_producto,)).fetchone()
        if fila is None:
            return None
        return Existencia(fila["id_producto"], fila["cantidad_actual"], fila["cantidad_reservada"])

    def guardar_existencia(self, existencia, tipo_movimiento, cantidad):
        with self.conexion:
            self.conexion.execute("UPDATE existencias SET cantidad_actual=? WHERE id_producto=?",
                                  (existencia.cantidad_actual, existencia.id_producto))
            self.conexion.execute(
                "INSERT INTO movimientos_inventario (id_producto, tipo, cantidad, fecha) VALUES (?,?,?,?)",
                (existencia.id_producto, tipo_movimiento, cantidad, _ahora()))


class RepositorioDeClientes:
    def __init__(self, conexion):
        self.conexion = conexion

    def guardar(self, cliente):
        with self.conexion:
            cursor = self.conexion.execute(
                "INSERT INTO clientes (nombres, credito_habilitado, limite_credito, plazo_credito_dias) "
                "VALUES (?,?,?,?)",
                (cliente.nombres, int(cliente.credito_habilitado), cliente.limite_credito,
                 cliente.plazo_credito_dias))
            cliente.id_cliente = cursor.lastrowid
        return cliente.id_cliente

    def obtener(self, id_cliente):
        fila = self.conexion.execute("SELECT * FROM clientes WHERE id_cliente=?", (id_cliente,)).fetchone()
        if fila is None:
            return None
        return Cliente(fila["id_cliente"], fila["nombres"], bool(fila["credito_habilitado"]),
                       fila["limite_credito"], fila["plazo_credito_dias"])


class RepositorioDeVentas(ABC):
    """Abstracción de la FPI-11: los servicios dependen de esta interfaz, no de SQLite."""

    @abstractmethod
    def guardar_transaccion(self, venta, cuenta, existencias):
        """Guarda venta, detalles, cuenta y existencias: todo o nada (RNF-04)."""

    @abstractmethod
    def cuentas_del_cliente(self, id_cliente):
        ...

    @abstractmethod
    def obtener_cuenta(self, id_cuenta):
        ...

    @abstractmethod
    def guardar_abono(self, cuenta, valor):
        ...


class RepositorioDeVentasSqlite(RepositorioDeVentas):
    def __init__(self, conexion):
        self.conexion = conexion

    def guardar_transaccion(self, venta, cuenta, existencias):
        with self.conexion:
            self._insertar_venta(venta)
            self._insertar_detalles(venta)
            self._insertar_cuenta(venta, cuenta)
            self._actualizar_existencias(existencias)

    def _insertar_venta(self, venta):
        cursor = self.conexion.execute(
            "INSERT INTO ventas (id_cliente, fecha, estado, total) VALUES (?,?,?,?)",
            (venta.id_cliente, venta.fecha.isoformat(), venta.estado.value, venta.total))
        venta.id_venta = cursor.lastrowid

    def _insertar_detalles(self, venta):
        for detalle in venta.detalles:
            self.conexion.execute(
                "INSERT INTO detalles_venta (id_venta, numero_linea, id_producto, cantidad, "
                "precio_unitario_venta, subtotal_linea) VALUES (?,?,?,?,?,?)",
                (venta.id_venta, detalle.numero_linea, detalle.id_producto, detalle.cantidad,
                 detalle.precio_unitario, detalle.subtotal()))

    def _insertar_cuenta(self, venta, cuenta):
        cuenta.id_venta = venta.id_venta
        cursor = self.conexion.execute(
            "INSERT INTO cuentas_por_cobrar (id_venta, id_cliente, fecha_apertura, fecha_vencimiento, "
            "monto_credito_original, estado) VALUES (?,?,?,?,?,?)",
            (cuenta.id_venta, cuenta.id_cliente, cuenta.fecha_apertura.isoformat(),
             cuenta.fecha_vencimiento.isoformat(), cuenta.monto_original, cuenta.estado.value))
        cuenta.id_cuenta = cursor.lastrowid

    def _actualizar_existencias(self, existencias):
        for existencia in existencias:
            self.conexion.execute("UPDATE existencias SET cantidad_actual=? WHERE id_producto=?",
                                  (existencia.cantidad_actual, existencia.id_producto))

    def cuentas_del_cliente(self, id_cliente):
        filas = self.conexion.execute(
            "SELECT * FROM cuentas_por_cobrar WHERE id_cliente=? ORDER BY id_cuenta", (id_cliente,)).fetchall()
        return [self._a_cuenta(fila) for fila in filas]

    def obtener_cuenta(self, id_cuenta):
        fila = self.conexion.execute("SELECT * FROM cuentas_por_cobrar WHERE id_cuenta=?", (id_cuenta,)).fetchone()
        return self._a_cuenta(fila) if fila else None

    def _a_cuenta(self, fila):
        cuenta = CuentaPorCobrar(fila["id_cuenta"], fila["id_venta"], fila["id_cliente"],
                                 fila["monto_credito_original"], fila["fecha_apertura"], fila["fecha_vencimiento"])
        cuenta.estado = EstadoCuenta(fila["estado"])
        abonos = self.conexion.execute(
            "SELECT valor FROM abonos WHERE id_cuenta=? ORDER BY id_abono", (cuenta.id_cuenta,)).fetchall()
        cuenta.abonos = [abono["valor"] for abono in abonos]
        return cuenta

    def guardar_abono(self, cuenta, valor):
        with self.conexion:
            self.conexion.execute("INSERT INTO abonos (id_cuenta, valor, fecha) VALUES (?,?,?)",
                                  (cuenta.id_cuenta, valor, _ahora()))
            self.conexion.execute("UPDATE cuentas_por_cobrar SET estado=? WHERE id_cuenta=?",
                                  (cuenta.estado.value, cuenta.id_cuenta))

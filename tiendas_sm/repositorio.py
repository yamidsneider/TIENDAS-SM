import sqlite3
from datetime import datetime
from tiendas_sm.dominio import Producto, Existencia, Cliente, CuentaPorCobrar


class RepositorioSqlite:
    def __init__(self, ruta=":memory:"):
        self.conexion = sqlite3.connect(ruta)
        self.conexion.execute("PRAGMA foreign_keys = ON")
        self._crear_tablas()

    def _crear_tablas(self):
        self.conexion.executescript("""
        CREATE TABLE IF NOT EXISTS productos (
            id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL, precio_compra INTEGER NOT NULL,
            precio_venta INTEGER NOT NULL, stock_minimo INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS existencias (
            id_producto INTEGER PRIMARY KEY REFERENCES productos(id_producto),
            cantidad_actual INTEGER NOT NULL, cantidad_reservada INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS movimientos_inventario (
            id_movimiento INTEGER PRIMARY KEY AUTOINCREMENT,
            id_producto INTEGER NOT NULL REFERENCES productos(id_producto),
            tipo TEXT NOT NULL, cantidad INTEGER NOT NULL, fecha TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS clientes (
            id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
            nombres TEXT NOT NULL, credito_habilitado INTEGER NOT NULL,
            limite_credito INTEGER NOT NULL, plazo_credito_dias INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS ventas (
            id_venta INTEGER PRIMARY KEY AUTOINCREMENT,
            id_cliente INTEGER REFERENCES clientes(id_cliente),
            fecha TEXT NOT NULL, estado TEXT NOT NULL, total INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS detalles_venta (
            id_detalle INTEGER PRIMARY KEY AUTOINCREMENT,
            id_venta INTEGER NOT NULL REFERENCES ventas(id_venta),
            numero_linea INTEGER NOT NULL,
            id_producto INTEGER NOT NULL REFERENCES productos(id_producto),
            cantidad INTEGER NOT NULL, precio_unitario_venta INTEGER NOT NULL,
            subtotal_linea INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS cuentas_por_cobrar (
            id_cuenta INTEGER PRIMARY KEY AUTOINCREMENT,
            id_venta INTEGER NOT NULL REFERENCES ventas(id_venta),
            id_cliente INTEGER NOT NULL REFERENCES clientes(id_cliente),
            fecha_apertura TEXT NOT NULL, fecha_vencimiento TEXT NOT NULL,
            monto_credito_original INTEGER NOT NULL, estado TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS abonos (
            id_abono INTEGER PRIMARY KEY AUTOINCREMENT,
            id_cuenta INTEGER NOT NULL REFERENCES cuentas_por_cobrar(id_cuenta),
            valor INTEGER NOT NULL, fecha TEXT NOT NULL);
        """)

    # ---------- productos y existencias ----------
    def guardar_producto(self, p):
        with self.conexion:
            if p.id_producto is None:
                cur = self.conexion.execute(
                    "INSERT INTO productos (nombre, precio_compra, precio_venta, stock_minimo) VALUES (?,?,?,?)",
                    (p.nombre, p.precio_compra, p.precio_venta, p.stock_minimo))
                p.id_producto = cur.lastrowid
                self.conexion.execute("INSERT INTO existencias (id_producto, cantidad_actual) VALUES (?, 0)",
                                      (p.id_producto,))
            else:
                self.conexion.execute(
                    "UPDATE productos SET nombre=?, precio_compra=?, precio_venta=?, stock_minimo=? WHERE id_producto=?",
                    (p.nombre, p.precio_compra, p.precio_venta, p.stock_minimo, p.id_producto))
        return p.id_producto

    def obtener_producto(self, id_producto):
        f = self.conexion.execute(
            "SELECT id_producto, nombre, precio_compra, precio_venta, stock_minimo FROM productos WHERE id_producto=?",
            (id_producto,)).fetchone()
        if f is None:
            return None
        return Producto(f[0], f[1], f[2], f[3], f[4])

    def listar_productos(self):
        filas = self.conexion.execute(
            "SELECT id_producto, nombre, precio_compra, precio_venta, stock_minimo FROM productos ORDER BY nombre").fetchall()
        return [Producto(f[0], f[1], f[2], f[3], f[4]) for f in filas]

    def obtener_existencia(self, id_producto):
        f = self.conexion.execute(
            "SELECT id_producto, cantidad_actual, cantidad_reservada FROM existencias WHERE id_producto=?",
            (id_producto,)).fetchone()
        if f is None:
            return None
        return Existencia(f[0], f[1], f[2])

    def guardar_existencia(self, ex, tipo_movimiento, cantidad):
        with self.conexion:
            self.conexion.execute("UPDATE existencias SET cantidad_actual=? WHERE id_producto=?",
                                  (ex.cantidad_actual, ex.id_producto))
            self.conexion.execute(
                "INSERT INTO movimientos_inventario (id_producto, tipo, cantidad, fecha) VALUES (?,?,?,?)",
                (ex.id_producto, tipo_movimiento, cantidad, datetime.now().isoformat()))

    # ---------- clientes y cuentas ----------
    def guardar_cliente(self, c):
        with self.conexion:
            cur = self.conexion.execute(
                "INSERT INTO clientes (nombres, credito_habilitado, limite_credito, plazo_credito_dias) VALUES (?,?,?,?)",
                (c.nombres, 1 if c.credito_habilitado else 0, c.limite_credito, c.plazo_credito_dias))
            c.id_cliente = cur.lastrowid
        return c.id_cliente

    def obtener_cliente(self, id_cliente):
        f = self.conexion.execute(
            "SELECT id_cliente, nombres, credito_habilitado, limite_credito, plazo_credito_dias FROM clientes WHERE id_cliente=?",
            (id_cliente,)).fetchone()
        if f is None:
            return None
        return Cliente(f[0], f[1], bool(f[2]), f[3], f[4])

    def _cargar_cuenta(self, f):
        cuenta = CuentaPorCobrar(f[0], f[1], f[2], f[5], f[3], f[4])
        cuenta.estado = f[6]
        abonos = self.conexion.execute("SELECT valor FROM abonos WHERE id_cuenta=? ORDER BY id_abono", (f[0],)).fetchall()
        for a in abonos:
            cuenta.abonos.append(a[0])
        return cuenta

    def cuentas_del_cliente(self, id_cliente):
        filas = self.conexion.execute(
            "SELECT id_cuenta, id_venta, id_cliente, fecha_apertura, fecha_vencimiento, monto_credito_original, estado "
            "FROM cuentas_por_cobrar WHERE id_cliente=? ORDER BY id_cuenta", (id_cliente,)).fetchall()
        return [self._cargar_cuenta(f) for f in filas]

    def obtener_cuenta(self, id_cuenta):
        f = self.conexion.execute(
            "SELECT id_cuenta, id_venta, id_cliente, fecha_apertura, fecha_vencimiento, monto_credito_original, estado "
            "FROM cuentas_por_cobrar WHERE id_cuenta=?", (id_cuenta,)).fetchone()
        if f is None:
            return None
        return self._cargar_cuenta(f)

    def guardar_abono(self, cuenta, valor):
        with self.conexion:
            self.conexion.execute("INSERT INTO abonos (id_cuenta, valor, fecha) VALUES (?,?,?)",
                                  (cuenta.id_cuenta, valor, datetime.now().isoformat()))
            self.conexion.execute("UPDATE cuentas_por_cobrar SET estado=? WHERE id_cuenta=?",
                                  (cuenta.estado, cuenta.id_cuenta))

    # ---------- venta a crédito (todo o nada) ----------
    def guardar_transaccion(self, venta, cuenta, existencias):
        with self.conexion:
            cur = self.conexion.execute("INSERT INTO ventas (id_cliente, fecha, estado, total) VALUES (?,?,?,?)",
                                        (venta.id_cliente, venta.fecha.isoformat(), venta.estado, venta.total))
            venta.id_venta = cur.lastrowid
            for d in venta.detalles:
                self.conexion.execute(
                    "INSERT INTO detalles_venta (id_venta, numero_linea, id_producto, cantidad, precio_unitario_venta, subtotal_linea) "
                    "VALUES (?,?,?,?,?,?)",
                    (venta.id_venta, d.numero_linea, d.id_producto, d.cantidad, d.precio_unitario, d.subtotal()))
            cuenta.id_venta = venta.id_venta
            cur = self.conexion.execute(
                "INSERT INTO cuentas_por_cobrar (id_venta, id_cliente, fecha_apertura, fecha_vencimiento, monto_credito_original, estado) "
                "VALUES (?,?,?,?,?,?)",
                (cuenta.id_venta, cuenta.id_cliente, cuenta.fecha_apertura.isoformat(),
                 cuenta.fecha_vencimiento.isoformat(), cuenta.monto_original, cuenta.estado))
            cuenta.id_cuenta = cur.lastrowid
            for ex in existencias:
                self.conexion.execute("UPDATE existencias SET cantidad_actual=? WHERE id_producto=?",
                                      (ex.cantidad_actual, ex.id_producto))

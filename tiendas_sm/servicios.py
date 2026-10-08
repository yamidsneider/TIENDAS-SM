from collections import namedtuple
from datetime import datetime, timedelta

from tiendas_sm.dominio import (Producto, Cliente, Venta, CuentaPorCobrar, StockInsuficiente,
                                CreditoNoPermitido, PLAZO_POR_DEFECTO_DIAS)

LineaDeVenta = namedtuple("LineaDeVenta", "id_producto cantidad")


class ServicioDeProductos:
    def __init__(self, repo_productos):
        self.repo_productos = repo_productos

    def registrar_producto(self, nombre, precio_compra, precio_venta, cantidad_inicial=0):
        producto = Producto(None, nombre, precio_compra, precio_venta)
        self.repo_productos.guardar(producto)
        if cantidad_inicial > 0:
            self.registrar_entrada(producto.id_producto, cantidad_inicial)
        return producto

    def obtener(self, id_producto):
        return self.repo_productos.obtener(id_producto)

    def listar(self):
        return self.repo_productos.listar()

    def actualizar_precio(self, id_producto, nuevo_precio):
        producto = self.repo_productos.obtener(id_producto)
        producto.actualizar_precio(nuevo_precio)
        self.repo_productos.guardar(producto)
        return producto

    def registrar_entrada(self, id_producto, cantidad):
        existencia = self.repo_productos.obtener_existencia(id_producto)
        existencia.aumentar(cantidad)
        self.repo_productos.guardar_existencia(existencia, "ENTRADA", cantidad)
        return existencia


class ServicioDeClientes:
    def __init__(self, repo_clientes):
        self.repo_clientes = repo_clientes

    def registrar_cliente(self, nombres, credito_habilitado, limite_credito,
                          plazo_credito_dias=PLAZO_POR_DEFECTO_DIAS):
        cliente = Cliente(None, nombres, credito_habilitado, limite_credito, plazo_credito_dias)
        self.repo_clientes.guardar(cliente)
        return cliente


class ControlInventario:
    def __init__(self, repo_productos):
        self.repo_productos = repo_productos

    def hay_disponible(self, producto, cantidad):
        existencia = self.repo_productos.obtener_existencia(producto.id_producto)
        return existencia.cantidad_disponible() >= cantidad

    def descontar(self, producto, cantidad):
        existencia = self.repo_productos.obtener_existencia(producto.id_producto)
        existencia.descontar(cantidad)
        return existencia


class ControlCredito:
    def __init__(self, repo_ventas):
        self.repo_ventas = repo_ventas

    def saldo_pendiente(self, cliente):
        cuentas = self.repo_ventas.cuentas_del_cliente(cliente.id_cliente)
        return sum(cuenta.calcular_saldo() for cuenta in cuentas)

    def puede_comprar_a_credito(self, cliente, monto):
        return cliente.puede_endeudarse(monto, self.saldo_pendiente(cliente))

    def crear_cuenta(self, venta):
        apertura = datetime.now()
        vencimiento = apertura + timedelta(days=PLAZO_POR_DEFECTO_DIAS)
        return CuentaPorCobrar(None, venta.id_venta, venta.id_cliente, venta.total, apertura, vencimiento)

    def registrar_abono(self, id_cuenta, monto):
        cuenta = self.repo_ventas.obtener_cuenta(id_cuenta)
        cuenta.aplicar_pago(monto)
        self.repo_ventas.guardar_abono(cuenta, monto)
        return cuenta

    def cuentas_del_cliente(self, id_cliente):
        return self.repo_ventas.cuentas_del_cliente(id_cliente)


class ServicioDeVentas:
    def __init__(self, repo_productos, repo_clientes, repo_ventas, control_inventario, control_credito):
        self.repo_productos = repo_productos
        self.repo_clientes = repo_clientes
        self.repo_ventas = repo_ventas
        self.control_inventario = control_inventario
        self.control_credito = control_credito

    def registrar_venta_a_credito(self, id_cliente, lineas):
        cliente = self._obtener_cliente(id_cliente)
        venta, pedido = self._armar_venta(cliente, lineas)
        self._validar_credito(cliente, venta.calcular_total())
        existencias = self._descontar_existencias(pedido)
        venta.confirmar()
        cuenta = self.control_credito.crear_cuenta(venta)
        self.repo_ventas.guardar_transaccion(venta, cuenta, existencias)
        return venta

    def _obtener_cliente(self, id_cliente):
        cliente = self.repo_clientes.obtener(id_cliente)
        if cliente is None:
            raise ValueError("El cliente no existe")
        return cliente

    def _obtener_producto(self, id_producto):
        producto = self.repo_productos.obtener(id_producto)
        if producto is None:
            raise ValueError("El producto no existe")
        return producto

    def _armar_venta(self, cliente, lineas):
        """Crea la venta y valida el stock. 'pedido' guarda, por producto, el total pedido."""
        venta = Venta(cliente.id_cliente)
        pedido = {}
        for linea in map(LineaDeVenta._make, lineas):
            producto = self._obtener_producto(linea.id_producto)
            cantidad_total = pedido.get(producto.id_producto, (producto, 0))[1] + linea.cantidad
            pedido[producto.id_producto] = (producto, cantidad_total)
            if not self.control_inventario.hay_disponible(producto, cantidad_total):
                raise StockInsuficiente(f"No hay suficiente stock de {producto.nombre}")
            venta.agregar_detalle(producto, linea.cantidad)
        return venta, pedido

    def _validar_credito(self, cliente, total):
        if not self.control_credito.puede_comprar_a_credito(cliente, total):
            raise CreditoNoPermitido(f"El cliente no puede comprar a crédito por {total}")

    def _descontar_existencias(self, pedido):
        return [self.control_inventario.descontar(producto, cantidad)
                for producto, cantidad in pedido.values()]

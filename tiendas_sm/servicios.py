from datetime import datetime, timedelta
from tiendas_sm.dominio import (Producto, Cliente, Venta, CuentaPorCobrar,
                                StockInsuficiente, CreditoNoPermitido)


class ServicioDeProductos:
    def __init__(self, repo):
        self.repo = repo

    def registrar_producto(self, nombre, precio_compra, precio_venta, cantidad_inicial=0):
        p = Producto(None, nombre, precio_compra, precio_venta)
        self.repo.guardar_producto(p)
        if cantidad_inicial > 0:
            self.registrar_entrada(p.id_producto, cantidad_inicial)
        return p

    def obtener(self, id_producto):
        return self.repo.obtener_producto(id_producto)

    def listar(self):
        return self.repo.listar_productos()

    def actualizar_precio(self, id_producto, nuevo):
        p = self.repo.obtener_producto(id_producto)
        p.actualizar_precio(nuevo)
        self.repo.guardar_producto(p)
        return p

    def registrar_entrada(self, id_producto, cantidad):
        ex = self.repo.obtener_existencia(id_producto)
        ex.aumentar(cantidad)
        self.repo.guardar_existencia(ex, "ENTRADA", cantidad)
        return ex


class ServicioDeClientes:
    def __init__(self, repo):
        self.repo = repo

    def registrar_cliente(self, nombres, credito_habilitado, limite_credito, plazo_credito_dias=30):
        c = Cliente(None, nombres, credito_habilitado, limite_credito, plazo_credito_dias)
        self.repo.guardar_cliente(c)
        return c


class ControlInventario:
    def __init__(self, repo):
        self.repo = repo

    def hay_disponible(self, producto, cantidad):
        existencia = self.repo.obtener_existencia(producto.id_producto)
        return existencia.cantidad_actual - existencia.cantidad_reservada >= cantidad

    def descontar(self, producto, cantidad):
        existencia = self.repo.obtener_existencia(producto.id_producto)
        existencia.descontar(cantidad)
        return existencia


class ControlCredito:
    def __init__(self, repo):
        self.repo = repo

    def saldo_pendiente(self, cliente):
        cuentas = self.repo.cuentas_del_cliente(cliente.id_cliente)
        return sum(cuenta.calcular_saldo() for cuenta in cuentas)

    def puede_comprar_a_credito(self, cliente, monto):
        return cliente.puede_endeudarse(monto, self.saldo_pendiente(cliente))

    def crear_cuenta(self, venta):
        apertura = datetime.now()
        vencimiento = apertura + timedelta(days=30)
        return CuentaPorCobrar(None, venta.id_venta, venta.id_cliente, venta.total, apertura, vencimiento)

    def registrar_abono(self, id_cuenta, monto):
        cuenta = self.repo.obtener_cuenta(id_cuenta)
        cuenta.aplicar_pago(monto)
        self.repo.guardar_abono(cuenta, monto)
        return cuenta

    def cuentas_del_cliente(self, id_cliente):
        return self.repo.cuentas_del_cliente(id_cliente)


class ServicioDeVentas:
    def __init__(self, repo):
        self.repo = repo
        self.control_inventario = ControlInventario(repo)
        self.control_credito = ControlCredito(repo)

    def registrar_venta_a_credito(self, id_cliente, lineas):
        cliente = self._obtener_cliente(id_cliente)
        venta, pedido = self._armar_venta(cliente, lineas)
        self._validar_credito(cliente, venta.calcular_total())
        existencias = self._descontar_existencias(pedido)
        venta.confirmar()
        cuenta = self.control_credito.crear_cuenta(venta)
        self.repo.guardar_transaccion(venta, cuenta, existencias)
        return venta

    def _obtener_cliente(self, id_cliente):
        cliente = self.repo.obtener_cliente(id_cliente)
        if cliente is None:
            raise ValueError("El cliente no existe")
        return cliente

    def _armar_venta(self, cliente, lineas):
        """Crea la venta y valida el stock. 'pedido' guarda, por producto, el total pedido."""
        venta = Venta(cliente.id_cliente)
        pedido = {}
        for linea in lineas:
            id_producto, cantidad = linea[0], linea[1]
            producto = self.repo.obtener_producto(id_producto)
            if producto is None:
                raise ValueError("El producto no existe")
            if cantidad <= 0:
                raise ValueError("La cantidad debe ser mayor a cero")
            cantidad_total = pedido.get(id_producto, (producto, 0))[1] + cantidad
            pedido[id_producto] = (producto, cantidad_total)
            if not self.control_inventario.hay_disponible(producto, cantidad_total):
                raise StockInsuficiente("No hay suficiente stock de " + producto.nombre)
            venta.agregar_detalle(producto, cantidad)
        return venta, pedido

    def _validar_credito(self, cliente, total):
        if not self.control_credito.puede_comprar_a_credito(cliente, total):
            raise CreditoNoPermitido("El cliente no puede comprar a crédito por " + str(total))

    def _descontar_existencias(self, pedido):
        return [self.control_inventario.descontar(producto, cantidad)
                for producto, cantidad in pedido.values()]

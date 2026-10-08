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
        ex = self.repo.obtener_existencia(producto.id_producto)
        return ex.cantidad_actual - ex.cantidad_reservada >= cantidad

    def descontar(self, producto, cantidad):
        ex = self.repo.obtener_existencia(producto.id_producto)
        ex.descontar(cantidad)
        return ex


class ControlCredito:
    def __init__(self, repo):
        self.repo = repo

    def saldo_pendiente(self, cliente):
        cuentas = self.repo.cuentas_del_cliente(cliente.id_cliente)
        saldo = 0
        for c in cuentas:
            saldo = saldo + c.calcular_saldo()
        return saldo

    def puede_comprar_a_credito(self, cliente, monto):
        if cliente.credito_habilitado == False:
            return False
        disponible = cliente.limite_credito - self.saldo_pendiente(cliente)
        if monto > disponible:
            return False
        return True

    def crear_cuenta(self, venta):
        cli = self.repo.obtener_cliente(venta.id_cliente)
        hoy = datetime.now()
        return CuentaPorCobrar(None, venta.id_venta, venta.id_cliente, venta.total, hoy, hoy + timedelta(days=30))

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
        self.inv = ControlInventario(repo)
        self.cred = ControlCredito(repo)

    def registrar_venta_a_credito(self, id_cliente, lineas):
        cli = self.repo.obtener_cliente(id_cliente)
        if cli is None:
            raise ValueError("El cliente no existe")
        venta = Venta(id_cliente)
        acumulado = {}
        productos = {}
        # recorre las lineas de la venta
        for lin in lineas:
            p = self.repo.obtener_producto(lin[0])
            if p is None:
                raise ValueError("El producto no existe")
            if lin[1] <= 0:
                raise ValueError("La cantidad debe ser mayor a cero")
            productos[p.id_producto] = p
            if p.id_producto in acumulado:
                acumulado[p.id_producto] = acumulado[p.id_producto] + lin[1]
            else:
                acumulado[p.id_producto] = lin[1]
            if not self.inv.hay_disponible(p, acumulado[p.id_producto]):
                raise StockInsuficiente("No hay suficiente stock de " + p.nombre)
            venta.agregar_detalle(p, lin[1])
        total = venta.calcular_total()
        if not self.cred.puede_comprar_a_credito(cli, total):
            raise CreditoNoPermitido("El cliente no puede comprar a crédito por " + str(total))
        existencias = []
        for id_p in acumulado:
            existencias.append(self.inv.descontar(productos[id_p], acumulado[id_p]))
        venta.confirmar()
        cuenta = self.cred.crear_cuenta(venta)
        self.repo.guardar_transaccion(venta, cuenta, existencias)
        return venta

from datetime import datetime


class StockInsuficiente(Exception):
    pass


class CreditoNoPermitido(Exception):
    pass


class Producto:
    def __init__(self, id_producto, nombre, precio_compra, precio_venta, stock_minimo=0):
        if nombre is None or nombre.strip() == "":
            raise ValueError("El nombre es obligatorio")
        if precio_compra < 0 or precio_venta < 0:
            raise ValueError("Los precios no pueden ser negativos")
        self.id_producto = id_producto
        self.nombre = nombre
        self.precio_compra = precio_compra
        self.precio_venta = precio_venta
        self.stock_minimo = stock_minimo

    def actualizar_precio(self, nuevo):
        if nuevo < 0:
            raise ValueError("El precio no puede ser negativo")
        self.precio_venta = nuevo


class Existencia:
    def __init__(self, id_producto, cantidad_actual=0, cantidad_reservada=0):
        self.id_producto = id_producto
        self.cantidad_actual = cantidad_actual
        self.cantidad_reservada = cantidad_reservada

    def descontar(self, cantidad):
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a cero")
        if cantidad > self.cantidad_actual:
            raise StockInsuficiente("Solo hay " + str(self.cantidad_actual) + " disponibles")
        self.cantidad_actual = self.cantidad_actual - cantidad

    def aumentar(self, cantidad):
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a cero")
        self.cantidad_actual = self.cantidad_actual + cantidad


class Cliente:
    def __init__(self, id_cliente, nombres, credito_habilitado, limite_credito, plazo_credito_dias):
        self.id_cliente = id_cliente
        self.nombres = nombres
        self.credito_habilitado = credito_habilitado
        self.limite_credito = limite_credito
        self.plazo_credito_dias = plazo_credito_dias

    def credito_disponible(self, saldo_pendiente):
        return self.limite_credito - saldo_pendiente

    def puede_endeudarse(self, monto, saldo_pendiente):
        return self.credito_habilitado and monto <= self.credito_disponible(saldo_pendiente)


class DetalleVenta:
    def __init__(self, numero_linea, id_producto, cantidad, precio_unitario):
        self.numero_linea = numero_linea
        self.id_producto = id_producto
        self.cantidad = cantidad
        self.precio_unitario = precio_unitario

    def subtotal(self):
        return self.cantidad * self.precio_unitario


class Venta:
    def __init__(self, id_cliente=None):
        self.id_venta = None
        self.id_cliente = id_cliente
        self.fecha = datetime.now()
        self.estado = "ABIERTA"
        self.detalles = []
        self.total = 0

    def agregar_detalle(self, producto, cantidad):
        if cantidad <= 0:
            raise ValueError("La cantidad debe ser mayor a cero")
        numero = len(self.detalles) + 1
        self.detalles.append(DetalleVenta(numero, producto.id_producto, cantidad, producto.precio_venta))

    def calcular_total(self):
        self.total = sum(detalle.subtotal() for detalle in self.detalles)
        return self.total

    def confirmar(self):
        if len(self.detalles) == 0:
            raise ValueError("La venta no tiene productos")
        self.estado = "CONFIRMADA"

    def anular(self):
        self.estado = "ANULADA"


class CuentaPorCobrar:
    def __init__(self, id_cuenta, id_venta, id_cliente, monto_original, fecha_apertura, fecha_vencimiento):
        self.id_cuenta = id_cuenta
        self.id_venta = id_venta
        self.id_cliente = id_cliente
        self.monto_original = monto_original
        self.fecha_apertura = fecha_apertura
        self.fecha_vencimiento = fecha_vencimiento
        self.abonos = []
        self.estado = "ABIERTA"

    def calcular_saldo(self):
        return self.monto_original - sum(self.abonos)

    def aplicar_pago(self, monto):
        if monto <= 0:
            raise ValueError("La cantidad debe ser mayor a cero")
        if monto > self.calcular_saldo():
            raise ValueError("El abono no puede ser mayor al saldo")
        self.abonos.append(monto)
        if self.calcular_saldo() == 0:
            self.estado = "PAGADA"

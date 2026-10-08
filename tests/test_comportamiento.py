"""Pruebas de comportamiento de TIENDAS S.M (Incremento 1 y flujo CU-01).

Cada prueba corresponde a un escenario Gherkin de la FPI-06. Se usan SOLO los
métodos públicos y los nombres de tablas, así que las mismas pruebas sirven
antes y después de refactorizar (el comportamiento externo no debe cambiar).
"""
import sqlite3
import unittest
from datetime import datetime

from tiendas_sm.aplicacion import Aplicacion
from tiendas_sm.dominio import StockInsuficiente, CreditoNoPermitido


class PruebasDeProductos(unittest.TestCase):
    def setUp(self):
        self.app = Aplicacion()

    def test_hu01_registra_producto_valido(self):
        p = self.app.productos.registrar_producto("Arroz 500 g", 2000, 2500, 20)
        guardado = self.app.productos.obtener(p.id_producto)
        self.assertEqual(guardado.nombre, "Arroz 500 g")
        self.assertEqual(guardado.precio_venta, 2500)
        self.assertEqual(self.app.cantidad_en_inventario(p.id_producto), 20)

    def test_hu01_rechaza_nombre_vacio(self):
        with self.assertRaises(ValueError):
            self.app.productos.registrar_producto("  ", 2000, 2500)
        self.assertEqual(self.app.productos.listar(), [])

    def test_hu01_rechaza_precio_negativo(self):
        with self.assertRaises(ValueError):
            self.app.productos.registrar_producto("Arroz", 2000, -1)
        self.assertEqual(self.app.productos.listar(), [])

    def test_hu02_actualizar_precio_no_cambia_ventas_anteriores(self):
        p = self.app.productos.registrar_producto("Arroz", 2000, 2500, 10)
        cliente = self.app.clientes.registrar_cliente("Cliente de prueba", True, 100000)
        self.app.ventas.registrar_venta_a_credito(cliente.id_cliente, [(p.id_producto, 2)])
        self.app.productos.actualizar_precio(p.id_producto, 2700)
        self.assertEqual(self.app.productos.obtener(p.id_producto).precio_venta, 2700)
        precio_vendido = self.app.conexion.execute(
            "SELECT precio_unitario_venta FROM detalles_venta").fetchone()[0]
        self.assertEqual(precio_vendido, 2500)

    def test_hu02_rechaza_precio_invalido_y_conserva_el_anterior(self):
        p = self.app.productos.registrar_producto("Arroz", 2000, 2500)
        with self.assertRaises(ValueError):
            self.app.productos.actualizar_precio(p.id_producto, -5)
        self.assertEqual(self.app.productos.obtener(p.id_producto).precio_venta, 2500)

    def test_hu03_entrada_aumenta_la_cantidad(self):
        p = self.app.productos.registrar_producto("Arroz", 2000, 2500, 5)
        self.app.productos.registrar_entrada(p.id_producto, 10)
        self.assertEqual(self.app.cantidad_en_inventario(p.id_producto), 15)
        movimientos = self.app.conexion.execute(
            "SELECT COUNT(*) FROM movimientos_inventario WHERE tipo='ENTRADA'").fetchone()[0]
        self.assertEqual(movimientos, 2)  # la inicial (5) y la de 10

    def test_hu03_rechaza_entrada_de_cero_o_negativa(self):
        p = self.app.productos.registrar_producto("Arroz", 2000, 2500, 5)
        for cantidad in (0, -3):
            with self.assertRaises(ValueError):
                self.app.productos.registrar_entrada(p.id_producto, cantidad)
        self.assertEqual(self.app.cantidad_en_inventario(p.id_producto), 5)


class PruebasDeVentaACredito(unittest.TestCase):
    def setUp(self):
        self.app = Aplicacion()
        self.a = self.app.productos.registrar_producto("Producto A", 1500, 2500, 10)
        self.b = self.app.productos.registrar_producto("Producto B", 2000, 3000, 4)
        self.cliente = self.app.clientes.registrar_cliente("Cliente de prueba", True, 50000)

    def vender(self, lineas, cliente=None):
        cliente = cliente or self.cliente
        return self.app.ventas.registrar_venta_a_credito(cliente.id_cliente, lineas)

    def test_hu04_total_e_inventario_de_venta_con_dos_productos(self):
        venta = self.vender([(self.a.id_producto, 2), (self.b.id_producto, 1)])
        self.assertEqual(venta.total, 8000)
        self.assertEqual(self.app.cantidad_en_inventario(self.a.id_producto), 8)
        self.assertEqual(self.app.cantidad_en_inventario(self.b.id_producto), 3)

    def test_hu04_rechaza_stock_insuficiente_sin_cambiar_nada(self):
        with self.assertRaises(StockInsuficiente):
            self.vender([(self.b.id_producto, 5)])
        self.assertEqual(self.app.cantidad_en_inventario(self.b.id_producto), 4)
        self.assertEqual(self.app.numero_de_ventas(), 0)

    def test_hu04_cuenta_el_mismo_producto_repetido_en_varias_lineas(self):
        with self.assertRaises(StockInsuficiente):
            self.vender([(self.b.id_producto, 3), (self.b.id_producto, 2)])
        self.assertEqual(self.app.cantidad_en_inventario(self.b.id_producto), 4)

    def test_hu04_rechaza_venta_sin_productos(self):
        with self.assertRaises(ValueError):
            self.vender([])
        self.assertEqual(self.app.numero_de_ventas(), 0)

    def test_hu04_rechaza_cantidad_cero_y_producto_inexistente(self):
        with self.assertRaises(ValueError):
            self.vender([(self.a.id_producto, 0)])
        with self.assertRaises(ValueError):
            self.vender([(9999, 1)])
        self.assertEqual(self.app.numero_de_ventas(), 0)

    def test_cu01_crea_la_cuenta_por_cobrar_con_el_total_como_deuda(self):
        venta = self.vender([(self.a.id_producto, 2)])
        cuentas = self.app.credito.cuentas_del_cliente(self.cliente.id_cliente)
        self.assertEqual(len(cuentas), 1)
        self.assertEqual(cuentas[0].id_venta, venta.id_venta)
        self.assertEqual(cuentas[0].monto_original, 5000)
        self.assertEqual(cuentas[0].calcular_saldo(), 5000)

    def test_cu01_rechaza_cliente_sin_credito_habilitado(self):
        sin_credito = self.app.clientes.registrar_cliente("Sin crédito", False, 0)
        with self.assertRaises(CreditoNoPermitido):
            self.vender([(self.a.id_producto, 1)], sin_credito)
        self.assertEqual(self.app.cantidad_en_inventario(self.a.id_producto), 10)
        self.assertEqual(self.app.numero_de_ventas(), 0)

    def test_cu01_rechaza_venta_que_supera_el_limite(self):
        caro = self.app.productos.registrar_producto("Producto caro", 20000, 30000, 5)
        with self.assertRaises(CreditoNoPermitido):
            self.vender([(caro.id_producto, 2)])           # 60.000 > 50.000
        self.assertEqual(self.app.cantidad_en_inventario(caro.id_producto), 5)
        self.assertEqual(self.app.numero_de_ventas(), 0)

    def test_cu01_el_saldo_pendiente_consume_el_limite_de_credito(self):
        self.vender([(self.b.id_producto, 4)])            # 12.000 de deuda
        self.app.productos.registrar_entrada(self.a.id_producto, 30)
        with self.assertRaises(CreditoNoPermitido):
            self.vender([(self.a.id_producto, 16)])        # 40.000 -> 52.000 > 50.000
        self.vender([(self.a.id_producto, 15)])            # 37.500 -> 49.500 <= 50.000

    def test_cu01_cliente_inexistente(self):
        with self.assertRaises(ValueError):
            self.app.ventas.registrar_venta_a_credito(9999, [(self.a.id_producto, 1)])

    def test_rnf04_si_falla_al_guardar_no_queda_nada_a_medias(self):
        self.app.conexion.execute(
            "CREATE TRIGGER falla_simulada BEFORE INSERT ON cuentas_por_cobrar "
            "BEGIN SELECT RAISE(ABORT, 'falla simulada'); END")
        with self.assertRaises(sqlite3.Error):
            self.vender([(self.a.id_producto, 2)])
        self.assertEqual(self.app.numero_de_ventas(), 0)
        self.assertEqual(self.app.cantidad_en_inventario(self.a.id_producto), 10)
        detalles = self.app.conexion.execute("SELECT COUNT(*) FROM detalles_venta").fetchone()[0]
        self.assertEqual(detalles, 0)


class PruebasDeAbonos(unittest.TestCase):
    def setUp(self):
        self.app = Aplicacion()
        producto = self.app.productos.registrar_producto("Producto", 1000, 5000, 50)
        self.cliente = self.app.clientes.registrar_cliente("Cliente de prueba", True, 100000)
        self.app.ventas.registrar_venta_a_credito(self.cliente.id_cliente, [(producto.id_producto, 10)])
        self.cuenta = self.app.credito.cuentas_del_cliente(self.cliente.id_cliente)[0]  # deuda de 50.000

    def test_hu06_abono_reduce_el_saldo(self):
        cuenta = self.app.credito.registrar_abono(self.cuenta.id_cuenta, 20000)
        self.assertEqual(cuenta.calcular_saldo(), 30000)
        guardada = self.app.credito.cuentas_del_cliente(self.cliente.id_cliente)[0]
        self.assertEqual(guardada.calcular_saldo(), 30000)

    def test_hu06_rechaza_abono_mayor_al_saldo(self):
        self.app.credito.registrar_abono(self.cuenta.id_cuenta, 20000)
        with self.assertRaises(ValueError):
            self.app.credito.registrar_abono(self.cuenta.id_cuenta, 60000)
        guardada = self.app.credito.cuentas_del_cliente(self.cliente.id_cliente)[0]
        self.assertEqual(guardada.calcular_saldo(), 30000)

    def test_hu06_rechaza_abono_de_cero_o_negativo(self):
        for valor in (0, -100):
            with self.assertRaises(ValueError):
                self.app.credito.registrar_abono(self.cuenta.id_cuenta, valor)

    def test_hu06_al_pagar_todo_la_cuenta_queda_pagada(self):
        self.app.credito.registrar_abono(self.cuenta.id_cuenta, 50000)
        guardada = self.app.credito.cuentas_del_cliente(self.cliente.id_cliente)[0]
        self.assertEqual(guardada.calcular_saldo(), 0)
        self.assertEqual(guardada.estado, "PAGADA")


class PruebasDeDeudaTecnica(unittest.TestCase):
    @unittest.expectedFailure
    def test_deuda_el_vencimiento_deberia_usar_el_plazo_del_cliente(self):
        """DT-02: hoy el vencimiento siempre es a 30 días (ignora plazo_credito_dias).
        Esta prueba fallará (a propósito) hasta que se pague la deuda en un commit aparte."""
        app = Aplicacion()
        producto = app.productos.registrar_producto("Producto", 1000, 2000, 5)
        cliente = app.clientes.registrar_cliente("Cliente de prueba", True, 100000, plazo_credito_dias=15)
        app.ventas.registrar_venta_a_credito(cliente.id_cliente, [(producto.id_producto, 1)])
        cuenta = app.credito.cuentas_del_cliente(cliente.id_cliente)[0]
        apertura = datetime.fromisoformat(str(cuenta.fecha_apertura))
        vencimiento = datetime.fromisoformat(str(cuenta.fecha_vencimiento))
        self.assertEqual((vencimiento - apertura).days, 15)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Mide señales simples de calidad con el módulo ast (solo biblioteca estándar).

Uso:  python medir_calidad.py ruta/al/paquete
Reporta por función: líneas, parámetros, anidamiento máximo y ramas (if/for/while).
Y señala: funciones largas (>15 líneas), con muchos parámetros (>3), anidamiento >2,
números mágicos y cadenas de estado repetidas.
"""
import ast
import sys
from collections import Counter
from pathlib import Path

MAX_LINEAS, MAX_PARAMS, MAX_ANIDAMIENTO = 15, 3, 2
RAMAS = (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.BoolOp)


def anidamiento(nodo, nivel=0):
    maximo = nivel
    for hijo in ast.iter_child_nodes(nodo):
        sube = isinstance(hijo, (ast.If, ast.For, ast.While, ast.Try, ast.With))
        maximo = max(maximo, anidamiento(hijo, nivel + sube))
    return maximo


def medir_archivo(ruta):
    arbol = ast.parse(ruta.read_text(encoding="utf8"))
    filas, numeros, cadenas = [], [], []
    for nodo in ast.walk(arbol):
        if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lineas = nodo.end_lineno - nodo.lineno + 1
            params = len([a for a in nodo.args.args if a.arg != "self"])
            ramas = sum(isinstance(n, RAMAS) for n in ast.walk(nodo))
            filas.append((nodo.name, lineas, params, anidamiento(nodo), ramas))
        if isinstance(nodo, ast.Constant):
            if isinstance(nodo.value, (int, float)) and not isinstance(nodo.value, bool) and nodo.value not in (0, 1, -1):
                numeros.append((nodo.value, nodo.lineno))
            if isinstance(nodo.value, str) and nodo.value.isupper() and len(nodo.value) > 3:
                cadenas.append(nodo.value)
    return filas, numeros, cadenas


def main(carpeta):
    total_funciones = largas = muchos = hondas = 0
    magicos, estados = [], Counter()
    clases = {}
    print(f"{'archivo':22}{'función':34}{'líneas':>7}{'params':>8}{'anid.':>7}{'ramas':>7}")
    for ruta in sorted(Path(carpeta).rglob("*.py")):
        filas, numeros, cadenas = medir_archivo(ruta)
        texto = ruta.read_text(encoding="utf8")
        for nodo in ast.parse(texto).body:
            if isinstance(nodo, ast.ClassDef):
                metodos = [n for n in nodo.body if isinstance(n, ast.FunctionDef)]
                clases[f"{ruta.name}:{nodo.name}"] = (len(metodos), nodo.end_lineno - nodo.lineno + 1)
        for nombre, lineas, params, anid, ramas in filas:
            total_funciones += 1
            marca = ""
            if lineas > MAX_LINEAS: largas += 1; marca += " L"
            if params > MAX_PARAMS: muchos += 1; marca += " P"
            if anid > MAX_ANIDAMIENTO: hondas += 1; marca += " A"
            if lineas > MAX_LINEAS or params > MAX_PARAMS or anid > MAX_ANIDAMIENTO:
                print(f"{ruta.name:22}{nombre:34}{lineas:>7}{params:>8}{anid:>7}{ramas:>7}{marca}")
        magicos += [(ruta.name, v, l) for v, l in numeros]
        estados.update(cadenas)
    print("\nResumen")
    print(f"  funciones/métodos analizados: {total_funciones}")
    print(f"  más de {MAX_LINEAS} líneas (L): {largas} | más de {MAX_PARAMS} parámetros (P): {muchos} | anidamiento > {MAX_ANIDAMIENTO} (A): {hondas}")
    print(f"  números mágicos (distintos de 0, 1, -1): {len(magicos)} -> {magicos}")
    repetidas = {k: v for k, v in estados.items() if v >= 2}
    print(f"  cadenas de estado repetidas: {repetidas}")
    grandes = {k: v for k, v in clases.items() if v[0] >= 10 or v[1] >= 100}
    print(f"  clases grandes (>=10 métodos o >=100 líneas): {grandes}")
    muertos = codigo_muerto(carpeta)
    print(f"  código muerto: {len(muertos)}")
    for m in muertos:
        print("    -", m)


def codigo_muerto(carpeta):
    """Importaciones sin usar y variables locales asignadas pero nunca leídas."""
    hallazgos = []
    for ruta in sorted(Path(carpeta).rglob("*.py")):
        arbol = ast.parse(ruta.read_text(encoding="utf8"))
        importados = {}
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom) or isinstance(nodo, ast.Import):
                for alias in nodo.names:
                    importados[(alias.asname or alias.name).split(".")[0]] = nodo.lineno
        usados = {n.id for n in ast.walk(arbol) if isinstance(n, ast.Name)} | \
                 {n.value.id for n in ast.walk(arbol) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)}
        for nombre, linea in importados.items():
            if nombre not in usados and ruta.name != "__init__.py":
                hallazgos.append(f"{ruta.name}:{linea} importación sin usar '{nombre}'")
        for func in [n for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef)]:
            asignadas = {t.id: t.lineno for n in ast.walk(func) if isinstance(n, ast.Assign)
                         for t in n.targets if isinstance(t, ast.Name)}
            leidas = {n.id for n in ast.walk(func) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
            for nombre, linea in asignadas.items():
                if nombre not in leidas:
                    hallazgos.append(f"{ruta.name}:{linea} variable '{nombre}' asignada y nunca usada (en {func.name})")
    return hallazgos


if __name__ == "__main__":
    main(sys.argv[1])

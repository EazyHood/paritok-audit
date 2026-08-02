"""Acorrala el HTTP 400: ¿es el tamaño, o es el contenido?

El header C++ de 16.360 tokens pasó sin problema, así que "demasiado grande"
no explica que un JSON de ~7.000 tokens falle. Bisecamos para separar las dos
hipótesis en vez de suponer.
"""
import sys, json, traceback
sys.path.insert(0, ".")
from paritok import CompressionPipeline, ParitokConfig

RAW = open("corpus/c4.json", "r", encoding="utf-8").read()
cfg = ParitokConfig.load()
pipe = CompressionPipeline(cfg)
Q = "List the audit competitions still open and their prize pools"


def intenta(texto, etiqueta):
    try:
        r = pipe.compress(texto, query=Q, kind="tool_output")
        print(f"  OK   {etiqueta:32s} {len(texto):>7,d} chars  ratio={r.ratio:.1%}")
        return True
    except Exception as exc:
        msg = str(exc).split("\n")[0][:90]
        print(f"  FAIL {etiqueta:32s} {len(texto):>7,d} chars  {type(exc).__name__}: {msg}")
        return False


print("=== 1. bisección por tamaño (mismo contenido JSON) ===")
for frac in (0.1, 0.25, 0.5, 0.75, 1.0):
    n = int(len(RAW) * frac)
    intenta(RAW[:n], f"c4.json[:{int(frac*100)}%]")

print("\n=== 2. ¿es el JSON, o cualquier texto de ese tamaño? ===")
n = len(RAW)
prosa = ("The quick brown fox jumps over the lazy dog near the riverbank. " * (n // 63))[:n]
intenta(prosa, "prosa del mismo tamaño")

print("\n=== 3. ¿JSON reformateado (con saltos de línea)? ===")
try:
    bonito = json.dumps(json.loads(RAW), indent=2)
    intenta(bonito, "mismo JSON, indentado")
except Exception as e:
    print("  no parseable:", e)

print("\n=== 4. ¿una sola línea larguísima sin saltos? ===")
una_linea = RAW.replace("\n", " ")
print(f"  lineas en el original: {RAW.count(chr(10)) + 1}")
print(f"  linea mas larga: {max(len(l) for l in RAW.split(chr(10))):,d} chars")
intenta(una_linea, "todo en una linea")

print("\n=== 5. traza completa del fallo ===")
try:
    pipe.compress(RAW, query=Q, kind="tool_output")
    print("  (no falló esta vez)")
except Exception:
    traceback.print_exc(limit=6)

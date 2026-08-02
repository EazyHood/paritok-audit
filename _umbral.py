"""Umbral exacto: ¿es CHUNK_SIZE (3000 tokens) en una sola línea?"""
import sys
sys.path.insert(0, ".")
from paritok.strategies.chunking import (
    CHUNK_SIZE, count_tokens, split_into_chunks_structural, _token_split_block,
)

RAW = open("corpus/c4.json", "r", encoding="utf-8").read()
print(f"CHUNK_SIZE = {CHUNK_SIZE} tokens")
print(f"c4.json: {len(RAW):,d} chars, {RAW.count(chr(10))+1} linea(s), {count_tokens(RAW):,d} tokens\n")

print("prueba directa del troceador sobre una sola linea:")
print(f"{'chars':>8} {'tokens':>8} {'chunks':>7} {'mayor chunk':>12}  veredicto")
for frac in (0.10, 0.25, 0.40, 0.50, 0.60, 0.75, 1.00):
    piece = RAW[: int(len(RAW) * frac)]
    toks = count_tokens(piece)
    chunks = split_into_chunks_structural(piece)
    mayor = max(count_tokens(c[0]) for c in chunks) if chunks else 0
    ok = mayor <= CHUNK_SIZE
    print(f"{len(piece):>8,d} {toks:>8,d} {len(chunks):>7d} {mayor:>12,d}  "
          f"{'ok' if ok else 'DESBORDA CHUNK_SIZE'}")

print("\ncontrol: el mismo contenido con saltos de linea")
multi = RAW.replace("},", "},\n")
chunks = split_into_chunks_structural(multi)
mayor = max(count_tokens(c[0]) for c in chunks) if chunks else 0
print(f"{len(multi):>8,d} {count_tokens(multi):>8,d} {len(chunks):>7d} {mayor:>12,d}  "
      f"{'ok' if mayor <= CHUNK_SIZE else 'DESBORDA'}")

print("\nprueba unitaria del agujero: una sola linea de 10x CHUNK_SIZE")
una = "word " * (CHUNK_SIZE * 10)
piezas = _token_split_block([una], CHUNK_SIZE)
print(f"  entrada: 1 linea de {count_tokens(una):,d} tokens")
print(f"  _token_split_block devolvio {len(piezas)} pieza(s)")
print(f"  mayor pieza: {count_tokens(chr(10).join(piezas[0])):,d} tokens  (limite {CHUNK_SIZE})")

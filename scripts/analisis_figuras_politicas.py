#!/usr/bin/env python3
"""
Análisis de menciones a Álvaro Uribe Vélez y Gustavo Petro
en el programa de gobierno de Iván Cepeda 2026-2030.
"""

import os, re, sys
import fitz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import numpy as np
from collections import Counter, defaultdict

PDF_PATH = r"C:\Users\David.Munoz\Downloads\programa-gobierno-2026-2030.pdf"
OUT_DIR  = r"C:\Users\David.Munoz\Documents\analisis_politico_ivan_cepeda"

# ── Extraer texto crudo por página ──────────────────────────────────────────
doc = fitz.open(PDF_PATH)
pages = [page.get_text("text") for page in doc]
print(f"Páginas cargadas: {len(pages)}")

# ── Patrones de búsqueda ────────────────────────────────────────────────────
PATRONES = {
    "Uribe Vélez": [
        r"uribe\s+v[eé]lez", r"\buribe\b", r"\buribismo\b", r"\buribista[s]?\b",
        r"\buribista\b", r"álvaro\s+uribe", r"alvaro\s+uribe",
        r"expresidente\s+uribe", r"ex[\-\s]?presidente\s+uribe",
        r"senador\s+uribe", r"ex[\-\s]?presidente\s+álvaro",
    ],
    "Gustavo Petro": [
        r"\bpetro\b", r"gustavo\s+petro", r"petroísmo", r"petroista[s]?",
        r"gobierno\s+petro", r"presidente\s+petro", r"petro\s+urrego",
    ],
}

# ── Buscar menciones por página ─────────────────────────────────────────────
def buscar_menciones(pages, patrones):
    """Retorna dict: figura -> lista de (page_num, fragmento, patron)"""
    resultados = {fig: [] for fig in patrones}
    for i, pg in enumerate(pages):
        pg_lower = pg.lower()
        for figura, pats in patrones.items():
            for pat in pats:
                for m in re.finditer(pat, pg_lower):
                    # Contexto: 150 chars antes y después
                    start = max(0, m.start()-150)
                    end   = min(len(pg), m.end()+150)
                    frag  = pg[start:end].replace("\n", " ").strip()
                    resultados[figura].append({
                        "pagina": i+1,
                        "patron": pat,
                        "match":  m.group(),
                        "contexto": frag,
                    })
    return resultados

menciones = buscar_menciones(pages, PATRONES)

# ── Estadísticas básicas ────────────────────────────────────────────────────
print("\n" + "="*60)
print("MENCIONES TOTALES")
print("="*60)
for fig, hits in menciones.items():
    paginas_unicas = set(h["pagina"] for h in hits)
    print(f"  {fig}: {len(hits)} menciones en {len(paginas_unicas)} páginas distintas")

# ── Frecuencia por página ───────────────────────────────────────────────────
uribe_por_pag = Counter(h["pagina"] for h in menciones["Uribe Vélez"])
petro_por_pag = Counter(h["pagina"] for h in menciones["Gustavo Petro"])

all_pages = list(range(1, len(pages)+1))
uribe_vals = [uribe_por_pag.get(p, 0) for p in all_pages]
petro_vals = [petro_por_pag.get(p, 0) for p in all_pages]

# ── Gráfico comparativo: menciones por página ───────────────────────────────
fig, axes = plt.subplots(2, 1, figsize=(16, 8), sharex=True)
fig.suptitle("Menciones a Uribe Vélez y Gustavo Petro\nPrograma de Gobierno Iván Cepeda 2026–2030",
             fontsize=13, fontweight="bold")

axes[0].bar(all_pages, uribe_vals, color="#c0392b", width=1.0, alpha=0.85)
axes[0].set_ylabel("Menciones por página", fontsize=9)
axes[0].set_title("Álvaro Uribe Vélez", fontsize=11, color="#c0392b", fontweight="bold")
axes[0].set_ylim(0, max(max(uribe_vals)+1, 3))

axes[1].bar(all_pages, petro_vals, color="#2980b9", width=1.0, alpha=0.85)
axes[1].set_ylabel("Menciones por página", fontsize=9)
axes[1].set_title("Gustavo Petro", fontsize=11, color="#2980b9", fontweight="bold")
axes[1].set_xlabel("Página", fontsize=10)
axes[1].set_ylim(0, max(max(petro_vals)+1, 3))

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "menciones_por_pagina.png"), dpi=150)
plt.close()
print("\nGuardado: menciones_por_pagina.png")

# ── Gráfico superpuesto (rolling avg) ───────────────────────────────────────
import pandas as pd
window = 10
u_smooth = pd.Series(uribe_vals).rolling(window, min_periods=1).mean()
p_smooth = pd.Series(petro_vals).rolling(window, min_periods=1).mean()

fig, ax = plt.subplots(figsize=(16, 5))
ax.fill_between(all_pages, u_smooth, alpha=0.3, color="#c0392b")
ax.fill_between(all_pages, p_smooth, alpha=0.3, color="#2980b9")
ax.plot(all_pages, u_smooth, color="#c0392b", linewidth=2, label="Uribe Vélez")
ax.plot(all_pages, p_smooth, color="#2980b9", linewidth=2, label="Gustavo Petro")
ax.set_xlabel("Página", fontsize=10)
ax.set_ylabel(f"Menciones (media móvil {window} páginas)", fontsize=9)
ax.set_title("Intensidad de menciones: Uribe Vélez vs Petro a lo largo del documento",
             fontsize=12, fontweight="bold")
ax.legend(fontsize=10)
ax.axhline(0, color="gray", linewidth=0.5)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "menciones_comparado_timeline.png"), dpi=150)
plt.close()
print("Guardado: menciones_comparado_timeline.png")

# ── Pie chart comparativo ────────────────────────────────────────────────────
totales = {fig: len(hits) for fig, hits in menciones.items()}
fig, ax = plt.subplots(figsize=(6, 5))
colores = ["#c0392b", "#2980b9"]
wedges, texts, autotexts = ax.pie(
    totales.values(), labels=totales.keys(),
    colors=colores, autopct="%1.1f%%",
    startangle=90, textprops={"fontsize": 11}
)
for at in autotexts:
    at.set_fontsize(13)
    at.set_fontweight("bold")
ax.set_title("Proporción de menciones totales", fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "menciones_proporcion.png"), dpi=150)
plt.close()
print("Guardado: menciones_proporcion.png")

# ── Análisis de contexto: ¿en qué tono se mencionan? ────────────────────────
# Palabras de connotación negativa/positiva cerca de cada mención
NEG_WORDS = {
    "corrupción","crimen","criminal","genocidio","masacre","muerte","víctima",
    "violencia","impunidad","engaño","mentira","traición","paramilitarismo",
    "paramilitar","narcotráfico","robo","saqueo","desplazamiento","persecución",
    "represión","autoritarismo","dictadura","fraude","ilegal","ilegítimo",
    "guerra","conflicto","ataque","asesinato","exterminio","terror","terrorismo",
}
POS_WORDS = {
    "paz","acuerdo","reforma","justicia","progreso","desarrollo","democracia",
    "libertad","esperanza","cambio","transformación","bienestar","social",
    "derecho","pueblo","construcción","diálogo","reconciliación","futuro",
}

def analizar_contexto(hits):
    neg_count, pos_count, neutral = 0, 0, 0
    for h in hits:
        ctx = h["contexto"].lower()
        ctx_words = set(re.findall(r"\b\w+\b", ctx))
        neg = len(ctx_words & NEG_WORDS)
        pos = len(ctx_words & POS_WORDS)
        if neg > pos:
            neg_count += 1
        elif pos > neg:
            pos_count += 1
        else:
            neutral += 1
    return {"negativo": neg_count, "positivo": pos_count, "neutro": neutral}

ctx_uribe = analizar_contexto(menciones["Uribe Vélez"])
ctx_petro = analizar_contexto(menciones["Gustavo Petro"])

print("\n" + "="*60)
print("TONO DEL CONTEXTO EN QUE SE MENCIONAN")
print("="*60)
print(f"  Uribe Vélez: {ctx_uribe}")
print(f"  Gustavo Petro: {ctx_petro}")

# Gráfico de tono por figura
fig, axes = plt.subplots(1, 2, figsize=(10, 5))
fig.suptitle("Tono del contexto en que se menciona cada figura",
             fontsize=12, fontweight="bold")

for ax, (figura, ctx, color) in zip(axes, [
    ("Álvaro Uribe Vélez", ctx_uribe, "#c0392b"),
    ("Gustavo Petro",      ctx_petro, "#2980b9"),
]):
    cats  = ["Negativo", "Positivo", "Neutro"]
    vals  = [ctx["negativo"], ctx["positivo"], ctx["neutro"]]
    cols  = ["#e74c3c", "#27ae60", "#95a5a6"]
    bars  = ax.bar(cats, vals, color=cols, edgecolor="white")
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.2,
                str(v), ha="center", fontsize=11, fontweight="bold")
    ax.set_title(figura, fontsize=10, color=color, fontweight="bold")
    ax.set_ylabel("N° de menciones")
    ax.set_ylim(0, max(vals)+3)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "tono_contexto_figuras.png"), dpi=150)
plt.close()
print("Guardado: tono_contexto_figuras.png")

# ── Exportar citas textuales ─────────────────────────────────────────────────
output_txt = os.path.join(OUT_DIR, "citas_figuras_politicas.txt")
with open(output_txt, "w", encoding="utf-8") as f:
    for figura, hits in menciones.items():
        f.write("\n" + "="*70 + "\n")
        f.write(f"  {figura.upper()} — {len(hits)} menciones\n")
        f.write("="*70 + "\n\n")
        paginas_vistas = set()
        for h in hits:
            # Una cita representativa por página
            if h["pagina"] not in paginas_vistas:
                paginas_vistas.add(h["pagina"])
                f.write(f"[Pág. {h['pagina']}] ...{h['contexto']}...\n\n")

print(f"Guardado: citas_figuras_politicas.txt")

# ── Páginas con mayor concentración ─────────────────────────────────────────
print("\n" + "="*60)
print("PÁGINAS CON MÁS MENCIONES")
print("="*60)
print("  Uribe Vélez:")
for pag, cnt in uribe_por_pag.most_common(10):
    print(f"    Pág {pag}: {cnt} menciones")
print("  Gustavo Petro:")
for pag, cnt in petro_por_pag.most_common(10):
    print(f"    Pág {pag}: {cnt} menciones")

# ── Palabras más frecuentes EN el contexto de cada mención ──────────────────
import nltk
try:
    from nltk.corpus import stopwords as nltk_sw
    SW = set(nltk_sw.words("spanish"))
except:
    SW = set()

EXTRA_SW = {"más","así","solo","puede","debe","cada","través","mediante",
            "tanto","bien","hacer","tener","parte","también","sino","ante",
            "desde","hacia","entre","sobre","donde","cual","este","esta",
            "ese","esa","uno","una","ser","estar","haber","hay","han",
            "son","sus","del","las","los","les","nos","como","pero","para",
            "por","con","sin","todo","todos","toda","cuando","quien","que",
            "porque","si","ya","aún","sólo","dicho","sido","mismo","misma"}
SW |= EXTRA_SW

def palabras_contexto(hits, figura_str, topn=25):
    all_words = []
    for h in hits:
        ctx = h["contexto"].lower()
        words = re.findall(r"\b[a-záéíóúüñ]{4,}\b", ctx)
        # excluir el propio nombre
        words = [w for w in words
                 if w not in SW
                 and not any(part in w for part in figura_str.lower().split())]
        all_words.extend(words)
    return Counter(all_words).most_common(topn)

ctx_words_uribe = palabras_contexto(menciones["Uribe Vélez"], "uribe vélez álvaro", 25)
ctx_words_petro = palabras_contexto(menciones["Gustavo Petro"], "gustavo petro", 25)

fig, axes = plt.subplots(1, 2, figsize=(16, 7))
fig.suptitle("Palabras más frecuentes en el contexto de cada mención",
             fontsize=12, fontweight="bold")

for ax, (titulo, data, color) in zip(axes, [
    ("Contexto de menciones a\nÁlvaro Uribe Vélez", ctx_words_uribe, "#c0392b"),
    ("Contexto de menciones a\nGustavo Petro",      ctx_words_petro, "#2980b9"),
]):
    if data:
        labels, vals = zip(*data)
        ax.barh(range(len(labels)), vals, color=color, alpha=0.8)
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=9)
        ax.invert_yaxis()
        ax.set_title(titulo, fontsize=10, fontweight="bold")
        ax.set_xlabel("Frecuencia en contexto")
        for i, v in enumerate(vals):
            ax.text(v+0.1, i, str(v), va="center", fontsize=8)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "palabras_contexto_figuras.png"), dpi=150)
plt.close()
print("Guardado: palabras_contexto_figuras.png")

print("\n✓ Análisis de figuras políticas completo.")

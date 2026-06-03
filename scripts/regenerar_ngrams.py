#!/usr/bin/env python3
"""
Regenera bigrams, trigrams y quadgrams desde texto crudo (sin lematizar)
para evitar artefactos del lematizador como 'uribir vélez'.
"""

import os, re
import fitz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from collections import Counter
from nltk.util import ngrams
from nltk.corpus import stopwords as nltk_sw
import nltk

PDF_PATH = r"C:\Users\David.Munoz\Downloads\programa-gobierno-2026-2030.pdf"
OUT_DIR  = r"C:\Users\David.Munoz\Documents\analisis_politico_ivan_cepeda"

doc = fitz.open(PDF_PATH)
pages = [p.get_text("text") for p in doc]

# Limpiar encabezados de página
clean_pages = []
for pg in pages:
    pg = re.sub(r"PROGRAMA DE GOBIERNO\s+DE IV[AÁ]N CEPEDA CASTRO\s*\|[^|]*\|",
                " ", pg, flags=re.IGNORECASE)
    pg = re.sub(r"©\s*Iv[aá]n Cepeda Castro[^\n]*\n", " ", pg)
    clean_pages.append(pg)

full = " ".join(clean_pages).lower()

base_sw = set(nltk_sw.words("spanish"))
EXTRA_SW = {
    "así","más","será","solo","puede","debe","cada","través","mediante",
    "tanto","bien","hacer","tener","parte","también","sino","ante",
    "desde","hacia","entre","sobre","donde","cual","este","esta",
    "ese","esa","uno","una","ser","estar","haber","hay","han",
    "son","sus","del","las","los","les","nos","como","pero","para",
    "por","con","sin","todo","todos","toda","cuando","quien","que",
    "porque","si","ya","aún","solo","dicho","sido","mismo","misma",
    "castro","cepeda","iván","ivan","programa","gobierno",
    "país","colombia","colombiano","nacional","público","años","año",
    "mil","millones","gran","grande","aquí",
}
SW = base_sw | EXTRA_SW

words = re.findall(r"\b[a-záéíóúüñ]{3,}\b", full)
words_clean = [w for w in words if w not in SW]

def hbar(data, title, filename, color="steelblue"):
    labels, values = zip(*data)
    labels = labels[::-1]
    values = values[::-1]
    fig, ax = plt.subplots(figsize=(13, max(6, len(labels)*0.42)))
    bars = ax.barh(range(len(labels)), values, color=color)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_title(title, fontsize=12, fontweight="bold")
    ax.set_xlabel("Frecuencia")
    for bar, v in zip(bars, values):
        ax.text(bar.get_width()+0.3, bar.get_y()+bar.get_height()/2,
                str(v), va="center", fontsize=8)
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, filename), dpi=150)
    plt.close()
    print(f"Guardado: {filename}")

# Bigrams
bg_freq = Counter(ngrams(words_clean, 2)).most_common(25)
bg_data = [(" ".join(bg), c) for bg, c in bg_freq]
hbar(bg_data, "Top 25 Bigramas — texto real del documento", "top25_bigrams.png", color="darkorange")

# Trigrams
tg_freq = Counter(ngrams(words_clean, 3)).most_common(20)
tg_data = [(" ".join(tg), c) for tg, c in tg_freq]
hbar(tg_data, "Top 20 Trigramas — texto real del documento", "top20_trigrams.png", color="seagreen")

# Quadgrams
qg_freq = Counter(ngrams(words_clean, 4)).most_common(10)
qg_data = [(" ".join(qg), c) for qg, c in qg_freq]
hbar(qg_data, "Top 10 Cuadrigramas — texto real del documento", "top10_quadgrams.png", color="mediumpurple")

print("\nTop 25 bigramas reales:")
for (a,b), c in bg_freq:
    print(f"  {a} {b}: {c}")

#!/usr/bin/env python3
"""
Regenera el wordcloud corrigiendo:
- Elimina 'castro', 'cepeda', 'iván' (encabezado de página, no contenido)
- Incluye 'uribe', 'petro', 'álvaro', 'gustavo' como términos válidos
"""

import os, re, sys
import fitz
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nltk
import spacy
from collections import Counter
from wordcloud import WordCloud

PDF_PATH = r"C:\Users\David.Munoz\Downloads\programa-gobierno-2026-2030.pdf"
OUT_DIR  = r"C:\Users\David.Munoz\Documents\analisis_politico_ivan_cepeda"

nlp = spacy.load("es_core_news_sm")

from nltk.corpus import stopwords as nltk_sw
base_sw = set(nltk_sw.words("spanish"))

# Stopwords: incluye nombres del propio documento que son ruido de encabezado
STOPWORDS = base_sw | {
    "así","más","será","solo","puede","debe","cada","través","mediante",
    "tanto","bien","hacer","tener","parte","también","sino","ante",
    "desde","hacia","entre","sobre","donde","cual","cuales","este",
    "esta","estos","estas","ese","esa","esos","esas","aquel","aquella",
    "uno","una","unos","unas","ser","estar","haber","hay","han",
    "son","sus","del","las","los","les","nos","como","pero","para",
    "por","con","sin","todo","todos","toda","todas","mismo","misma",
    "cuando","quien","quienes","que","qué","cual","cuál","donde","cómo",
    "porque","si","ya","aún","sólo","dicho","sido",
    # ← RUIDO DE ENCABEZADO DE PÁGINA (apellido del candidato repetido en header)
    "castro","cepeda","iván","ivan","programa","gobierno",
    # genéricos sin valor analítico
    "país","colombia","colombiano","colombiana","colombianos","colombianas",
    "nacional","público","pública","años","año","mil","millones",
    "deben","hacer","decir","querer","poder","deber","gran","grande",
}

# ── Extraer texto SIN encabezados de página ──────────────────────────────────
doc_pdf = fitz.open(PDF_PATH)
pages_clean_text = []
for page in doc_pdf:
    full = page.get_text("text")
    # Eliminar la línea de encabezado típica: "PROGRAMA DE GOBIERNO  DE IVÁN CEPEDA CASTRO | N |"
    cleaned = re.sub(
        r"PROGRAMA DE GOBIERNO\s+DE IV[AÁ]N CEPEDA CASTRO\s*\|[^|]*\|",
        " ", full, flags=re.IGNORECASE
    )
    cleaned = re.sub(r"©\s*Iv[aá]n Cepeda Castro[^\n]*\n", " ", cleaned)
    pages_clean_text.append(cleaned)

# ── Limpiar y tokenizar ───────────────────────────────────────────────────────
def clean(text):
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"[0-9]+", " ", text)
    text = re.sub(r"[^\w\sáéíóúüñÁÉÍÓÚÜÑ]", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()

all_tokens = []
for pg in pages_clean_text:
    doc_spacy = nlp(clean(pg)[:100_000])
    tokens = [
        token.lemma_.lower() for token in doc_spacy
        if token.is_alpha
        and token.lemma_.lower() not in STOPWORDS
        and len(token.lemma_) > 2
    ]
    all_tokens.extend(tokens)

freq = Counter(all_tokens)

print(f"Tokens totales: {len(all_tokens):,}")
print(f"Únicos: {len(freq):,}")
print("\nTop 20 (con corrección):")
for w, c in freq.most_common(20):
    print(f"  {w}: {c}")

# ── Wordcloud corregido ───────────────────────────────────────────────────────
wc = WordCloud(
    width=1600, height=900,
    background_color="white",
    colormap="tab20",
    max_words=200,
    collocations=False,
    prefer_horizontal=0.85,
).generate_from_frequencies(freq)

wc.to_file(os.path.join(OUT_DIR, "wordcloud.png"))
print("\nWordcloud regenerado: wordcloud.png")

# ── También regenerar top40 unigrams ─────────────────────────────────────────
top40 = freq.most_common(40)
labels, values = zip(*top40)
labels = labels[::-1]
values = values[::-1]

fig, ax = plt.subplots(figsize=(12, 10))
bars = ax.barh(range(len(labels)), values, color="steelblue")
ax.set_yticks(range(len(labels)))
ax.set_yticklabels(labels, fontsize=9)
ax.set_title("Top 40 palabras más frecuentes (lemmatizadas, sin ruido de encabezado)",
             fontsize=11, fontweight="bold")
ax.set_xlabel("Frecuencia")
for bar, v in zip(bars, values):
    ax.text(bar.get_width()+0.5, bar.get_y()+bar.get_height()/2,
            str(v), va="center", fontsize=8)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "top40_unigrams.png"), dpi=150)
plt.close()
print("Top40 unigrams regenerado: top40_unigrams.png")

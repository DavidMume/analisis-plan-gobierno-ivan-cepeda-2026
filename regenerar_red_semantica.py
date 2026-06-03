#!/usr/bin/env python3
"""
Regenera la red semántica con menos nodos y más legible.
Solo palabras más frecuentes, umbral de similitud más alto,
nodos dimensionados por frecuencia, layout más espaciado.
"""

import os, re
import fitz
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import networkx as nx
from collections import Counter
from gensim.models import Word2Vec
from nltk.corpus import stopwords as nltk_sw
import spacy

PDF_PATH = r"C:\Users\David.Munoz\Downloads\programa-gobierno-2026-2030.pdf"
OUT_DIR  = r"C:\Users\David.Munoz\Documents\analisis_politico_ivan_cepeda"

nlp = spacy.load("es_core_news_sm")
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
    "mil","millones","gran","grande","aquí","primero","hoy","seguir",
    "decir","querer","poder","deber","nuevo","vez","hacer","tener",
}
SW = base_sw | EXTRA_SW

# Extraer y limpiar texto
doc_pdf = fitz.open(PDF_PATH)
pages_tokens = []
for page in doc_pdf:
    pg = page.get_text("text")
    pg = re.sub(r"PROGRAMA DE GOBIERNO\s+DE IV[AÁ]N CEPEDA CASTRO\s*\|[^|]*\|", " ", pg, flags=re.IGNORECASE)
    pg = re.sub(r"[0-9]+|http\S+", " ", pg)
    pg = re.sub(r"[^\w\sáéíóúüñÁÉÍÓÚÜÑ]", " ", pg).lower()
    doc_spacy = nlp(pg[:80_000])
    tokens = [t.lemma_.lower() for t in doc_spacy
              if t.is_alpha and t.lemma_.lower() not in SW and len(t.lemma_) > 3]
    if tokens:
        pages_tokens.append(tokens)

all_tokens = [t for pg in pages_tokens for t in pg]
freq = Counter(all_tokens)

# Entrenar Word2Vec
w2v = Word2Vec(sentences=pages_tokens, vector_size=100, window=5,
               min_count=3, workers=4, epochs=30, seed=42)

# Solo los top 60 palabras más frecuentes que estén en el vocabulario W2V
TOP_N   = 60
THRESHOLD = 0.72   # umbral alto → red menos densa

top_words = [w for w, _ in freq.most_common(200) if w in w2v.wv.key_to_index][:TOP_N]
print(f"Palabras en la red: {len(top_words)}")

# Construir grafo
G = nx.Graph()
for i, w1 in enumerate(top_words):
    for w2 in top_words[i+1:]:
        sim = w2v.wv.similarity(w1, w2)
        if sim > THRESHOLD:
            G.add_edge(w1, w2, weight=float(sim))

# Filtrar nodos aislados
G.remove_nodes_from(list(nx.isolates(G)))
print(f"Nodos: {G.number_of_nodes()} | Aristas: {G.number_of_edges()}")

# Detectar comunidades para colorear
communities = list(nx.community.greedy_modularity_communities(G))
color_map = {}
palette = cm.tab10(np.linspace(0, 0.9, len(communities)))
for i, comm in enumerate(communities):
    for node in comm:
        color_map[node] = palette[i]

node_colors = [color_map.get(n, (0.5,0.5,0.5,1)) for n in G.nodes()]

# Tamaño de nodo según frecuencia en el documento
max_freq = max(freq.get(n, 1) for n in G.nodes())
node_sizes = [300 + 1800 * (freq.get(n, 1) / max_freq) for n in G.nodes()]

# Grosor de arista según similitud
edge_weights = [G[u][v]["weight"] for u, v in G.edges()]
edge_widths  = [1.5 + 4.0 * (w - THRESHOLD) / (1 - THRESHOLD) for w in edge_weights]

# Layout: más separado
pos = nx.spring_layout(G, seed=42, k=2.8, iterations=80)

fig, ax = plt.subplots(figsize=(16, 12))
fig.patch.set_facecolor("white")
ax.set_facecolor("#f8f9fa")

nx.draw_networkx_edges(G, pos, ax=ax, width=edge_widths,
                       edge_color="#aaaaaa", alpha=0.6)
nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors,
                       node_size=node_sizes, alpha=0.92, linewidths=0.8,
                       edgecolors="white")
nx.draw_networkx_labels(G, pos, ax=ax, font_size=9, font_weight="bold",
                        font_color="#1a1a2e")

ax.set_title(
    "Red semántica — conceptos clave del programa de gobierno\n"
    "Nodos: tamaño = frecuencia | Color = comunidad semántica | Aristas: similitud coseno > 0.72",
    fontsize=12, fontweight="bold", pad=20
)
ax.axis("off")

# Leyenda de comunidades
legend_patches = []
for i, comm in enumerate(communities):
    if len(comm) >= 2:
        label = ", ".join(sorted(comm)[:3]) + ("..." if len(comm) > 3 else "")
        legend_patches.append(
            plt.matplotlib.patches.Patch(color=palette[i], label=label)
        )
if legend_patches:
    ax.legend(handles=legend_patches, loc="lower left", fontsize=7,
              title="Comunidades semánticas", title_fontsize=8,
              framealpha=0.9, borderpad=0.8)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "semantic_network.png"), dpi=160, bbox_inches="tight")
plt.close()
print("Guardado: semantic_network.png")

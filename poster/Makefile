PYTHON ?= python3
.PHONY: all pdf preview
all: pdf
pdf:
	$(PYTHON) build_poster.py
preview: pdf
	pdftoppm -singlefile -scale-to 2400 -png Omni-RAG_Poster_13522057.pdf Omni-RAG_Poster_13522057

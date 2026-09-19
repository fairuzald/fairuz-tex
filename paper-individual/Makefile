LATEX ?= xelatex
BIBER ?= biber
OUTPUT := OMNI-RAG_Individual_Knowledge_Base_IEEE
BUILD := build

.PHONY: all pdf clean

all: pdf

pdf:
	@mkdir -p $(BUILD)
	$(LATEX) -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=$(BUILD) -jobname=$(OUTPUT) main.tex
	$(BIBER) --input-directory=$(BUILD) --output-directory=$(BUILD) $(OUTPUT)
	$(LATEX) -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=$(BUILD) -jobname=$(OUTPUT) main.tex
	$(LATEX) -interaction=nonstopmode -halt-on-error -file-line-error -output-directory=$(BUILD) -jobname=$(OUTPUT) main.tex
	cp $(BUILD)/$(OUTPUT).pdf $(OUTPUT).pdf

clean:
	rm -rf $(BUILD) $(OUTPUT).pdf

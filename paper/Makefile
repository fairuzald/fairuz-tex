LATEX ?= xelatex
BIBER ?= biber
OUTPUT := Omni-RAG_Paper_13522057
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
	rm -f $(BUILD)/$(OUTPUT).aux $(BUILD)/$(OUTPUT).bbl $(BUILD)/$(OUTPUT).bcf $(BUILD)/$(OUTPUT).blg $(BUILD)/$(OUTPUT).log $(BUILD)/$(OUTPUT).out $(BUILD)/$(OUTPUT).run.xml $(BUILD)/$(OUTPUT).pdf

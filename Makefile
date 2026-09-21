TEXDIR := src
MAIN := main
OUTPUT := IF4092_Laporan_SidangTA_13522057
LATEX := xelatex
BIBER := biber
LATEXMK := latexmk
PREVIEWER ?= xdg-open
NODE ?= node
PUPPETEER_EXECUTABLE_PATH ?= /usr/bin/google-chrome
MMDC := node_modules/@mermaid-js/mermaid-cli/src/cli.js
DIAGRAM_SRC := $(wildcard src/diagrams/*.mmd)
DIAGRAM_OUT := $(patsubst src/diagrams/%.mmd,src/generated/diagrams/%.png,$(DIAGRAM_SRC))

REPORT_OUTPUT_DIR := output/pdf
REPORT_SIGNED_PDF := $(REPORT_OUTPUT_DIR)/IF4092_Laporan_SidangTA_13522057_21-September-2026-dengan-tanda-tangan.pdf
REPORT_UNSIGNED_PDF := $(REPORT_OUTPUT_DIR)/IF4092_Laporan_SidangTA_13522057_22-September-2026-tanpa-tanda-tangan.pdf

.PHONY: all pdf pdf-variants pdf-signed pdf-unsigned paper poster diagrams watch clean help

all: pdf

paper:
	$(MAKE) -C paper pdf

poster:
	$(MAKE) -C poster preview

pdf: diagrams
	cd $(TEXDIR) && $(LATEX) -interaction=nonstopmode -halt-on-error -file-line-error $(MAIN).tex
	cd $(TEXDIR) && $(BIBER) $(MAIN)
	cd $(TEXDIR) && $(LATEX) -interaction=nonstopmode -halt-on-error -file-line-error $(MAIN).tex
	cd $(TEXDIR) && $(LATEX) -interaction=nonstopmode -halt-on-error -file-line-error $(MAIN).tex
	@test -f $(TEXDIR)/$(MAIN).pdf || { echo "Error: $(TEXDIR)/$(MAIN).pdf was not produced."; exit 1; }
	cp $(TEXDIR)/$(MAIN).pdf $(TEXDIR)/$(OUTPUT).pdf
	rm -f $(TEXDIR)/$(MAIN).pdf

pdf-variants: pdf-signed pdf-unsigned

pdf-signed: diagrams
	@mkdir -p $(REPORT_OUTPUT_DIR)
	cd $(TEXDIR) && $(LATEXMK) -pdfxe -interaction=nonstopmode -halt-on-error -file-line-error $(MAIN).tex
	cp $(TEXDIR)/$(MAIN).pdf $(REPORT_SIGNED_PDF)

pdf-unsigned: diagrams
	@mkdir -p $(REPORT_OUTPUT_DIR)
	cd $(TEXDIR) && $(LATEXMK) -pdfxe -interaction=nonstopmode -halt-on-error -file-line-error main-unsigned.tex
	cp $(TEXDIR)/main-unsigned.pdf $(REPORT_UNSIGNED_PDF)

diagrams: $(DIAGRAM_OUT)

src/generated/diagrams/%.png: src/diagrams/%.mmd
	@mkdir -p $(dir $@)
	@test -f $(MMDC) || { echo "Error: Mermaid CLI is missing. Run npm install first."; exit 1; }
	PUPPETEER_EXECUTABLE_PATH=$(PUPPETEER_EXECUTABLE_PATH) $(NODE) $(MMDC) -i $< -o $@ -b transparent -s 2

watch:
	@command -v $(LATEXMK) >/dev/null 2>&1 || { \
		echo "Error: $(LATEXMK) is required for 'make watch'."; \
		exit 1; \
	}
	@command -v $(PREVIEWER) >/dev/null 2>&1 || { \
		echo "Error: $(PREVIEWER) is required for the PDF preview."; \
		exit 1; \
	}
	@cd $(TEXDIR) && $(LATEXMK) \
		-pdfxe -pvc -view=pdf \
		-interaction=nonstopmode -halt-on-error -file-line-error \
		-e '$$pdf_previewer="$(PREVIEWER) %O %S"' \
		$(MAIN).tex

clean:
	rm -f $(TEXDIR)/$(MAIN).{aux,bcf,blg,log,lof,lot,out,pdf,run.xml,toc}
	rm -f $(TEXDIR)/$(OUTPUT).pdf
	rm -f $(TEXDIR)/chapters/*.aux
	rm -f $(TEXDIR)/appendices/*.aux
	rm -rf $(TEXDIR)/generated/diagrams

help:
	@printf '%s\n' 'Available targets:'
	@printf '%s\n' '  make poster Create the A1 research poster PDF and PNG'
	@printf '%s\n' '  make paper  Compile the short article in paper/'
	@printf '%s\n' '  make        Compile the proposal PDF'
	@printf '%s\n' '  make pdf    Compile the proposal PDF to src/IF4092_Laporan_SidangTA_13522057.pdf'
	@printf '%s\n' '  make pdf-variants Build dated signed and unsigned report PDFs under output/pdf/'
	@printf '%s\n' '  make diagrams Render Mermaid diagram sources to PNG assets'
	@printf '%s\n' '  make watch  Watch sources and refresh the PDF preview'
	@printf '%s\n' '  make clean  Remove generated LaTeX files'

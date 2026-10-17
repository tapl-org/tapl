TEX_PAPERS = semantics
PDF_ENGINE = pdflatex

# macOS basictex installs here; add to PATH if present
export PATH := /Library/TeX/texbin:$(PATH)

.PHONY: all clean

all: $(addsuffix .pdf,$(TEX_PAPERS))

%.pdf: %.tex
	$(PDF_ENGINE) -interaction=nonstopmode -halt-on-error $< >/dev/null
	$(PDF_ENGINE) -interaction=nonstopmode -halt-on-error $<

clean:
	rm -f $(addsuffix .pdf,$(TEX_PAPERS))
	rm -f *.aux *.log *.out

MD_PAPERS = xi-calculus tapl-paper
TEX_PAPERS = ground-rules
PDF_ENGINE = pdflatex

# macOS basictex installs here; add to PATH if present
export PATH := /Library/TeX/texbin:$(PATH)

.PHONY: all clean

all: $(addsuffix .pdf,$(MD_PAPERS)) $(addsuffix .pdf,$(TEX_PAPERS))

%.pdf: %.md
	pandoc $< -o $@ --pdf-engine=$(PDF_ENGINE) --highlight-style=tango

%.pdf: %.tex
	$(PDF_ENGINE) $<

clean:
	rm -f $(addsuffix .pdf,$(MD_PAPERS)) $(addsuffix .pdf,$(TEX_PAPERS))
	rm -f *.aux *.log *.out

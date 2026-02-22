TEX_PAPERS = theta-calculus
PDF_ENGINE = pdflatex

# macOS basictex installs here; add to PATH if present
export PATH := /Library/TeX/texbin:$(PATH)

.PHONY: all clean

all: $(addsuffix .pdf,$(TEX_PAPERS))

%.pdf: %.tex
	$(PDF_ENGINE) $<

clean:
	rm -f $(addsuffix .pdf,$(TEX_PAPERS))
	rm -f *.aux *.log *.out

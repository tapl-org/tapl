PAPERS = xi-calculus tapl-paper ground-rules
PDF_ENGINE = pdflatex

# macOS basictex installs here; add to PATH if present
export PATH := /Library/TeX/texbin:$(PATH)

.PHONY: all clean

all: $(addsuffix .pdf,$(PAPERS))

%.pdf: %.md
	pandoc $< -o $@ --pdf-engine=$(PDF_ENGINE) --highlight-style=tango

clean:
	rm -f $(addsuffix .pdf,$(PAPERS))

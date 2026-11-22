# Part of the TAPL project, under the Apache License v2.0 with LLVM
# Exceptions. See /LICENSE for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

# Builds the arXiv submissions: one PDF (for checking) and one tarball (for
# uploading) per paper. theta-calculus.tex is taken from doc/; oymomo-calculus.tex
# is the arXiv edition in this folder, a copy of doc/oymomo-calculus.tex.

BUILD = build
export PATH := /Library/TeX/texbin:$(PATH)

.PHONY: all clean
all: $(BUILD)/theta-calculus.tar.gz $(BUILD)/oymomo-calculus.tar.gz

# One set of rules per paper: $(1) is its name, $(2) its source.
define paper
$(BUILD)/$(1)/$(1).tex: $(2)
	mkdir -p $$(dir $$@)
	cp $$< $$@

# Two runs settle references; the second must leave none undefined.
$(BUILD)/$(1)/$(1).pdf: $(BUILD)/$(1)/$(1).tex
	cd $(BUILD)/$(1) && pdflatex -interaction=nonstopmode -halt-on-error $(1).tex >/dev/null
	cd $(BUILD)/$(1) && pdflatex -interaction=nonstopmode -halt-on-error $(1).tex >/dev/null
	! grep -E '(Reference|Citation).*undefined|Rerun to get' $(BUILD)/$(1)/$(1).log

# arXiv compiles the source itself: the tarball holds only the .tex.
$(BUILD)/$(1).tar.gz: $(BUILD)/$(1)/$(1).pdf
	tar -czf $$@ -C $(BUILD)/$(1) $(1).tex
endef

$(eval $(call paper,theta-calculus,../theta-calculus.tex))
$(eval $(call paper,oymomo-calculus,oymomo-calculus.tex))

clean:
	rm -rf build

SHELL=/bin/bash
PACKAGE=acmart
MAIN = spec_mining_final_report
PDF = $(MAIN).pdf

all:  ${PDF}

%.pdf: %.tex $(PACKAGE).cls ACM-Reference-Format.bst
	texfot pdflatex --shell-escape $<
	bibtex $(basename $<)
	texfot pdflatex --shell-escape $<
	texfot pdflatex --shell-escape $<

clean:
	$(RM)  *.log *.aux \
	*.cfg *.glo *.idx *.toc \
	*.ilg *.ind *.out *.lof \
	*.lot *.bbl *.blg *.gls *.cut *.hd \
	*.dvi *.ps *.thm *.tgz *.zip *.rpi $(PDF)
	rm -rf _minted-$(MAIN)

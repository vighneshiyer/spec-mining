SHELL=/bin/bash
PACKAGE=acmart
PDF = spec_mining_final_report.pdf

all:  ${PDF}

%.pdf: %.tex $(PACKAGE).cls ACM-Reference-Format.bst
	texfot pdflatex $<
	bibtex $(basename $<)
	texfot pdflatex $<
	texfot pdflatex $<
	#- cd $(dir $@) && bibtex $(notdir $(basename $<))
	#cd $(dir $@) && pdflatex $(notdir $<)
	#cd $(dir $@) && pdflatex $(notdir $<)
	#while ( grep -q '^LaTeX Warning: Label(s) may have changed' $(basename $<).log) \
	#  do cd $(dir $@) && pdflatex $(notdir $<); done

clean:
	$(RM)  *.log *.aux \
	*.cfg *.glo *.idx *.toc \
	*.ilg *.ind *.out *.lof \
	*.lot *.bbl *.blg *.gls *.cut *.hd \
	*.dvi *.ps *.thm *.tgz *.zip *.rpi $(PDF)

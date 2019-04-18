main = proposal

pdf : $(main).pdf
.PHONY: pdf

%.pdf : %.tex references.bib
	texfot pdflatex -shell-escape $(main).tex
	texfot biber $(main).bcf
	texfot pdflatex -shell-escape $(main).tex
	texfot pdflatex -shell-escape $(main).tex

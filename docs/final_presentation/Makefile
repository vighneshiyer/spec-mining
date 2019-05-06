srcdir  = .

main = spec_mining_final_presentation
figs = $(wildcard figs/*)
style = $(shell find . -maxdepth 2 -name "*.sty")

pdf : $(main).pdf
.PHONY: pdf

%.pdf: %.tex $(figs) $(style) references.bib
	texfot lualatex -shell-escape $(main).tex
	#texfot biber $(main).bcf
	#texfot lualatex -shell-escape $(main).tex
	#texfot lualatex -shell-escape $(main).tex

clean :
	 rm -rf $(main).pdf *.aux *.out *.log _minted* *.bbl *.bcf *.blg *.nav *.run.xml *.snm *.toc *.vrb

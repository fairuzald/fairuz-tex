# A1 Thesis Poster

The poster is a single-page A1 portrait composition for the individual
knowledge-base construction contribution to OMNI-RAG. It follows the story
`Problem -> Objective -> Architecture -> Experimental setup -> Evidence ->
Takeaways` and uses the original ITB logo from `src/images/itb-logo.png`.

Build the PDF with:

```bash
python3 poster/build_poster.py
```

The final PDF is written to `output/pdf/OMNI-RAG_Poster_A1.pdf`. A PNG preview
can be generated with Poppler:

```bash
mkdir -p output/png
pdftoppm -png -r 120 output/pdf/OMNI-RAG_Poster_A1.pdf output/png/OMNI-RAG_Poster_A1
```

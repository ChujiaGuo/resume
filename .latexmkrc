# Set default engine to pdflatex (use 5 for xelatex, 4 for lualatex)
$pdf_mode = 1;

# Route all intermediate files to a build/ directory
$out_dir = 'build/latexmk';

# Silence standard output; only print warnings and errors
$silent = 1;

# Automatically copy the generated PDF from build/ back to the root working directory
$cleanup_mode = 0;
$compiling_cmd = 0;
$success_cmd = 'mv %D .';

# Extra file extensions to remove when running cleanup
$clean_ext = 'synctex.gz synctex.gz(busy) run.xml bcf fdb_latexmk fls nav snm vrb';
# Notebook troubleshooting (SignalSpring)

## Invalid API key
Common causes:
- Environment variable not set in the same shell that launched Jupyter
- Leading/trailing whitespace when copying keys
- Using the wrong variable name

Steps:
1. Restart the notebook kernel.
2. In a notebook cell, print whether the env var is present (do NOT print the key itself).
3. Re-copy the key and paste carefully; avoid spaces.

## Missing file errors (FileNotFoundError)
Common causes:
- Running from the wrong working directory
- Renaming the `data/` or `kb/` folder

Steps:
1. Confirm the path exists relative to the notebook.
2. Use `Path(...).resolve()` to see the absolute path.



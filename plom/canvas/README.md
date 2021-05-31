# Canvas integration
This is a collection of scripts meant to help `plom` interface with
the [Canvas API](https://canvas.instructure.com/doc/api) using the
[`canvasapi` Python library](https://github.com/ucfopen/canvasapi).

The goal is to allow one to substitute Plom for Canvas's SpeedGrader.

This is very much pre-alpha.


## Pushing completed grading back to Canvas

1. Create `api_secrets.py` with containing:
   ```
   my_key = "11224~AABBCCDDEEFF..."
   ```

2. After you finish grading, `plom_push_to_canvas.py` will push the
   completed marks and reassembled PDF files to a Canvas Assignment.
   Run `python plom_push_to_canvas.py -h` for details.


## Starting a server automatically from a Canvas Assignment.

1. Create `api_secrets.py` as above.

2. Run `python canvas_server.py`
   You will need the `aria2c` command-line downloader in addition
   to the usual Plom dependencies.

3. Follow prompts.

4. Go the directory you created and run `plom-server launch`.

# Canvas integration
This is a collection of scripts meant to help `plom` interface with
the [Canvas API](https://canvas.instructure.com/doc/api/). The goal is
to allow one to substitute `plom` for Canvas's `SpeedGrader` feature.

This is very much pre-alpha.


## Rough guide

0. Install `aria2c` command-line downloader.

1. Create api_secrets.py with containing:
   ```
   my_key = "11224~AABBCCDDEEFF..."
   ```

2. Run `python canvas_server.py`

3. Follow prompts.

4. Go the directory you created and run `plom-server launch`.

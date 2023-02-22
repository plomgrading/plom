To run the django demo use

```
python -m demo
```

from the plom/django directory


If the demo crashes (or you force quit out of it) then you may have
lingering huey tasks floating about that you'll need to terminate
before running again. On unix system the easiest way to do this is to
run

```
pkill -KILL -f manage.py
```

This will terminate **any** user process that includes "manage.py",
which is (basically) all running django related stuff.... not just
those associated with the demo. **Use with care**

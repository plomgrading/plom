<!--
__copyright__ = "Copyright (C) 2023 Andrew Rechnitzer"
__copyright__ = "Copyright (C) 2023 Colin B. Macdonald"
__license__ = "AGPL-3.0-or-later"
 -->

To run the django demo use

```
python3 -m demo
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

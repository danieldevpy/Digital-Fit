"""Permite `python -m eval ...` além de `python -m eval.evalctl ...`."""

from eval.evalctl import main

raise SystemExit(main())

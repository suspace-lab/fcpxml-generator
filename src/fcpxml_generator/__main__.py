"""Allow `python -m fcpxml_generator` as an alternative to `fcpxml`."""

import sys

from .cli import main

sys.exit(main())

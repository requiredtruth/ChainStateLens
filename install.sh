#!/usr/bin/env sh
set -eu
python -m unittest discover -s tests -v
python -m compileall -q chainstatelens tests
./run.sh >/dev/null
echo "ChainStateLens verification complete"

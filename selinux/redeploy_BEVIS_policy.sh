#!/bin/bash
  
rm -f BEVIS.mod BEVIS.pp

# Build the policy package (.pp) file from type enforcement (.te) and file contexts (.fc) files.
checkmodule -M -m -o BEVIS.mod BEVIS.te
semodule_package -o BEVIS.pp -m BEVIS.mod -f BEVIS.fc

# Install it.
semodule -i BEVIS.pp

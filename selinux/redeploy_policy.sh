#!/bin/bash
  
rm -f anubis.mod anubis.pp

# Build the policy package (.pp) file from type enforcement (.te) and file contexts (.fc) files.
checkmodule -M -m -o anubis.mod anubis.te
semodule_package -o anubis.pp -m anubis.mod -f anubis.fc

# Install it.
semodule -i anubis.pp

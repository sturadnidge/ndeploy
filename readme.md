ndeploy
======

a tiny, simple application designed to provide automated os installs

best used with ipxe as follows:

- compile your own ipxe binary (make bin/undionly.kpxe EMBED=ndeploy.ipxe),
  where ndeploy.ipxe looks something like:

```
#!ipxe
dhcp
echo
echo attempting to netboot with IP ${ip}
echo
set ndeploy_server ndeploy.your.domain
chain http://${ndeploy_server}/provisions/${uuid}/boot ||
echo
echo provision not found or net boot failed, booting ipxe shell
echo
shell
```

- everything after ${ndeploy_server} must be as above (the hostname
  can be whatever you like - co-locating the ndeploy service with 
  your tftp service isn't a bad idea).

- setup your DHCP insfrastructure to serve undionly.kpxe to all pxe boot requests

- keep your os binary serving http infrastructure somewhere else

- make sure you create some .ipxe and .ks files in the templates directory before 
  doing anything. The web UI is populated from them.

- check out the sample files in the templates directory for some pointers


nDeploy
======

a tiny, simple Flask-based application designed to provide automated os installs

best used with ipxe as follows:

- compile your own ipxe binary (`make bin/undionly.kpxe EMBED=ndeploy.ipxe`),
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

- everything after ${ndeploy_server} must be as above

- setup your DHCP insfrastructure to serve undionly.kpxe to all pxe boot requests

- set the boot order on all your servers to pxe boot first

- provision some boot sequences and go go go!

usage guidance
--------------

- keep your binary serving http infrastructure somewhere else

- make sure you create some .ipxe and .ks files (by hand) in the templates directory before 
  doing anything. The provisioning process requires them and the web UI is populated from them.

- check out the sample files in the templates directory for some pointers

- check out provision.json in the templates directory for an idea of the data model

- the web UI is just javascript talking to the backend API

- the web UI only gives you 3 options for a build sequence, but you can create as many as you want via curl:

```
curl -i -H "Content-Type: application/json" -X POST -d \
'{
"uuid":"b9ae67b8-25e7-4633-b46a-8702c4bf1d34",
"fqdn":"ndeploy-test.local",
"os_template":"centos_6.4.ks",
"boot_sequence":{"1":"firmware_1.ipxe","2":"firmware_2.ipxe","3":"centos_6.4.ipxe","4":"local.ipxe",}
}' \
http://[ndeploy.fqdn]/provisions/
```

- to quickly reprovision something `curl -X POST http://[ndeploy.fqdn]/provisions/[uuid]/reprovision`


todo
----

- build out DNS resolution function
- build a network information service
- ~~node.js~~ gevent rewrite

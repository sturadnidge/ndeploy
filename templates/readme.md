with the exception of provision.json, valid options for the 'os_install_file'
and 'boot_sequence' properties of a provision go in here. 

use a '.ipxe' extension for boot files

use a '.ks' extension  for kickstart files

a get request to /templates will return a directory listing of .ipxe
and .ks files only.

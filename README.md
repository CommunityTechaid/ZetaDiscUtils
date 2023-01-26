# ZetaDiscWipe
Script for using Zeta to wipe drives

## External Requirements
Requires ata-secure-erase.sh (https://github.com/TigerOnVaseline/ata-secure-erase)

## Internal setup
Both this script and ata-secure-erase.sh have been added to /usr/local/bin as `CTADiscWipe` and `ata-secure-erase` to enable users to easily access and run the script.

Additionally, an unpriveleged user `CTA` has been created that has specific permissions to run the required `ata-secure-erase` via sudo without need for password prompting. This is done by adding the following line to the sudoers file:
```
CTA ALL=(ALL) NOPASSWD: /usr/local/bin/ata-secure-erase
```

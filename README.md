# ZetaDiscUtils
Scripts for using Zeta to handle drives

## Requirements
### DiskHealth
Requires:
 - lsscsi 
 - skdump, sktest both provided by libatasmart

### DiskWipe
Requires:
 - ata-secure-erase.sh (https://github.com/TigerOnVaseline/ata-secure-erase)

## Setup
### Install
Copy scripts and ata-secure-erase.sh to /usr/local/bin to enable users to easily access and run them.

### User
To allow ease of use, create an unpriveleged user `CTA` that should be given specific permissions to run the required the required privileged commands via sudo without need for password prompting. This is done by adding the following line to the sudoers file:
```
CTA ALL=(ALL) NOPASSWD: /usr/local/bin/ata-secure-erase,/usr/bin/skdump,usr/bin/sktest
```

### Shortcut
TODO - Grab example off Zeta


## Usage
- Load front bays with drives
- Wait ~30 secs for all of them to spin up
- Run desired script. (Normally, `CTADiskHealth` followed by `CTADiskWipe`) This can either be done from a terminal or via the installed shortcut by pressing the Windows key and typing `CTA`

### CTADiskHealth
Gets the drives to run a short self-diagnostic test which usual takes only a couple of minutes to run. After that it looks at the report and flags any drives that are suspect and displays the results in a table that represents the physical layout of the front bay.

If an unwiped drive is flagged as being bad, the current recommendation is to physically destroy the drive.

### CTADiskWipe
Current gets all the drives present in the system that aren't the main system drive (i.e., every disk other than the one that's mounted at `/`), asks for confirmation from the user that the drive list seems sane and then spawns new terminal windows to run `ata-secure-erase` on each drive in parallel.
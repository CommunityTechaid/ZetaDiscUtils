#!/bin/bash
# Usage: 
#      ZetaDiscWipe.sh
#
# Last updated:
#      2023/01/26
#
# Options:
#      None at the moment
#
# Description:
#      This is a wrapper script to use the ata-secure-erase.sh to wipe drives in the hotswap
#      bay of Zeta in a reasonibly foolproof fashion
#
# Caveats:
#      - Requires ata-secure-erase.sh (https://github.com/TigerOnVaseline/ata-secure-erase),
#        preferably in the users path
#
# TODO:
#      - Investigate detecting secure-erase in progress
#      - Get main script to properly wait for child windows to finish 
#
#########################################################


intro() {
    printf \
"
###############################
#                             #
#         Wiping Time         #
#                             #
###############################
"
}

fetch_disk_info() {
    # Use lsblk to get all current disks
    all_disks=$(lsblk --raw --noheadings | grep disk | cut -d " " -f 1)
    # Use lsblk and grep to find the disk where / is mounted
    root_disk=$(lsblk --raw --noheadings | grep / | awk '{print substr($0, 0,3)}')

    # Go through all disks and if they aren't the root disk add them to an array to wipe
    for disk in $all_disks; do
        if [[ $disk != "$root_disk" ]]; then
            disks_to_wipe+=("$disk")
        fi
    done

    # Store number of disks to wipe as a var
    num_to_wipe=${#disks_to_wipe[@]}

    # Print some info to be useful
    printf "Will be wiping %s disks:\n" "$num_to_wipe" 
    printf "/dev/%s\n" "${disks_to_wipe[@]}"
}

sanity_check() {
    # Give the user to nope out
    # Wait for 1 character of input
    read -r -n 1 -p "Proceed? (Y/N) : " proceed_input
    # If lowercase user input is y then proceed
    if [ "${proceed_input,,}" == "y" ]; then
        printf "\nPROCEEDING"
    else
        printf "\nExiting..."
        exit
    fi
}

spawn() {
    printf "\nWill be opening %s new windows to wipe the drives in 5 seconds..." "$num_to_wipe"

    sleep 5

    for disk in "${disks_to_wipe[@]}"; do
        # Spawn new terminal, print time, start the wipe and then print DONE when finished
        # Exec bash leaves the terminal open. Long line as multi-line bugged out
        gnome-terminal -- bash -c "date +Start\ time\:\ %H:%M; sudo ata-secure-erase -f /dev/$disk; echo \"DONE WIPING /dev/$disk\"; exec bash"
    done
}

finished() {
    printf \
"
Finished opening the windows.
"
}

main() {
    intro
    fetch_disk_info
    sanity_check
    spawn
    wait
    finished
}

main

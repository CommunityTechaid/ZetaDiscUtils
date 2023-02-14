#!/bin/bash
# Usage: 
#      CTADiscHealth.sh
#
# Last updated:
#      2023/02/01
#
# Options:
#      None at the moment
#
# Description:
#      This script looks for the front bay drives via lsscsi, gets them to run a 
#      SMART short test and then prints out a human friendly summary
#
# Caveats:
#      - Requires lsscsi and skdump, sktest from libatasmart package
#      - Presumes ATA port numbers are static. 
#
# TODO:
#      - Quietly handle missing disks / empty bays
#      - Look into table cell padding issue
#
#########################################################

printf \
"\
###############################
#                             #
#      Disk Health Time       #
#                             #
###############################
"

# Bay ATA port numbers, as determined
# via lsscsi
# ---------
# | 8 | 6 |
# ---------
# | 4 | 7 |
# ---------
# | 5 | 9 | 
# ---------

position_array=(disk_tl disk_tr disk_ml disk_mr disk_bl disk_br)

# Get /dev location for later use
disk_tl=$(lsscsi -b | grep "\[8:" | grep -Eo "/dev/[a-z]{3}")
disk_tr=$(lsscsi -b | grep "\[6:" | grep -Eo "/dev/[a-z]{3}")
disk_ml=$(lsscsi -b | grep "\[4:" | grep -Eo "/dev/[a-z]{3}")
disk_mr=$(lsscsi -b | grep "\[7:" | grep -Eo "/dev/[a-z]{3}")
disk_bl=$(lsscsi -b | grep "\[5:" | grep -Eo "/dev/[a-z]{3}")
disk_br=$(lsscsi -b | grep "\[9:" | grep -Eo "/dev/[a-z]{3}")

# Get model for human friendly printing
disk_tl_pretty=$(lsscsi -c | grep -A1 "scsi8" | grep -Po "(?<=Model: )(.*?)(?= Rev)")
disk_tr_pretty=$(lsscsi -c | grep -A1 "scsi6" | grep -Po "(?<=Model: )(.*?)(?= Rev)")
disk_ml_pretty=$(lsscsi -c | grep -A1 "scsi4" | grep -Po "(?<=Model: )(.*?)(?= Rev)")
disk_mr_pretty=$(lsscsi -c | grep -A1 "scsi7" | grep -Po "(?<=Model: )(.*?)(?= Rev)")
disk_bl_pretty=$(lsscsi -c | grep -A1 "scsi5" | grep -Po "(?<=Model: )(.*?)(?= Rev)")
disk_br_pretty=$(lsscsi -c | grep -A1 "scsi9" | grep -Po "(?<=Model: )(.*?)(?= Rev)")

# Append size info to pretty
disk_tl_pretty+=$(lsscsi -bs | grep "\[8:" | awk '{print ": "$3}')
disk_tr_pretty+=$(lsscsi -bs | grep "\[6:" | awk '{print ": "$3}')
disk_ml_pretty+=$(lsscsi -bs | grep "\[4:" | awk '{print ": "$3}')
disk_mr_pretty+=$(lsscsi -bs | grep "\[7:" | awk '{print ": "$3}')
disk_bl_pretty+=$(lsscsi -bs | grep "\[5:" | awk '{print ": "$3}')
disk_br_pretty+=$(lsscsi -bs | grep "\[9:" | awk '{print ": "$3}')

# Set default wait time
time_to_wait=0

# Check if any disks report larger and then extend test wait time
for disk in "${position_array[@]}"; do
	if [[ ${disk} ]]; then
		disk_test_time=$(sudo skdump "${!disk}" | grep "Short Self-Test Polling" | grep -Eo "[[:digit:]]")
		if [[ $disk_test_time > $time_to_wait ]]; then
			time_to_wait=$disk_test_time
		fi
	fi
done

# for each disk if present run the short test
for disk in "${position_array[@]}"; do
	if [[ ${disk} ]]; then
		# echo "${!disk}"
		# run short test
		sudo sktest "${!disk}" short
	fi
done

wait_end=$(date -ud "$time_to_wait minutes" +%s)

printf "We need to wait %s minutes for some tests to run...\n" "$time_to_wait"
while [[ $(date -u +%s) -le $wait_end ]] ;do 
	for s in / - \\ \|; do 
		printf "\r%s" $s
		sleep .1
	done
done

# Remove stray char left from spinner
printf "\r"

# for each disk if present run the short test
for disk in "${position_array[@]}"; do
	if [[ ${disk} ]]; then
		# get skdump status
		status=$(sudo skdump --overall "${!disk}")
		if [[ $status != "GOOD" ]]; then
			status="$(tput setaf 1)$status$(tput sgr0)             "
		fi
		pretty="${disk}_pretty"
		printf -v "$pretty" "%s" "${!pretty}: $status"
	fi
done


# pretty print layout

row="#######################################################################################################"
col="#                                                  #                                                  #"
cell="                                                "

printf \
"\
$row
$col
# %s%s # %s%s #
# %s%s # %s%s #
$col
$row
$col
# %s%s # %s%s #
# %s%s # %s%s #
$col
$row
$col
# %s%s # %s%s #
# %s%s # %s%s #
$col
$row
" \
"$disk_tl_pretty" "${cell:${#disk_tl_pretty}}" \
"$disk_tr_pretty" "${cell:${#disk_tr_pretty}}" \
"$disk_tl" "${cell:${#disk_tl}}" \
"$disk_tr" "${cell:${#disk_tr}}" \
"$disk_ml_pretty" "${cell:${#disk_ml_pretty}}" \
"$disk_mr_pretty" "${cell:${#disk_mr_pretty}}" \
"$disk_ml" "${cell:${#disk_ml}}" \
"$disk_mr" "${cell:${#disk_mr}}" \
"$disk_bl_pretty" "${cell:${#disk_bl_pretty}}" \
"$disk_br_pretty" "${cell:${#disk_br_pretty}}" \
"$disk_bl" "${cell:${#disk_bl}}" \
"$disk_br" "${cell:${#disk_br}}" 
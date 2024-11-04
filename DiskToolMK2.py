#!/usr/bin/python3
# Usage:
#   DiskToolMK2.py
#
# Options:
#   None at the moment
#
# Description:
#   A python GUI to help volunteers wipe discs on zeta
#
# Caveats:
#   - Relies on physical hardware in zeta
#
# TODO:
#   - Everything
#
# Author:
#   tom.cronin@communitytechaid.org.uk
#
##################################################

from dataclasses import dataclass, MISSING
from datetime import datetime
from time import sleep
import subprocess
import re
import os
import fnmatch
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout,
                             QHBoxLayout, QLabel, QGridLayout, QGroupBox,
                             QLineEdit, QProgressBar, QMessageBox)
from PyQt5.QtCore import *
import paramiko


@dataclass
class Disk:
    position: str = None
    bay_port_number: int = None
    dev_path: str = "/path/to/dev"
    size: int = None
    make: str = "Make"
    model: str = "Model"
    serial: str = "Serial"
    health: str = "Unknown"
    cta_id: int = None
    wipe_status: str = "Unknown"
    cert_path: str = None

    def reset(self):
        # Function to reset values to defaults set above
        for name, field in self.__dataclass_fields__.items():
            # Skip resetting positiona and bay info as this won't change
            # after initialization
            if name not in {"position", "bay_port_number"}:
                if field.default != MISSING:
                    setattr(self, name, field.default)
                else:
                    setattr(self, name, field.default_factory())



class remoteFiles():
    def __init__(self):
        self.host = "theta"
        self.port = 22
        self.transport = paramiko.Transport((self.host, self.port))
        self.password = "ThreeInOne!"
        self.username = "netboot-log"
        self.transport.connect(username = self.username, password = self.password)
        self.sftp = paramiko.SFTPClient.from_transport(self.transport)
        self.sftp.chdir("./shredos/")

    def upload(self, file):
        self.sftp.put(file, file)

    def list_files(self):
        self.files = self.sftp.listdir()
        return self.files

    def get_file(self, file):
        self.sftp.get(file)

    def close(self):
        self.sftp.close()
        self.transport.close()
    


class HealthWorker(QObject):
    finished = pyqtSignal()
    status = pyqtSignal(str)

    def __init__(self, path):
        super(HealthWorker, self).__init__()
        self.path = path

    @pyqtSlot()
    def health_run(self):
        run_test = subprocess.run(['sudo',
                                   'smartctl',
                                   '-t',
                                   'short',
                                   self.path],
                                  text=True,
                                  capture_output=True)

        # Captive mode doesn't seem to be actually captive
        sleep(130)


        skdump_test_info = subprocess.run(['sudo', 'skdump', self.path],
                                          text=True,
                                          capture_output=True)

        # self_test_search = skdump_test_info.stdout

        self_test_search = re.search('Overall Status: ([A-Za-z0-9]*_*[A-Za-z0-9]*)',
                                     skdump_test_info.stdout)

        if self_test_search:
            test_outcome = self_test_search.group(1)
        else:
            test_outcome = self.path+" ERROR"

        self.status.emit(test_outcome)

        self.finished.emit()


class DiskWipeWorker(QObject):
    finished = pyqtSignal()
    status = pyqtSignal(str)

    def __init__(self, path, cta_id):
        super(DiskWipeWorker, self).__init__()
        self.path = path
        self.cta_id = cta_id

    @pyqtSlot()
    def wipe_run(self):
        datestamp = datetime.now().strftime('%Y-%m-%d')
        timestamp = datetime.now().strftime('%H%M%S')
        logfile = "nwipe_log_"+datestamp+"--"+str(self.cta_id)+"--BULK_"+timestamp+".txt"

        nwipe_run = subprocess.run(['sudo',
                                    'nwipe',
                                    '--exclude=/dev/nvme0n1',
                                    '--autonuke',
                                    '--method=zero',
                                    '--verify=last',
                                    '--nowait',
                                    '--nogui',
                                    '--logfile='+logfile,
                                    self.path],
                                    text=True,
                                    capture_output=True)

        grab_last_line = subprocess.run(['tail', '-1', logfile],
                                        text=True,
                                        capture_output=True)

        last_line = grab_last_line.stdout

        if "Nwipe successfully completed." in last_line:
            test_outcome = "Wiped"
        elif "Nwipe was aborted by the user" in last_line:
            # Shouldn't ever be an issue
            test_outcome = "Aborted"
        elif "Storage devices not found." in last_line:
            # Shouldn't ever be an issue
            test_outcome = "Device not found"
        elif "Devices not found." in last_line:
            # Shouldn't ever be an issue
            test_outcome = "Device not found"
        elif "Nwipe exited with errors" in last_line:
            test_outcome = "FAILED"
        else:
            test_outcome = "FAILED"     

        self.t = remoteFiles()
        self.t.upload(logfile)
        self.t.close()

        self.status.emit(test_outcome)

        self.finished.emit()



class DiskWidgetGroup(QWidget):
    def __init__(self, dev_path, cta_id, make, model, size, health, wipe_status,
                 serial, position):
        QWidget.__init__(self)

        self.setObjectName(position)

        self.dev_path = dev_path
        self.cta_id = cta_id
        self.position = position
        self.make = QLabel(make)
        self.model = QLabel(model)
        self.size = QLabel(size)
        self.health = QLabel(health)
        self.wipe_status = QLabel(wipe_status)
        self.serial = QLabel(serial)

        self.check_health_button = QPushButton("Check")
        self.check_health_button.clicked.connect(self.health_check)

        self.view_wipelog_button = QPushButton("View log")
        self.view_wipelog_button.clicked.connect(self.open_wipelog)
        # Disable to start with, only enable once wipe has started
        self.view_wipelog_button.setEnabled(False)

        self.start_wipe_button = QPushButton("Wipe")
        self.start_wipe_button.clicked.connect(self.start_wipe)

        self.cta_id_input = QLineEdit(self.cta_id)
        self.cta_id_input.returnPressed.connect(self.start_wipe_button.click)

        layout = QGridLayout()
        self.setLayout(layout)
        groupbox = QGroupBox(self.position)
        inner = QGridLayout()

        layout.addWidget(groupbox)

        inner.addWidget(QLabel("Make:"), 0, 0,)
        inner.addWidget(self.make, 0, 1, 1, 2)
        inner.addWidget(QLabel("Model:"), 1, 0)
        inner.addWidget(self.model, 1, 1)
        inner.addWidget(QLabel("Size:"), 2, 0)
        inner.addWidget(self.size, 2, 1)
        inner.addWidget(QLabel("Serial:"), 3, 0)
        inner.addWidget(self.serial, 3, 1)
        inner.addWidget(QLabel("Health:"), 4, 0)
        inner.addWidget(self.health, 4, 1)
        inner.addWidget(self.check_health_button, 4, 2)
        inner.addWidget(QLabel("Wipe status:"), 5, 0)
        inner.addWidget(self.wipe_status, 5, 1)
        inner.addWidget(self.view_wipelog_button, 5, 2)
        inner.addWidget(QLabel("CTA ID:"), 6, 0)
        inner.addWidget(self.cta_id_input, 6, 1)
        inner.addWidget(self.start_wipe_button, 6, 2)
        groupbox.setLayout(inner)

    def health_check(self):
        # Disable button to avoid multiple requests
        self.check_health_button.setEnabled(False)

        # exit is dev_path is Null 
        if self.dev_path is None:
            return

        # Update UI to indicate something is happening
        self.health.setText("Testing")
        self.health.setStyleSheet("background-color: yellow;\
                                  border: 1px solid black")
        self.repaint()


        self.obj = HealthWorker(path=self.dev_path)
        self.thread = QThread()
        self.obj.status.connect(self.updateHealthStatus)
        self.obj.moveToThread(self.thread)
        self.obj.finished.connect(self.thread.quit)
        self.thread.started.connect(self.obj.health_run)
        self.thread.start()

    def updateHealthStatus(self, status):
        if status == "GOOD":
            self.health.setText("Healthy")
            self.health.setStyleSheet("background-color: lightgreen;\
                                            border: 1px solid black")
        elif status == "FAILED":
            self.health.setText("Unhealthy")
            self.health.setStyleSheet("background-color: red;\
                                            border: 1px solid black")
        elif status == "BAD_SECTOR":
            self.health.setText("Unhealthy (bad sector)")
            self.health.setStyleSheet("background-color: orange;\
                                            border: 1px solid black")
        else:
            self.health.setText(status)
            self.health.setStyleSheet("background-color: yellow;\
                                            border: 1px solid black")

    def open_wipelog(self):
        for file in os.listdir('.'):
            if fnmatch.fnmatch(file, "TEST-nwipe_log_"+str(self.cta_id)+"*"):
                logfile = open(file, 'r').read()


        log = QMessageBox()
        log.setIcon(QMessageBox.Information)
        log.setStandardButtons(QMessageBox.Close)
        log.setWindowTitle(str(self.dev_path)+" wipe log")
        log.setText("Here is the log file:")
        log.setInformativeText(logfile)
        log.exec_()




    def start_wipe(self):
        # Disable button to avoid multiple requests
        self.start_wipe_button.setEnabled(False)
        # Enable wipelog button
        self.view_wipelog_button.setEnabled(True)

        # exit is dev_path is Null 
        if self.dev_path is None:
            return

        inputNumber = self.cta_id_input.text()
        if inputNumber.isdigit():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setWindowTitle("CTA ID")
            msg.setText("You've entered "+str(inputNumber)+" as the ID.")
            msg.setInformativeText("Do you want to proceed and wipe this drive under this ID?")
            return_value = msg.exec_()

            if isinstance(return_value, int) and return_value != 65536:
                self.cta_id = inputNumber
                self.wipe_start = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.wipe_status.setText(self.wipe_start+": Wiping started... ")
                self.wipe_status.setStyleSheet("background-color: yellow;\
                                                border: 1px solid black")
                self.update()

                # Spawn nwipe in DiskWipeWorker
                self.obj = DiskWipeWorker(path=self.dev_path, cta_id=self.cta_id)
                self.thread = QThread()
                self.obj.status.connect(self.updateWipeStatus)
                self.obj.moveToThread(self.thread)
                self.obj.finished.connect(self.thread.quit)
                self.thread.started.connect(self.obj.wipe_run)
                self.thread.start()

            else:
                self.start_wipe_button.setEnabled(True)
                self.view_wipelog_button.setEnabled(False)
        else:
            self.start_wipe_button.setEnabled(True)
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setText(inputNumber+"is not a valid CTA ID")
            msg.setWindowTitle("CTA ID Warning")
            msg.exec_()

    def updateWipeStatus(self, status):
        if status == "Wiped":
            self.wipe_status.setText("Wiped")
            self.wipe_status.setStyleSheet("background-color: lightgreen;\
                                            border: 1px solid black")
        elif status == "FAILED":
            self.wipe_status.setText("FAILED")
            self.wipe_status.setStyleSheet("background-color: red;\
                                            border: 1px solid black")
        else:
            self.wipe_status.setText(status)
            self.wipe_status.setStyleSheet("background-color: yellow;\
                                            border: 1px solid black")


def get_disk_info(disk_object):
    # Function to poll hardware and update given object properties
    time = str(datetime.now())
    disk_object.serial = time

    bay_number = disk_object.bay_port_number
    disk_object.dev_path = get_disk_path(bay_number)
    disk_object.make = get_disk_make(bay_number)
    disk_object.model = get_disk_model(bay_number)
    disk_object.size = get_disk_size(bay_number)

    disk_object.serial = get_disk_serial(disk_object.dev_path)


def get_disk_path(bay_number):
    # Take position, parse lsscsi output and return path
    lsscsi_info = subprocess.run(['lsscsi', '-b'],
                                 text=True,
                                 capture_output=True)
    search = re.search('\['+str(bay_number)+':.+?\\n',
                       lsscsi_info.stdout)
    if search is not None:
        line = search.group(0)
        path = re.search('/dev/[a-z]{3}', line).group(0)
    else:
        path = None
    return path


def get_disk_make(bay_number):
    # Take position, parse lsscsi output and return model name
    lsscsi_info = subprocess.run(['lsscsi', '-c'],
                                 capture_output=True,
                                 text=True,
                                 )
    search= re.search('scsi'+str(bay_number)+'.+?\\n.+?\\n',
                      lsscsi_info.stdout)
    if search is not None:
        line = search.group(0)
        make = re.search('(?<=Vendor: )(.+?)(?=Model:)', line).group(0).rstrip()
    else:
        make = None
    return make


def get_disk_model(bay_number):
    # Take position, parse lsscsi output and return model name
    lsscsi_info = subprocess.run(['lsscsi', '-c'],
                                 capture_output=True,
                                 text=True,
                                 )
    search = re.search('scsi'+str(bay_number)+'.+?\\n.+?\\n',
                     lsscsi_info.stdout)
    if search is not None:
        line = search.group(0)
        model = re.search('(?<=Model: )(.+?)(?=Rev:)', line).group(0).rstrip()
    else:
        model = None
    return model


def get_disk_size(bay_number):
    # Take position, parse lsscsi output and return human readable size
    lsscsi_info = subprocess.run(['lsscsi', '-bs'],
                                 capture_output=True,
                                 text=True,
                                 )
    search = re.search('\['+str(bay_number)+':.+?\s+\/dev\/[a-z]{3}\s+(.+?)\\n',
                       lsscsi_info.stdout)
    if search is not None:
        # group 1 as the group 0 is the matching group and 1 is the capturing group
        size = search.group(1)
    else:
        size = None
    return size


def get_disk_serial(dev_path):
    if dev_path is None:
        serial = None
    else:
        # Take dev_path, parse skdump output and return serial
        skdump_info = subprocess.run(['sudo', 'skdump', dev_path],
                                     text=True,
                                     capture_output=True)
        # group 1 as the group 0 is the matching group and 1 is the capturing group
        serial_search = re.search('Serial:\s\[(.+)\]\\n', skdump_info.stdout)
        if serial_search:
            serial = serial_search.group(1)
        else:
            serial = "Unknown"
    return serial


# def disk_refresh(w):


# Bay ATA port numbers, as determined via lsscsi
# -----------
# |  8 | 12 |
# -----------
# |  9 | 13 |
# -----------
# | 11 | 10 |
# -----------

top_left = Disk("Top Left", 8)
top_right = Disk("Top Right", 12)
mid_left = Disk("Middle left", 9)
mid_right = Disk("Middle Right", 13)
bottom_left = Disk("Bottom Left", 11)
bottom_right = Disk("Bottom Right", 10)

disk_list = [top_left, top_right,
             mid_left, mid_right,
             bottom_left, bottom_right]


app = QApplication([])
window = QWidget()

# Sort out header with info
header = QHBoxLayout()
header_text = QLabel("Welcome to CTAZeta")
# header_text.setAlignment(Qt.AlignCenter)
header.addWidget(header_text)

# Sort out body
main = QGridLayout()
main.addLayout(header, 0, 0, 1, 2, Qt.AlignCenter)

# Initiate disk stuff
# test = Disk("Top Left", 0)
# disk_list = [test]

for disk in disk_list:
    get_disk_info(disk)
    dev_path = disk.dev_path
    make = disk.make
    model = disk.model
    size = disk.size
    health = disk.health
    wipe_status = disk.wipe_status
    serial = disk.serial
    cta_id = disk.cta_id
    position = disk.position
    widget_group = DiskWidgetGroup(dev_path, cta_id, make, model, size, health,
                                   wipe_status, serial, position)
    main.addWidget(widget_group)

row_count = main.rowCount()

footer = QHBoxLayout()
footer_text = QLabel("Footer refresh")
footer.addWidget(footer_text)
main.addLayout(footer, row_count+1, 0, 1, 2, Qt.AlignCenter)

window.setLayout(main)
window.show()
app.exec()

import sys
import tkinter as tk

from queue import Queue
from threading import Thread
import requests
import re

_EDSM_URL = 'https://www.edsm.net/api-system-v1/bodies'
_EDSM_TIMEOUT = 20

# For holding module globals
this = sys.modules[__name__]

# Track information about the scanned state of the current system
this.system = None
this.bodies = []
this.tomap = []
this.count = 0
this.total = 0

# UI element
this.lbl_status = None
this.lbl_bodies = None

# The PlanetClass and Terraformed states we're interested in mapping
this.terraform = ['Terraformable', 'Terraforming', 'Terraformed']

# ASync EDSM system data query
this.thead = None
this.queue = Queue()
this.session = requests.Session()
this.edsm_data = []
this.edsm_error = False

def plugin_start3(plugin_dir):
    """
    Load the plugin.
    :param plugin_dir: directory that contains the main .py file
    """
    this.thread = Thread(target=worker, name='Mapping worker')
    this.thread.daemon = True
    this.thread.start()
    return "SystemScan"


def plugin_start(plugin_dir):
    """
    Legacy (python 2.7) method for loading the plugin.
    :param plugin_dir: directory that contains the main .py file
    """
    return plugin_start3(plugin_dir)


def plugin_stop():
    this.queue.put(None)
    this.thread.join()
    this.thread = None


def plugin_app(parent):
    """
    Create mainwindow content and return it.
    :param parent: the parent frame for this entry.
    :returns: a tk Widget
    """
    this.lbl_status = tk.Label(parent)
    this.lbl_bodies = tk.Label(parent, justify=tk.LEFT, anchor=tk.W, wraplength=200)
    update_ui()
    return this.lbl_status, this.lbl_bodies


def journal_entry(cmdr, is_beta, system, station, entry, state):
    """
    Receive a journal entry.
    :param cmdr: The Cmdr name, or None if not yet known
    :param is_beta: whether the player is in a Beta universe.
    :param system: The current system, or None if not yet known
    :param station: The current station, or None if not docked or not yet known
    :param entry: The journal entry as a dictionary
    :param state: A dictionary containing info about the Cmdr, current ship and cargo
    """
    update = False
    if entry['event'] == 'StartUp':
        handle_startup(entry)
    elif entry['event'] in ['FSDJump', 'CarrierJump']:
        update = handle_system_jump(entry)
    elif entry['event'] == 'FSSDiscoveryScan':
        update = handle_honk(entry)
    elif entry['event'] == 'FSSAllBodiesFound':
        update = handle_all_bodies_found(entry)
    elif entry['event'] == 'Scan':
        update = handle_scan(entry)
    if update:
        update_ui()


def handle_startup(entry):
    """
    Process the EDMC generated 'StartUp' event.
    :param entry: The journal entry as a dictionary
    """
    reset_data()
    this.system = entry['StarSystem']
    this.queue.put(this.system)


def handle_system_jump(entry):
    """
    Process the 'FSDJump' / 'CarrierJump' journal event.
    :param entry: The journal entry as a dictionary
    :returns: a boolean to indicate if the UI needs updating
    """
    handle_startup(entry)
    return True


def handle_honk(entry):
    """
    Process the 'FSSDiscoveryScan' journal event.
    :param entry: The journal entry as a dictionary
    :returns: a boolean to indicate if the UI needs updating
    """
    this.system = entry['SystemName']
    this.total = entry['BodyCount']
    if entry['Progress'] == 1.0:
        this.count = this.total
    elif this.count == 0:
        this.count = int(this.total * entry['Progress'])
    return True


def handle_scan(entry):
    """
    Process the 'Scan' journal event.
    :param entry: The journal entry as a dictionary
    :returns: a boolean to indicate if the UI needs updating
    """
    if entry['ScanType'] == 'NavBeaconDetail':
        return False

    body = entry['BodyName']
    if 'PlanetClass' in entry and body not in this.bodies:
        this.bodies.append(body)
        this.count += 1

        body_name = truncate_body(body, this.system)
        if entry['PlanetClass'] == 'Earthlike body':
            body_name += 'ᴱᴸᵂ'
        elif entry['PlanetClass'] == 'Water world':
            body_name += 'ᵂᵂ'
        elif entry['PlanetClass'] == 'Ammonia world':
            body_name += 'ᴬᵂ'
        elif entry['TerraformState'] in this.terraform:
            body_name += 'ᵀ'
        else:
            return True

        if body_name not in this.tomap:
            this.tomap.append(body_name)
            this.tomap.sort(key=natural_key)
        return True
    if 'StarType' in entry and body not in this.bodies:
        this.bodies.append(body)
        this.count += 1
        return True
    return False


def handle_all_bodies_found(entry):
    """
    Process the 'AllBodiesFound' journal event.
    :param entry: The journal entry as a dictionary
    :returns: a boolean to indicate if the UI needs updating
    """
    this.count = this.total = entry['Count']
    return True


def update_ui():
    """
    Update the UI elements with the system scan progress and the interesting
    body names.
    """
    if this.count == this.total and len(this.tomap) < len(this.edsm_data):
        this.tomap = this.edsm_data

    this.lbl_status['text'] = ' {} / {}'.format(this.count, this.total)
    if this.total == 0:
        this.lbl_bodies['fg'] = 'black'
        this.lbl_bodies['bg'] = 'red'
        this.lbl_bodies['text'] = 'Discovery Scan'
        return
    if this.count < this.total:
        this.lbl_bodies['fg'] = 'black'
        this.lbl_bodies['bg'] = 'orange'
        this.lbl_bodies['text'] = 'Full Spectrum Scan'
        return

    this.lbl_bodies['fg'] = this.lbl_status['fg']
    this.lbl_bodies['bg'] = this.lbl_status['bg']

    if len(this.tomap) > 0:
        this.lbl_bodies['text'] = '  '.join(this.tomap)
    elif this.edsm_error:
        this.lbl_bodies['text'] = '? error'
    else:
        this.lbl_bodies['text'] = '-'


def reset_data():
    """
    Clear all the counters and system body lists.
    """
    this.system = None
    this.total = 0
    this.count = 0
    this.bodies = []
    this.tomap = []
    this.edsm_data = []


def truncate_body(body, system):
    """
    This function tries to truncate long body names.
    This is done by removing the system name from the start of the body name.
    :param body: name of the body
    :param system: name of the system
    :returns: the truncated body name
    """
    if body.startswith(system):
        sys_length = len(system) + 1
        return body[sys_length:].replace(' ', '\u2009')
    return body


def natural_key(string_):
    """
    Helper function for natural sort order.

    See https://blog.codinghorror.com/sorting-for-humans-natural-sort-order/
    """
    return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string_)]


def worker():
    """
    EDSM-Query worker.

    Processess `this.queue` until the queued item is None.
    """
    while True:
        systemName = this.queue.get()
        if systemName == None:
            return
        if len(this.edsm_data) > 0:
            continue

        data = { 'systemName': systemName }
        r = this.session.post(_EDSM_URL, data=data, timeout=_EDSM_TIMEOUT)
        reply = r.json()

        this.edsm_error = (len(reply) == 0)
        if this.edsm_error:
            continue

        this.edsm_data = []
        for body in reply['bodies']:
            if body['type'] != 'Planet':
                continue

            body_name = truncate_body(body['name'], this.system)
            if body['subType'] == 'Earth-like world':
                body_name += 'ᴱᴸᵂ'
            elif body['subType'] == 'Water world':
                body_name += 'ᵂᵂ'
            elif body['subType'] == 'Ammonia world':
                body_name += 'ᴬᵂ'
            elif body['terraformingState'] not in [None, 'Not terraformable']:
                body_name += 'ᵀ'
            else:
                continue

            if body_name not in this.edsm_data:
                this.edsm_data.append(body_name)

        this.edsm_data.sort(key=natural_key)

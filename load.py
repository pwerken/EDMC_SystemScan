import sys
import edmc_data

from systemscan import SystemScan

this = sys.modules[__name__]
this.s = None

def plugin_start3(plugin_dir):
    this.s = SystemScan()
    return this.s.load()

def plugin_stop():
    return this.s.unload()

def plugin_app(parent):
    return this.s.create_ui(parent)

def dashboard_entry(cmdr, is_beta, entry):
    this.s.show_ui(entry['Flags'] & edmc_data.FlagsInMainShip)

def journal_entry(cmdr, is_beta, system, station, entry, state):
    update = False
    if entry['event'] == 'StartUp':
        this.s.handle_startup(entry['StarSystem'])
    elif entry['event'] == 'StartJump' and entry['JumpType'] == 'Hyperspace':
        update = this.s.handle_jump_start(entry['StarSystem'])
    elif entry['event'] in ['Location', 'FSDJump', 'CarrierJump']:
        update = this.s.handle_jump_complete(entry['StarSystem'])
    elif entry['event'] == 'FSSDiscoveryScan':
        update = this.s.handle_honk(entry['SystemName'],
                                    entry['BodyCount'],
                                    entry['Progress'])
    elif entry['event'] == 'FSSAllBodiesFound':
        update = this.s.handle_all_bodies_found(entry['Count'])
    elif entry['event'] == 'Scan':
        update = this.s.handle_scan(entry)
    if update:
        this.s.update_ui()

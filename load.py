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
    journalfunc_name= f'journal_{entry["event"]}'
    this.s.logger.info(journalfunc_name)
    if not hasattr(this.s, journalfunc_name):
        return

    journalfunc = getattr(this.s, journalfunc_name)
    if not callable(journalfunc):
        return
    if journalfunc(entry):
        this.s.update_ui()

import sys
import edmc_data

from systemscan import SystemScan

this = sys.modules[__name__]
this.s = None
this.journal_funcs = {}

def plugin_start3(plugin_dir):
    this.s = SystemScan()
    for fname in dir(this.s):
        func = getattr(this.s, fname, None)
        if fname.startswith('journal_') and callable(func):
            this.journal_funcs[fname[8:]] = func
    return this.s.load()

def plugin_stop():
    return this.s.unload()

def plugin_app(parent):
    return this.s.create_ui(parent)

def dashboard_entry(cmdr, is_beta, entry):
    this.s.show_ui(entry['Flags'] & edmc_data.FlagsInMainShip)

def journal_entry(cmdr, is_beta, system, station, entry, state):
    func = this.journal_funcs.get(entry["event"])
    if func and func(entry):
        this.s.update_ui()

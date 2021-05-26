from systemscan import SystemScan

s = SystemScan()


def plugin_start3(plugin_dir):
    return s.load()


def plugin_stop():
    return s.unload()


def plugin_app(parent):
    return s.create_ui(parent)


def journal_entry(cmdr, is_beta, system, station, entry, state):
    return s.on_journal_entry(entry)

from systemscan import SystemScan

s = SystemScan()

def plugin_start3(plugin_dir):
    return s.load()

def plugin_stop():
    return s.unload()

def plugin_app(parent):
    return s.create_ui(parent)

def journal_entry(cmdr, is_beta, system, station, entry, state):
    update = False
    if entry['event'] == 'StartUp':
        s.handle_startup(entry['StarSystem'])
    elif entry['event'] in ['FSDJump', 'CarrierJump']:
        update = s.handle_system_jump(entry['StarSystem'])
    elif entry['event'] == 'FSSDiscoveryScan':
        update = s.handle_honk(entry['SystemName'],
                               entry['BodyCount'],
                               entry['Progress'])
    elif entry['event'] == 'FSSAllBodiesFound':
        update = s.handle_all_bodies_found(entry['Count'])
    elif entry['event'] == 'Scan':
        update = s.handle_scan(entry)
    if update:
        s.update_ui()

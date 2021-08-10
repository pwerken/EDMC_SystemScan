import requests
import re
import tkinter as tk

from queue import Queue
from threading import Thread


class SystemScan:

    TERRAFORM = ['Terraformable', 'Terraforming', 'Terraformed']

    def __init__(self):
        self.reset_data()
        self.thead = None
        self.queue = Queue()
        self.edsm_error = False

    def load(self):
        self.thread = Thread(target=self.worker, name="SystemScan worker")
        self.thread.daemon = True
        self.thread.start()
        return 'SystemScan'

    def unload(self):
        self.queue.put(None)
        self.thread.join()
        self.thread = None

    def create_ui(self, parent):
        self.lbl_status = tk.Label(parent)
        self.lbl_bodies = tk.Label(parent)
        self.lbl_bodies['justify'] = tk.LEFT
        self.lbl_bodies['anchor'] = tk.W
        self.lbl_bodies['wraplength'] = 200
        self.update_ui()

        self.lbl_status.bind_all('<<SystemScanUpdate>>', self.worker_update)
        return self.lbl_status, self.lbl_bodies

    def update_ui(self):
        if not self.lbl_status or not self.lbl_bodies:
            return

        if self.count == self.total and len(self.tomap) < len(self.edsm_data):
            self.tomap = self.edsm_data

        self.lbl_status['text'] = f'{self.count} / {self.total}'
        if self.total == 0:
            self.lbl_bodies['fg'] = 'black'
            self.lbl_bodies['bg'] = 'red'
            self.lbl_bodies['text'] = 'Discovery Scan'
            return

        if self.count < self.total:
            self.lbl_bodies['fg'] = 'black'
            self.lbl_bodies['bg'] = 'orange'
            self.lbl_bodies['text'] = 'Full Spectrum Scan'
            return

        self.lbl_bodies['fg'] = self.lbl_status['fg']
        self.lbl_bodies['bg'] = self.lbl_status['bg']

        if len(self.tomap) > 0:
            self.lbl_bodies['text'] = '  '.join(self.tomap)
        elif self.edsm_error:
            self.lbl_bodies['text'] = '? error'
        else:
            self.lbl_bodies['text'] = '-'

    def on_journal_entry(self, entry):
        update = False
        if entry['event'] == 'StartUp':
            self.handle_startup(entry)
        elif entry['event'] in ['FSDJump', 'CarrierJump']:
            update = self.handle_system_jump(entry)
        elif entry['event'] == 'FSSDiscoveryScan':
            update = self.handle_honk(entry)
        elif entry['event'] == 'FSSAllBodiesFound':
            update = self.handle_all_bodies_found(entry)
        elif entry['event'] == 'SAAScanComplete':
            update = self.handle_surface_scan(entry)
        elif entry['event'] == 'Scan':
            update = self.handle_scan(entry)
        if update:
            self.update_ui()

    def handle_startup(self, entry):
        self.reset_data()
        self.system = entry['StarSystem']
        self.queue.put(self.system)
        return True

    def handle_system_jump(self, entry):
        return self.handle_startup(entry)

    def handle_honk(self, entry):
        self.system = entry['SystemName']
        self.total = entry['BodyCount']
        if entry['Progress'] == 1.0:
            self.count = self.total
        elif self.count == 0:
            self.count = int(self.total * entry['Progress'])

        return True

    def handle_surface_scan(self, entry):
        body = entry['BodyName']
        if body in self.bodies:
            self.bodies.remove(body)
        self.count -= 1
        return False

    def handle_scan(self, entry):
        if entry['ScanType'] == 'NavBeaconDetail':
            return False

        body = entry['BodyName']
        if 'PlanetClass' in entry and body not in self.bodies:
            self.bodies.append(body)
            self.count += 1

            body_name = self.truncate_body(body, self.system)
            if entry['PlanetClass'] == 'Earthlike body':
                body_name += 'ᴱᴸᵂ'
            elif entry['PlanetClass'] == 'Water world':
                body_name += 'ᵂᵂ'
            elif entry['PlanetClass'] == 'Ammonia world':
                body_name += 'ᴬᵂ'
            elif entry['TerraformState'] in self.TERRAFORM:
                body_name += 'ᵀ'
            else:
                return True

            if body_name not in self.tomap:
                self.tomap.append(body_name)
                self.tomap.sort(key=self.natural_key)
            return True

        if 'StarType' in entry and body not in self.bodies:
            self.bodies.append(body)
            self.count += 1
            return True

        return False

    def handle_all_bodies_found(self, entry):
        self.count = self.total = entry['Count']
        return True

    def reset_data(self):
        self.system = None
        self.total = 0
        self.count = 0
        self.bodies = []
        self.tomap = []
        self.edsm_data = []

    def worker_update(self, event):
        self.update_ui()

    def worker(self):
        EDSM_URL = 'https://www.edsm.net/api-system-v1/bodies'
        EDSM_TIMEOUT = 20
        EDSM_TERRAFORM = [None, 'Not terraformable']

        session = requests.Session()

        while True:
            systemName = self.queue.get()
            if systemName is None:
                return

            if len(self.edsm_data) > 0:
                continue

            data = {'systemName': systemName}
            r = session.post(EDSM_URL, data=data, timeout=EDSM_TIMEOUT)
            reply = r.json()

            self.edsm_error = (len(reply) == 0)
            if self.edsm_error:
                continue

            self.edsm_data = []
            for body in reply['bodies']:
                if body['type'] != 'Planet':
                    continue

                body_name = self.truncate_body(body['name'], self.system)
                if body['subType'] == 'Earth-like world':
                    body_name += 'ᴱᴸᵂ'
                elif body['subType'] == 'Water world':
                    body_name += 'ᵂᵂ'
                elif body['subType'] == 'Ammonia world':
                    body_name += 'ᴬᵂ'
                elif body['terraformingState'] not in EDSM_TERRAFORM:
                    body_name += 'ᵀ'
                else:
                    continue

                if body_name not in self.edsm_data:
                    self.edsm_data.append(body_name)

            self.edsm_data.sort(key=self.natural_key)
            self.lbl_status.event_generate('<<SystemScanUpdate>>', when='tail')

    @staticmethod
    def truncate_body(body, system):
        """
        Remove the system name from the start of the body name.
        :param body: name of the body
        :param system: name of the system
        :returns: the truncated body name
        """
        if body.startswith(system+' '):
            sys_length = len(system) + 1
            return body[sys_length:].replace(' ', '\u2009')
        return body

    @staticmethod
    def natural_key(key):
        """
        Helper function for natural sort order.

        https://blog.codinghorror.com/sorting-for-humans-natural-sort-order/
        """
        return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', key)]

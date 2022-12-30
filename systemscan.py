import logging
import requests
import re
import tkinter as tk

from queue import Queue
from threading import Thread
from config import appname

class SystemScan:

    TERRAFORM = ['Terraformable', 'Terraforming', 'Terraformed']

    def __init__(self):
        self.reset_data()
        self.thead = None
        self.queue = Queue()
        self.edsm_error = False
        self.show = True
        self.logger = logging.getLogger(f'{appname}.SystemScan')

    def load(self):
        self.thread = Thread(target=self.worker, name="SystemScan worker")
        self.thread.daemon = True
        self.thread.start()
        self.logger.info('started')
        return 'SystemScan'

    def unload(self):
        self.queue.put(None)
        self.thread.join()
        self.thread = None

    def create_ui(self, parent):
        self.show = True
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

    def show_ui(self, show):
        if self.show == show:
            return
        self.show = show
        if self.show:
            self.lbl_status.grid()
            self.lbl_bodies.grid()
        else:
            self.lbl_status.grid_remove()
            self.lbl_bodies.grid_remove()

    def handle_startup(self, system):
        self.reset_data()
        self.system = system
        self.queue.put(self.system)
        return True

    def handle_system_jump(self, system):
        self.logger.info(f'arrived in: {system}')
        return self.handle_startup(system)

    def handle_honk(self, system, bodyCount, progress):
        self.system = system
        self.total = bodyCount
        if progress == 1.0:
            self.count = self.total
        elif self.count == 0:
            self.count = int(self.total * progress)

        return True

    def handle_all_bodies_found(self, total):
        self.count = self.total = total
        return True

    def handle_scan(self, entry):
        if entry['ScanType'] == 'NavBeaconDetail':
            return False

        body = entry['BodyName']
        if 'PlanetClass' in entry and body not in self.bodies:
            self.bodies.append(body)
            if self.count < self.total:
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

            self.logger.debug(f'EDSM? {systemName}')
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
                    self.logger.debug(f'EDSM: {systemName} {body_name}')
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

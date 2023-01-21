import logging
import requests
import re
import tkinter as tk

from queue import Queue
from threading import Thread
from config import appname, user_agent

class SystemScan:

    def __init__(self):
        self.reset_data()
        self.session = requests.Session()
        self.session.headers['User-Agent'] = user_agent
        self.thread = None
        self.queue = Queue()
        self.external_error = False
        self.external_data = []
        self.external_id64 = None
        self.show = True
        self.logger = logging.getLogger(f'{appname}.SystemScan')

    def load(self):
        return 'SystemScan'

    def unload(self):
        self.queue.put(None)
        if self.thread:
            self.thread.join()

    def create_ui(self, parent):
        self.show = True
        self.lbl_bodies = tk.Label(parent, name='systemscan')
        self.lbl_bodies['justify'] = tk.LEFT
        self.lbl_bodies['anchor'] = tk.W
        self.lbl_bodies['wraplength'] = 200
        self.color_ref = parent.nametowidget('.edmarketconnector.cmdr_label')
        self.update_ui()

        self.lbl_bodies.bind_all('<<SystemScanUpdate>>', self.worker_update)
        return self.lbl_bodies

    def update_ui(self):
        if not self.lbl_bodies:
            return

        if self.count == self.total \
        and self.id64 == self.external_id64 \
        and len(self.tomap) < len(self.external_data):
            self.tomap = self.external_data

        if self.total == 0:
            text = f'Discovery Scan ({self.count} / {self.total})'
            self.lbl_bodies['fg'] = 'black'
            self.lbl_bodies['bg'] = 'red'
            self.lbl_bodies['anchor'] = tk.CENTER
            self.lbl_bodies['text'] = text
            return

        if self.count < self.total:
            text = f'Full Spectrum Scan ({self.count} / {self.total})'
            self.lbl_bodies['fg'] = 'black'
            self.lbl_bodies['bg'] = 'orange'
            self.lbl_bodies['anchor'] = tk.CENTER
            self.lbl_bodies['text'] = text
            return

        bodies = ' '.join(self.tomap) or '-'
        self.lbl_bodies['anchor'] = tk.W
        self.lbl_bodies['fg'] = self.color_ref['fg']
        self.lbl_bodies['bg'] = self.color_ref['bg']
        self.lbl_bodies['text'] = f'{self.total} : {bodies}'

    def show_ui(self, show):
        if self.show == show:
            return
        self.show = show
        if self.show:
            self.lbl_bodies.grid()
        else:
            self.lbl_bodies.grid_remove()

    def journal_StartUp(self, entry):
        self.reset_data()
        self.id64 = entry['SystemAddress']
        self.system = entry['StarSystem']

        self.to_worker(self.id64)
        return True

    def journal_StartJump(self, entry):
        if entry['JumpType'] == 'Hyperspace':
            self.to_worker(entry['SystemAddress'])
        return False

    def journal_Location(self, entry):
        return self.journal_StartUp(entry)

    def journal_FSDJump(self, entry):
        return self.journal_StartUp(entry)

    def journal_CarrierJump(self, entry):
        return self.journal_StartUp(entry)

    def journal_FSSDiscoveryScan(self, entry):
        self.id64 = entry['SystemAddress']
        self.system = entry['SystemName']
        self.total = entry['BodyCount']
        progress = entry['Progress']
        if progress == 1.0:
            self.count = self.total
        elif self.count == 0:
            self.count = int(self.total * progress)
        return True

    def journal_FSSAllBodiesFound(self, entry):
        self.count = self.total = entry['Count']
        return True

    def journal_Scan(self, entry):
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
        self.id64 = None
        self.system = None
        self.total = 0
        self.count = 0
        self.bodies = []
        self.tomap = []

    def worker_update(self, event):
        self.update_ui()

    def to_worker(self, id64):
        self.queue.put(id64)
        if self.thread and not self.thread.is_alive():
            self.logger.warning('restarting thread')
            self.thread.join()
            self.thread = None
        if self.thread is None:
            self.thread = Thread(target=self.worker, name="SystemScan worker")
            self.thread.daemon = True
            self.thread.start()

    def worker(self):
        URL = 'https://www.spansh.co.uk/api/system'
        TIMEOUT = 20

        while True:
            id64 = self.queue.get()
            if id64 is None:
                self.logger.info('stopped')
                return
            if id64 == self.external_id64:
                continue

            self.external_id64 = id64
            self.external_error = False
            self.external_data = []

            reply = self.session.get(f'{URL}/{id64}', timeout=TIMEOUT).json()
            if len(reply) == 0 or 'error' in reply:
                self.logger.debug(f'SPANSH {repr(reply)}')
                self.external_error = True
                continue

            system_name = reply['record']['name']
            for body in reply['record']['bodies']:
                if body['type'] != 'Planet':
                    continue

                body_name = self.truncate_body(body['name'], system_name)
                if body['subtype'] == 'Earth-like world':
                    body_name += 'ᴱᴸᵂ'
                elif body['subtype'] == 'Water world':
                    body_name += 'ᵂᵂ'
                elif body['subtype'] == 'Ammonia world':
                    body_name += 'ᴬᵂ'
                else:
                    continue

                if body_name not in self.external_data:
                    self.external_data.append(body_name)

            self.external_data.sort(key=self.natural_key)
            self.lbl_bodies.event_generate('<<SystemScanUpdate>>', when='tail')
        self.logger.error('exit?')

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

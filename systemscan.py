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

        if self.count == self.total \
        and self.id64 == self.external_id64 \
        and len(self.tomap) < len(self.external_data):
            self.tomap = self.external_data

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
        elif self.external_error:
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

    def handle_startup(self, entry):
        self.reset_data()
        self.id64 = entry['SystemAddress']
        self.system = entry['StarSystem']

        self.to_worker(self.id64)
        return True

    def handle_jump_start(self, entry):
        self.to_worker(entry['SystemAddress'])
        return False

    def handle_jump_complete(self, entry):
        return self.handle_startup(entry)

    def handle_honk(self, entry):
        self.id64 = entry['SystemAddress']
        self.system = entry['SystemName']
        self.total = entry['BodyCount']
        progress = entry['Progress']
        if progress == 1.0:
            self.count = self.total
        elif self.count == 0:
            self.count = int(self.total * progress)
        return True

    def handle_all_bodies_found(self, entry):
        self.count = self.total = entry['Count']
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
            r = self.session.get(f'{URL}/{id64}', timeout=TIMEOUT)
            reply = r.json()

            if len(reply) == 0 or 'error' in reply:
                self.logger.debug(f'SPANSH {repr(reply)}')
                self.external_error = True
                continue

            self.external_data = []
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
            self.lbl_status.event_generate('<<SystemScanUpdate>>', when='tail')
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

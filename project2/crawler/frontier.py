import os
import time
from threading import RLock
from utils import get_logger, get_urlhash, normalize
from scraper import is_valid


class Frontier(object):
    def __init__(self, config, restart):
        self.logger = get_logger("FRONTIER")
        self.config = config

        self.lock = RLock()
        self.to_be_downloaded = []
        self.save = {}

        # Politeness tracking (domain → last access time)
        self.last_access_time = {}

        if restart:
            for url in self.config.seed_urls:
                self.add_url(url)
        else:
            if os.path.exists(self.config.save_file):
                self._parse_save_file()
            if not self.save:
                for url in self.config.seed_urls:
                    self.add_url(url)

    def _parse_save_file(self):
        for url, completed in self.save.values():
            if not completed and is_valid(url):
                self.to_be_downloaded.append(url)

    def get_tbd_url(self):
        with self.lock:
            if not self.to_be_downloaded:
                return None
            url = self.to_be_downloaded.pop()
            
            # CRITICAL: Do politeness check INSIDE the lock
            domain = self._get_domain(url)
            last_time = self.last_access_time.get(domain, 0)
            current_time = time.time()
            wait_time = max(0.5 - (current_time - last_time), 0)
            
            # Update BEFORE releasing lock
            self.last_access_time[domain] = current_time + wait_time
        
        # Sleep OUTSIDE the lock
        if wait_time > 0:
            time.sleep(wait_time)
        
        return url

    def add_url(self, url):
        url = normalize(url)
        urlhash = get_urlhash(url)

        with self.lock:
            if urlhash not in self.save:
                self.save[urlhash] = (url, False)
                self.to_be_downloaded.append(url)

    def mark_url_complete(self, url):
        urlhash = get_urlhash(url)
        with self.lock:
            self.save[urlhash] = (url, True)

    def _get_domain(self, url):
        return url.split("/")[2].lower()

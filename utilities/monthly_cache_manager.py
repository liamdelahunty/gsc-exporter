import time
import os

class MonthlyCacheManager:
    def __init__(self, cache_directory):
        self.cache_directory = cache_directory
        # Create the cache directory if it doesn't exist
        if not os.path.exists(cache_directory):
            os.makedirs(cache_directory)

    def get_cache_file_path(self):
        # Create a unique cache file name based on the current month
        current_time = time.strftime('%Y-%m', time.gmtime())
        return os.path.join(self.cache_directory, f'cache_{current_time}.txt')

    def read_cache(self):
        cache_file_path = self.get_cache_file_path()
        try:
            with open(cache_file_path, 'r') as cache_file:
                return cache_file.read()
        except FileNotFoundError:
            return None

    def write_cache(self, data):
        cache_file_path = self.get_cache_file_path()
        with open(cache_file_path, 'w') as cache_file:
            cache_file.write(data)

    def clear_cache(self):
        # Clear cache files older than the current month
        current_time = time.strftime('%Y-%m', time.gmtime())
        for filename in os.listdir(self.cache_directory):
            if filename.startswith('cache_') and filename[6:12] != current_time:
                os.remove(os.path.join(self.cache_directory, filename))

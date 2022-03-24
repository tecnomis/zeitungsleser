import threading
import requests
import pyzipper
import datetime
import hashlib
import pygame
import time
import math
import json
import yaml
import os


class RescaleWorker:

    instances = []

    def __init__(self, viewer):

        self.viewer = viewer

        self.allowed = True
        self.mutex = threading.Lock()

        self.th = threading.Thread(target=self.worker)
        self.th.start()

        self.instances.insert(0, self)


    def worker(self):

        rescale_width = self.viewer.high_res_image_width * self.viewer.scale * self.viewer.dpi_ratio
        rescale_height = self.viewer.high_res_image_height * self.viewer.scale * self.viewer.dpi_ratio

        rescaled_img = pygame.transform.smoothscale(self.viewer.high_res_image, (rescale_width, rescale_height))

        self.mutex.acquire()
        if self.allowed:
            self.viewer.rescaled_image = rescaled_img
            self.viewer.rescale_mode = 0
        self.mutex.release()

        self.instances.remove(self)


    def cancel(self):

        self.mutex.acquire()
        self.allowed = False
        self.mutex.release()


    def abort():

        if RescaleWorker.instances:
            RescaleWorker.instances[0].cancel()



class ImageViewer:

    run_in_window = True
    window_size = (800, 1280)

    min_scale = 1.0
    max_scale = 10.0

    rescale_wait_sec = 0.5
    overlay_fade_exp = 0.01

    font_file_path = 'data/Ubuntu-B.ttf'
    font_notify_size = 30

    black = pygame.color.Color('#000000')
    white = pygame.color.Color('#FFFFFF')
    transparency = (0, 0, 0, 0)

    notify_downloading = 'Die Zeitung wird aus dem Briefkasten geholt...'
    notify_progress = 'Fortschritt: {}%'
    notify_first_page = 'Erste Seite erreicht'
    notify_last_page = 'Letzte Seite erreicht'
    notify_last_date = 'Heutiges Datum erreicht'
    notify_bookmark = 'Lesezeichen gesetzt'
    notify_unbookmark = 'Lesezeichen entfernt'
    notify_no_content = 'Für den {} existiert keine Ausgabe'
    notify_loading = 'Seite wird geladen...'

    wallpaper_path = 'data/wallpaper.png'

    icon_downloading_path = 'data/doggo_news.png'
    icon_downloading_vig_path = 'data/doggo_news_vignette.png'

    icon_loading_path = 'data/doggo_fetch.png'
    icon_loading_vig_path = 'data/doggo_fetch_vignette.png'

    icon_empty_path = 'data/doggo_idle.png'
    icon_empty_vig_path = 'data/doggo_idle_vignette.png'

    insert_vignette_path = 'data/insert_vignette.png'
    info_vignette_path = 'data/info_vignette.png'

    FIRSTPAGE =  0
    LASTPAGE =   1
    LASTDATE =   2
    BOOKMARK =   3
    UNBOOKMARK = 4


    def __init__(self):

        pygame.init()

        if self.run_in_window:
            self.screen = pygame.display.set_mode(self.window_size)
        else:
            self.screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)

        pygame.mouse.set_visible(False)

        self.window_width, self.window_height = self.screen.get_size()
        self.clock = pygame.time.Clock()

        self.font = pygame.freetype.Font(self.font_file_path, size=self.font_notify_size)

        self.wallpaper = pygame.image.load(self.wallpaper_path)

        self.icon_downloading = pygame.image.load(self.icon_downloading_path)
        self.icon_downloading_vig = pygame.image.load(self.icon_downloading_vig_path)

        self.icon_loading = pygame.image.load(self.icon_loading_path)
        self.icon_loading_vig = pygame.image.load(self.icon_loading_vig_path)

        self.icon_empty = pygame.image.load(self.icon_empty_path)
        self.icon_empty_vig = pygame.image.load(self.icon_empty_vig_path)

        self.insert_vignette = pygame.image.load(self.insert_vignette_path)
        self.info_vignette = pygame.image.load(self.info_vignette_path)

        self.info_text = ('', '')
        self.info_time = 0.0

        self.insert_text = ''
        self.insert_time = 0.0

        self.view_x = 0.0
        self.view_y = 0.0

        self.scale = 1.0

        self.rescale_mode = 1
        self.rescale_time = 0

        self.low_res_image = None
        self.high_res_image = None

        self.low_res_image_width = 0
        self.low_res_image_height = 0

        self.high_res_image_width = 0
        self.high_res_image_width = 0

        self.rescaled_image = None
        self.draw_images = True


    def display_info(self, info, time):

        self.info_text = info
        self.info_time = time

        self.clock.tick()


    def clear_info(self):

        self.info_time = 0.0


    def display_insert(self, insert, time):

        if insert == self.FIRSTPAGE:
            self.insert_text = self.notify_first_page

        if insert == self.LASTPAGE:
            self.insert_text = self.notify_last_page

        if insert == self.LASTDATE:
            self.insert_text = self.notify_last_date

        if insert == self.BOOKMARK:
            self.insert_text = self.notify_bookmark

        if insert == self.UNBOOKMARK:
            self.insert_text = self.notify_unbookmark

        self.insert_time = time
        self.clock.tick()


    def display_no_content(self, date):

        date_str = date.strftime('%d.%m.%Y')
        no_content_str = self.notify_no_content.format(date_str)

        self.insert_text = no_content_str
        self.insert_time = math.inf


    def clear_insert(self):

        self.insert_time = 0.0


    def loading_screen(self, invert):

        if invert:
            self.screen.fill(self.black)

        screen_center = (0.5 * self.window_width, 0.5 * self.window_height)
        screen_below = (0.5 * self.window_width, 0.5 * self.window_height + 250)

        text_color = self.white if invert else self.black
        notify_surf, notify_rect = self.font.render(text=self.notify_loading, fgcolor=text_color)

        notify_rect_center = notify_surf.get_rect(center=screen_center)
        icon_rect_center = self.icon_loading.get_rect(center=screen_below)

        if not invert:
            bar_rect_center = self.insert_vignette.get_rect(center=screen_center)

            self.screen.blit(self.insert_vignette, bar_rect_center)
            self.screen.blit(self.icon_loading_vig, icon_rect_center)

        self.screen.blit(notify_surf, notify_rect_center)
        self.screen.blit(self.icon_loading, icon_rect_center)

        pygame.display.flip()

        for event in pygame.event.get():
            pass


    def download_screen(self, perc):

        self.screen.fill(self.black)

        screen_center = (0.5 * self.window_width, 0.5 * self.window_height)
        screen_newline = (0.5 * self.window_width, 0.5 * self.window_height + 40)
        screen_below = (0.5 * self.window_width, 0.5 * self.window_height + 250)

        notify_surf, notify_rect = self.font.render(text=self.notify_downloading, fgcolor=self.white)
        notify_rect_center = notify_surf.get_rect(center=screen_center)
        self.screen.blit(notify_surf, notify_rect_center)

        percentage_str = self.notify_progress.format(perc)
        perc_surf, perc_rect = self.font.render(percentage_str, fgcolor=self.white)
        perc_rect_center = perc_surf.get_rect(center=screen_newline)
        self.screen.blit(perc_surf, perc_rect_center)

        icon_rect_center = self.icon_downloading.get_rect(center=screen_below)
        self.screen.blit(self.icon_downloading, icon_rect_center)

        pygame.display.flip()

        for event in pygame.event.get():
            pass


    def set_draw_images(self, draw):

        if draw != self.draw_images:
            print(f'Image drawing {"enabled" if draw else "disabled"}')

        self.draw_images = draw


    def get_draw_images(self):

        return self.draw_images


    def set_images(self, low_res, high_res, dpi_ratio):

        self.low_res_image = pygame.image.load(low_res)
        self.high_res_image = pygame.image.load(high_res)

        self.low_res_image_width = self.low_res_image.get_width()
        self.low_res_image_height = self.low_res_image.get_height()

        self.high_res_image_width = self.high_res_image.get_width()
        self.high_res_image_height = self.high_res_image.get_height()

        self.dpi_ratio = dpi_ratio

        self.initial_view()

        self.rescale_mode = 1
        self.rescale_time = 0


    def initial_view(self):

        if self.low_res_image_width * self.scale > self.window_width:
            self.view_x = 0.5 * self.window_width / self.scale
        else:
            self.view_x = 0.5 * self.low_res_image_width

        if self.low_res_image_height * self.scale > self.window_height:
            self.view_y = 0.5 * self.window_height / self.scale
        else:
            self.view_y = 0.5 * self.low_res_image_height


    def set_center(self, px, py):

        self.view_x = px
        self.view_y = py

        if px < 0:
            self.view_x = 0.0
        if py < 0:
            self.view_y = 0.0

        if px > self.low_res_image_width:
            self.view_x = self.low_res_image_width
        if py > self.low_res_image_height:
            self.view_y = self.low_res_image_height


    def move_center(self, dx, dy):

        new_view_x = self.view_x + dx
        new_view_y = self.view_y + dy

        self.set_center(new_view_x, new_view_y)


    def set_scale(self, scale):

        if scale < self.min_scale:
            scale = self.min_scale
        if scale > self.max_scale:
            scale = self.max_scale

        if scale != self.scale:
            self.scale = scale

            RescaleWorker.abort()

            self.rescale_mode = 1
            self.rescale_time = time.time()


    def change_scale(self, factor):

        self.set_scale(self.scale * factor)


    def draw(self):

        self.clock.tick()
        dt = self.clock.get_time()

        # Draw background
        self.screen.blit(self.wallpaper, dest=(0, 0))

        if self.draw_images:

            # Rescale image

            if self.rescale_mode == 1:

                current_time = time.time()
                if (current_time - self.rescale_time) > self.rescale_wait_sec:

                    self.rescale_mode = 2
                    RescaleWorker(self)

            # Draw newspaper

            if self.rescale_mode == 0:

                location_top = 0.5 * self.window_width - self.view_x * self.scale
                location_left = 0.5 * self.window_height - self.view_y * self.scale

                self.screen.blit(self.rescaled_image, dest=(location_top, location_left))

            else:

                viewport_width = self.window_width / self.scale
                viewport_height = self.window_height / self.scale

                viewport_top = self.view_x - 0.5 * viewport_width
                viewport_left = self.view_y - 0.5 * viewport_height

                viewport_surf = pygame.Surface((viewport_width, viewport_height), flags=pygame.SRCALPHA)
                viewport = (viewport_top, viewport_left, viewport_width, viewport_height)

                viewport_surf.fill(self.transparency)
                viewport_surf.blit(self.low_res_image, dest=(0, 0), area=viewport)

                scaled_surf = pygame.transform.scale(viewport_surf, (self.window_width, self.window_height))
                self.screen.blit(scaled_surf, (0, 0))


        # Draw info text

        if self.info_time > 0:
            self.info_time = (self.info_time - dt) if self.info_time > dt else 0.0

            screen_top_left = (15, 12)
            screen_top_right = (self.window_width - 15, 12)
            overlay_alpha = 255 * (1.0 - math.exp(-self.overlay_fade_exp * self.info_time))

            info_text_left, info_text_right = self.info_text
            bar_rect_top_left = self.info_vignette.get_rect(topleft=(0, 0))

            text_left_surf, text_left_rect = self.font.render(text=info_text_left, fgcolor=self.black)
            text_left_rect_top_left = text_left_surf.get_rect(topleft=screen_top_left)

            text_right_surf, text_right_rect = self.font.render(text=info_text_right, fgcolor=self.black)
            text_right_rect_top_right = text_right_surf.get_rect(topright=screen_top_right)

            transparent_surf = pygame.Surface((self.window_width, self.window_height), flags=pygame.SRCALPHA)
            transparent_surf.fill(self.transparency)

            transparent_surf.blit(self.info_vignette, bar_rect_top_left)
            transparent_surf.blit(text_left_surf, text_left_rect_top_left)
            transparent_surf.blit(text_right_surf, text_right_rect_top_right)

            transparent_surf.set_alpha(overlay_alpha)
            self.screen.blit(transparent_surf, (0, 0))

        # Draw text insert

        if self.insert_time > 0:
            self.insert_time = (self.insert_time - dt) if self.insert_time > dt else 0.0

            screen_center = (0.5 * self.window_width, 0.5 * self.window_height)
            overlay_alpha = 255 * (1.0 - math.exp(-self.overlay_fade_exp * self.insert_time))

            bar_rect_center = self.insert_vignette.get_rect(center=screen_center)

            text_surf, text_rect = self.font.render(text=self.insert_text, fgcolor=self.black)
            text_rect_center = text_surf.get_rect(center=screen_center)

            transparent_surf = pygame.Surface((self.window_width, self.window_height), flags=pygame.SRCALPHA)
            transparent_surf.fill(self.transparency)

            transparent_surf.blit(self.insert_vignette, bar_rect_center)
            transparent_surf.blit(text_surf, text_rect_center)

            transparent_surf.set_alpha(overlay_alpha)
            self.screen.blit(transparent_surf, (0, 0))

        # Done drawing
        pygame.display.flip()

        # Handle events
        for event in pygame.event.get():
            pass

        return dt



class ArchiveManager:

    history_days = 1

    database_path = 'database.json'
    credentials_path = 'credentials.yaml'

    downloads_folder = 'downloads'
    renderings_folder = 'renderings'

    entry_info_template = '{} vom {}'
    page_info_template = 'Seite {}'


    def __init__(self):

        self.online_archives = []
        self.missing_archives = []

        self.current_source = ''
        self.current_date = datetime.date.today()

        if not os.path.isfile(self.database_path):
            empty_database = {'bookmark': {}, 'newspaper': {}}

            with open(self.database_path, 'w') as database_file:
                json.dump(empty_database, database_file)

        with open(self.database_path, 'r') as database_file:
            self.database = json.load(database_file)

        self.bookmark_db = self.database['bookmark']
        self.newspaper_db = self.database['newspaper']

        with open(self.credentials_path, 'r') as credentials_file:
            self.credentials = yaml.safe_load(credentials_file)

        self.server_host = self.credentials['archive_host']
        self.archive_key_start = self.credentials['archive_key']

        if not os.path.isdir(self.downloads_folder):
            os.mkdir(self.downloads_folder)

        if not os.path.isdir(self.renderings_folder):
            os.mkdir(self.renderings_folder)


    def save_database(self):

        with open(self.database_path, 'w') as database_file:

            print('Writing to database')
            json.dump(self.database, database_file)


    def current_entry(self):

        date_format = self.current_date.strftime('%d-%m-%Y')
        current_entry = f'{self.current_source}_{date_format}'

        return current_entry


    def parse_name(self, name):

        source, date_str = name.rstrip('.zip').split('_')
        date = datetime.datetime.strptime(date_str, '%d-%m-%Y')

        return source, date.date()


    def update_available(self):

        server_index = requests.get(self.server_host).json()
        self.online_archives = server_index['archives']

        self.missing_archives = []
        for archive_name in self.online_archives:

            archive_name_base = archive_name.rstrip('.zip')

            if not archive_name_base in self.newspaper_db:
                self.missing_archives.append(archive_name)


    def download_archive(self, name):

        local_archive_path = os.path.join(self.downloads_folder, name)
        archive_name_base = name.rstrip('.zip')

        perc_reported = 0

        with requests.get(self.server_host + name, stream=True) as archive_response:
            print('Downloading...')

            content_size = int(archive_response.headers.get('content-length', 0))
            content_done = 0

            with open(local_archive_path, 'wb') as local_file:
                for data_chunk in archive_response.iter_content(chunk_size=1024):

                    data_size = local_file.write(data_chunk)

                    content_done += data_size
                    percentage = math.floor(50 * content_done / content_size)

                    if percentage > perc_reported:
                        perc_reported = percentage
                        yield percentage

        unpack_folder_path = os.path.join(self.renderings_folder, archive_name_base)
        os.makedirs(unpack_folder_path)

        archive_key = (self.archive_key_start + archive_name_base).encode()
        archive_pw = hashlib.md5(archive_key).hexdigest().encode()

        with pyzipper.AESZipFile(local_archive_path, 'r') as archive_file:
            print('Extracting...')

            archive_file.setpassword(archive_pw)

            all_member_paths = archive_file.infolist()
            member_count = len(all_member_paths)

            for i, member_path in enumerate(all_member_paths):

                archive_file.extract(member_path, unpack_folder_path)
                percentage = 50 + math.floor(50 * (i+1) / member_count)

                if percentage > perc_reported:
                    perc_reported = percentage
                    yield percentage

        os.remove(local_archive_path)

        info_file_path = os.path.join(unpack_folder_path, 'info.json')
        with open(info_file_path, 'r') as info_file:
            newspaper_entry = json.load(info_file)

        newspaper_entry['page'] = 1
        self.newspaper_db[archive_name_base] = newspaper_entry
        self.save_database()


    def download_recent(self):

        today = datetime.date.today()

        for_download = []
        for missing_archive in self.missing_archives:

            source, archive_date = self.parse_name(missing_archive)
            archive_age = today - archive_date

            if not archive_age.days > self.history_days:
                for_download.append(missing_archive)

        downloads_count = len(for_download)

        for i, archive_name in enumerate(for_download):
            print(f'Downloading {i+1}/{downloads_count}: {archive_name}')

            download_gen = self.download_archive(archive_name)

            for percentage in download_gen:

                total_percentage = int(percentage / downloads_count + i * 100 / downloads_count)
                yield total_percentage


    def delete_older(self, days):

        today = datetime.date.today()
        # TODO


    def create_bookmark(self):

        current_entry = self.current_entry()
        print(f'Bookmark created: {current_entry}')

        self.bookmark_db[self.current_source] = current_entry
        self.save_database()


    def remove_bookmark(self):

        print(f'Bookmark removed')
        self.bookmark_db.pop(self.current_source, None)
        self.save_database()


    def bookmark_set(self):

        bookmark_exists = self.current_source in self.bookmark_db
        return bookmark_exists


    def set_source(self, source):

        self.current_source = source
        print(f'Now using {source} as source')

        if source in self.bookmark_db:

            current_entry = self.bookmark_db[self.current_source]
            print(f'Bookmark entry {current_entry} applied')

            src, self.current_date = self.parse_name(current_entry)

        else:
            self.newest_entry()


    def newest_entry(self):

        newest_date = datetime.date.min
        newest_entry = ''

        for entry in self.newspaper_db:

            entry_source, entry_data = self.parse_name(entry)
            if entry_source == self.current_source and entry_data > newest_date:

                newest_date = entry_data
                newest_entry = entry

        if not newest_entry:
            newest_date = datetime.date.today()

        self.current_date = newest_date

        date_format = newest_date.strftime('%d-%m-%Y')
        print(f'Applying {date_format} as newest date')


    def next_entry(self):

        self.current_date += datetime.timedelta(days=1)

        if self.current_date > datetime.date.today():
            self.current_date = datetime.date.today()

            print(f'Date of today reached')
            return False

        date_format = self.current_date.strftime('%d-%m-%Y')
        print(f'Switched to date {date_format}')

        return True


    def prev_entry(self):

        self.current_date -= datetime.timedelta(days=1)

        date_format = self.current_date.strftime('%d-%m-%Y')
        print(f'Switched to date {date_format}')


    def first_page(self):

        current_entry = self.current_entry()
        if not current_entry in self.newspaper_db:

            print(f'Entry {current_entry} not in database')
            return False

        entry_info = self.newspaper_db[current_entry]

        entry_info['page'] = 1
        self.save_database()

        print(f'Turned to first page')


    def last_page(self):

        current_entry = self.current_entry()
        if not current_entry in self.newspaper_db:

            print(f'Entry {current_entry} not in database')
            return False

        entry_info = self.newspaper_db[current_entry]
        page_count = entry_info['page_count']

        entry_info['page'] = page_count
        self.save_database()

        print(f'Turned to last page')


    def next_page(self):

        current_entry = self.current_entry()
        if not current_entry in self.newspaper_db:

            print(f'Entry {current_entry} not in database')
            return False

        entry_info = self.newspaper_db[current_entry]
        page_count = entry_info['page_count']
        page_nr = entry_info['page']

        page_nr += 1
        if page_nr > page_count:

            page_nr = page_count

            print(f'Last page reached')
            return False

        entry_info['page'] = page_nr
        self.save_database()

        print(f'Turned to page {page_nr}')
        return True


    def prev_page(self):

        current_entry = self.current_entry()
        if not current_entry in self.newspaper_db:

            print(f'Entry {current_entry} not in database')
            return False

        entry_info = self.newspaper_db[current_entry]
        page_nr = entry_info['page']

        page_nr -= 1
        if page_nr == 0:

            page_nr = 1

            print(f'First page reached')
            return False

        entry_info['page'] = page_nr
        self.save_database()

        print(f'Turned to page {page_nr}')
        return True


    def get_opened_page(self):

        if self.current_source == 'haz':
            source_str = 'HAZ'

        date_str = self.current_date.strftime('%d.%m.%Y')

        current_entry = self.current_entry()
        if current_entry in self.newspaper_db:

            entry_info = self.newspaper_db[current_entry]
            page_nr = entry_info['page']

        else:
            page_nr = 1

        entry_info = self.entry_info_template.format(source_str, date_str)
        page_info = self.page_info_template.format(page_nr)

        return entry_info, page_info


    def get_current_date(self):

        return self.current_date


    def entry_exists(self):

        current_entry = self.current_entry()
        entry_exists = current_entry in self.newspaper_db

        return entry_exists


    def get_opened_images(self):

        current_entry = self.current_entry()
        entry_info = self.newspaper_db[current_entry]

        page_nr = entry_info['page']
        page_nr_filled = str(page_nr).zfill(2)

        image_path_low = os.path.join(self.renderings_folder, current_entry, f'{page_nr_filled}_lo.png')
        image_path_high = os.path.join(self.renderings_folder, current_entry, f'{page_nr_filled}_hi.png')

        images_exist = os.path.isfile(image_path_low) and os.path.isfile(image_path_high)
        assert images_exist, f'Images {image_path_low} and/or {image_path_high} for {current_entry} not found'

        return image_path_low, image_path_high


    def get_dpi_ratio(self):

        current_entry = self.current_entry()
        entry_info = self.newspaper_db[current_entry]

        low_res_dpi = entry_info['dpi_low']
        high_res_dpi = entry_info['dpi_high']

        dpi_ratio = low_res_dpi / high_res_dpi
        return dpi_ratio



class InputManager:

    allow_sensors = False
    allow_keyboard = True

    keyboard_dpdt = 0.1
    keyboard_dsdt = 0.001

    long_press_thres = 1000

    NEXTENTRY =     0
    PREVENTRY =     1
    NEXTENTRYLONG = 2
    PREVENTRYLONG = 3
    NEXTPAGE =      4
    PREVPAGE =      5
    NEXTPAGELONG =  6
    PREVPAGELONG =  7


    def __init__(self, viewer):

        self.viewer = viewer
        self.events = []

        self.next_entry_pressed = 0.0
        self.prev_entry_pressed = 0.0

        self.next_page_pressed = 0.0
        self.prev_page_pressed = 0.0

        self.next_entry_locked = False
        self.prev_entry_locked = False

        self.next_page_locked = False
        self.prev_page_locked = False

        if self.allow_sensors:

            import spidev
            import mraa

            # TODO
            #self.gpio_shutdown = mraa.Gpio(???)

            self.pwm_led_green = mraa.Pwm(11)
            self.pwm_led_green.enable(True)

            self.gpio_source_0 = mraa.Gpio(36)
            self.gpio_source_0.dir(mraa.DIR_IN)

            self.gpio_source_1 = mraa.Gpio(38)
            self.gpio_source_1.dir(mraa.DIR_IN)

            self.gpio_source_2 = mraa.Gpio(40)
            self.gpio_source_2.dir(mraa.DIR_IN)


    def get_source(self):

        if self.allow_sensors:
            source_selected = (gpio_source_0.read(), gpio_source_1.read(), gpio_source_2.read())

        else:
            source_selected = (1, 0, 0)

        if source_selected[0]:
            return 'haz'
        if source_selected[1]:
            return None
        if source_selected[2]:
            return None

        return None


    def sensors_state(self, dt):

        if not self.allow_sensors:
            return


    def keyboard_state(self, dt):

        if not self.allow_keyboard:
            return

        keys = pygame.key.get_pressed()

        if keys[pygame.K_m]:
            self.next_entry_pressed += dt
            if self.next_entry_pressed > self.long_press_thres and not self.next_entry_locked:
                self.events.append(self.NEXTENTRYLONG)
                self.next_entry_locked = True
        else:
            if self.next_entry_pressed > 0 and not self.next_entry_locked:
                self.events.append(self.NEXTENTRY)
            self.next_entry_pressed = 0.0
            self.next_entry_locked = False

        if keys[pygame.K_n]:
            self.prev_entry_pressed += dt
            if self.prev_entry_pressed > self.long_press_thres and not self.prev_entry_locked:
                self.events.append(self.PREVENTRYLONG)
                self.prev_entry_locked = True
        else:
            if self.prev_entry_pressed > 0 and not self.prev_entry_locked:
                self.events.append(self.PREVENTRY)
            self.prev_entry_pressed = 0.0
            self.prev_entry_locked = False

        if keys[pygame.K_x]:
            self.next_page_pressed += dt
            if self.next_page_pressed > self.long_press_thres and not self.next_page_locked:
                self.events.append(self.NEXTPAGELONG)
                self.next_page_locked = True
        else:
            if self.next_page_pressed > 0 and not self.next_page_locked:
                self.events.append(self.NEXTPAGE)
            self.next_page_pressed = 0.0
            self.next_page_locked = False

        if keys[pygame.K_y]:
            self.prev_page_pressed += dt
            if self.prev_page_pressed > self.long_press_thres and not self.prev_page_locked:
                self.events.append(self.PREVPAGELONG)
                self.prev_page_locked = True
        else:
            if self.prev_page_pressed > 0 and not self.prev_page_locked:
                self.events.append(self.PREVPAGE)
            self.prev_page_pressed = 0.0
            self.prev_page_locked = False


    def sensors_input(self, dt):

        if not self.allow_sensors:
            return


    def keyboard_input(self, dt):

        if not self.allow_keyboard:
            return

        translate_speed = self.keyboard_dpdt * dt
        zoom_factor = 1.0 + self.keyboard_dsdt * dt

        keys = pygame.key.get_pressed()

        if keys[pygame.K_w]:
            self.viewer.move_center(0.0, -translate_speed)

        if keys[pygame.K_s]:
            self.viewer.move_center(0.0, +translate_speed)

        if keys[pygame.K_a]:
            self.viewer.move_center(-translate_speed, 0.0)

        if keys[pygame.K_d]:
            self.viewer.move_center(+translate_speed, 0.0)

        if keys[pygame.K_e]:
            self.viewer.change_scale(zoom_factor)

        if keys[pygame.K_q]:
            self.viewer.change_scale(1.0/zoom_factor)


    def set_green_led(self, level):

        self.pwm_led_green.write(1.0 - level)


    def get_events(self):

        if self.events:
            yield self.events.pop(0)



def handle_content(reload=True, invert=False):

    entry_exists = archive_man.entry_exists()
    draw_images = image_viewer.get_draw_images()

    if entry_exists and not draw_images:
        image_viewer.clear_insert()

    if not entry_exists:
        image_viewer.clear_info()

        current_date = archive_man.get_current_date()
        image_viewer.display_no_content(current_date)

    image_viewer.set_draw_images(entry_exists)

    if entry_exists and reload:
        image_viewer.loading_screen(invert=invert)

        low_res, high_res = archive_man.get_opened_images()
        dpi_ratio = archive_man.get_dpi_ratio()

        image_viewer.set_images(low_res, high_res, dpi_ratio)

        left_info, right_info = archive_man.get_opened_page()
        image_viewer.display_info((left_info, right_info), 5000)


image_viewer = ImageViewer()
archive_man = ArchiveManager()
input_man = InputManager(image_viewer)

archive_man.update_available()
progress_gen = archive_man.download_recent()

for progress_perc in progress_gen:
    image_viewer.download_screen(progress_perc)

current_source = input_man.get_source()
archive_man.set_source(current_source)

handle_content(invert=True)


while True:

    dt = image_viewer.draw()

    input_man.sensors_state(dt)
    input_man.keyboard_state(dt)

    input_man.sensors_input(dt)
    input_man.keyboard_input(dt)

    for event in input_man.get_events():
        good = False

        if event == InputManager.NEXTENTRY:
            print('Event: Next entry')

            good = archive_man.next_entry()
            if not good:
                image_viewer.display_insert(ImageViewer.LASTDATE, 2000)

        if event == InputManager.PREVENTRY:
            print('Event: Previous entry')

            archive_man.prev_entry()
            good = True

        if event == InputManager.NEXTENTRYLONG:
            print('Event: Newest entry')

            archive_man.newest_entry()
            archive_man.remove_bookmark()
            good = True

            if archive_man.bookmark_set():
                image_viewer.display_insert(ImageViewer.UNBOOKMARK, 2000)

        if event == InputManager.PREVENTRYLONG:
            print('Event: Bookmark')

            archive_man.create_bookmark()
            image_viewer.display_insert(ImageViewer.BOOKMARK, 2000)

        if event == InputManager.NEXTPAGE:
            print('Event: Next page')

            good = archive_man.next_page()
            if not good:
                image_viewer.display_insert(ImageViewer.LASTPAGE, 2000)

        if event == InputManager.PREVPAGE:
            print('Event: Previous page')

            good = archive_man.prev_page()
            if not good:
                image_viewer.display_insert(ImageViewer.FIRSTPAGE, 2000)

        if event == InputManager.NEXTPAGELONG:
            print('Event: Last page')

            archive_man.last_page()
            good = True

        if event == InputManager.PREVPAGELONG:
            print('Event: First page')

            archive_man.first_page()
            good = True

        handle_content(reload=good)

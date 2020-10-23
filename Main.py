import os
import re
import math as mth
import tkinter as tk
from tkinter import filedialog, font
from tkscrolledframe import ScrolledFrame
from functools import partial


class Directory:
    def __init__(self, path, name, size):
        self.path = path
        self.name = name
        self.file_type = identify_element(self.path)
        self.byte_size = size
        self.converted_size, self.converted_unit = self.convert_size_unit()
        self.fully_converted_size = str(self.converted_size) + ' ' + self.converted_unit
        self.change_protected_folder_size()

    def convert_size_unit(self, precision=2):
        size_units_symbols = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
        if self.byte_size:
            divider = int(mth.log(self.byte_size, 1024))
        else:
            divider = 0

        return round(self.byte_size / (1024 ** divider), precision), size_units_symbols[divider] + 'B'

    def change_protected_folder_size(self):
        if self.file_type == 'protected folder':
            self.byte_size = - 0.001
            self.fully_converted_size = 'N/A'


class ElementsSizeDictionary:
    def __init__(self, start_path):
        self.start_path = start_path
        self.dictionary = get_dictionary(self.start_path)


def identify_element(path):
    try:
        os.scandir(path)
        return 'folder'
    except PermissionError:
        return 'protected folder'
    except NotADirectoryError:
        return 'file'


def merge_path(current_path, new_element):
    if current_path[-1] == '\\':
        return current_path + new_element
    else:
        return current_path + '\\' + new_element


def get_dictionary(start_path):
    dictionary = {}

    def get_all_elements_sizes_from_partition(path, overall_size=0):
        directories = []
        identify_result = identify_element(path)
        if identify_result == 'folder':
            directories = os.scandir(path)
        elif identify_result == 'file':
            try:
                file_size = os.stat(path).st_size
                overall_size += file_size
                dictionary[path] = dictionary.get(path, 0) + file_size
            except FileNotFoundError:
                pass

        for directory in directories:
            d_name, d_is_folder = directory.name, directory.is_dir()
            if not d_is_folder:
                try:
                    file_size = os.stat(directory).st_size
                    overall_size += file_size
                    dictionary[merge_path(path, directory.name)] = dictionary.get(merge_path(path, directory.name), 0) + file_size
                except FileNotFoundError:
                    pass
            else:
                overall_size += get_all_elements_sizes_from_partition(merge_path(path, directory.name), overall_size=0)

        dictionary[path] = dictionary.get(path, 0) + overall_size
        return overall_size

    get_all_elements_sizes_from_partition(start_path)
    return dictionary


def set_path_previous_location(path):
    if len(path) > 3:
        if path.count('\\') > 1:
            return path[:path.rfind('\\')]
        else:
            return path[:path.rfind('\\') + 1]
    else:
        return None


def fix_path(path):
    path = list(path)
    for match in re.finditer('/', ''.join(path)):
        path[match.start()] = '\\'
    if len(path) > 3 and path[-1] == '\\':
        return ''.join(path[: -1])
    else:
        return ''.join(path)


def window_position_adjuster(window, width_adjuster=0.7, height_adjuster=0.7):
    window.update()
    window.geometry('%dx%d+%d+%d' % (window.winfo_width(), window.winfo_height(), width_adjuster * ((window.winfo_screenwidth() - window.winfo_width()) / 2), height_adjuster * ((window.winfo_screenheight() - window.winfo_height()) / 2)))


def window_on_top_update(window):
    window.attributes('-topmost', True)
    window.update()
    window.attributes('-topmost', False)
    window.focus_force()
    window.update()


def window_alpha(window, alpha):
    window.attributes('-alpha', alpha)
    window.update()


def get_sorted_directories(path, elements_dictionary):
    directories = []

    for directory in list(os.scandir(path)):
        directories.append(Directory(directory.path, directory.name, elements_dictionary.dictionary[directory.path]))

    return sort_directories(directories)


def sort_directories(directories, elements_limit=150):
    directories.sort(key=lambda x: x.byte_size, reverse=True)
    if len(directories) > elements_limit:
        return directories[:elements_limit], elements_limit
    else:
        return directories, None


def shorten_the_path(path, path_max_size=40):
    if len(path) > path_max_size:
        return path[:3] + '(...)' + path[path.rfind('\\'):]
    else:
        return path


def check_path(path):
    return bool(len(path))


def create_waiting_window():
    window = tk.Tk()
    window.title('Calculating...')
    window_alpha(window, 0)
    window.update()

    return window


def run_the_program(path, elements_dictionary=None, window=None):
    if check_path(path):
        calc_window = None
        if elements_dictionary is None:
            calc_window = create_waiting_window()
            elements_dictionary = ElementsSizeDictionary(path[:3])
        elif elements_dictionary.start_path != path[:3]:
            window.destroy()
            window = None
            calc_window = create_waiting_window()
            elements_dictionary = ElementsSizeDictionary(path[:3])

        if calc_window is not None:
            calc_window.destroy()
        gui(path, elements_dictionary, window)


def gui(path, elements_dictionary, window=None):
    def change(dir_):
        return dir_

    if window is not None:
        window.destroy()

    window = tk.Tk()
    window.title('File Size Inspector')

    tk.Label(window, text='File Size Inspector', font=font.Font(family='Helvetica', size=14, weight='bold')).grid(row=0, column=0)
    tk.Label(window, text='').grid(row=1, column=0)

    frame = tk.Frame(window)
    tk.Label(frame, text='Current path: ' + shorten_the_path(path), font=font.Font(family='Helvetica', size=12, weight='normal')).grid(row=0, column=0)
    tk.Label(frame, text='   ').grid(row=0, column=1)
    tk.Button(frame, text='CHANGE', command=lambda: [run_the_program(select_path(), elements_dictionary, window)]).grid(row=0, column=2)
    frame.grid(row=2, column=0)

    tk.Label(window, text='').grid(row=3, column=0)

    sf = ScrolledFrame(window, width=520, height=425)
    sf.grid(row=5, column=0)

    sf.bind_arrow_keys(window)
    sf.bind_scroll_wheel(window)

    inner_frame = sf.display_widget(tk.Frame)
    frame = tk.Frame(inner_frame)

    headers_dict = {'Name': 40, 'Type': 15, 'Size': 10}
    i = 0

    for key in list(headers_dict.keys()):
        l_box = tk.Listbox(frame, bg=window['bg'], justify=tk.CENTER, relief=tk.GROOVE, width=headers_dict[key], height=1, font=font.Font(family='Helvetica', size=10, weight='bold'))
        l_box.insert(0, key)
        l_box.grid(row=0, column=i)
        i += 1

    frame.grid(row=5, column=0, sticky='W')

    sorted_directories, limited_elements_number = get_sorted_directories(path, elements_dictionary)
    if limited_elements_number is not None:
        tk.Label(window, text='Showing ' + str(limited_elements_number) + ' largest elements from this directory.', fg='#e67300', font=font.Font(family='Helvetica', size=10, weight='normal')).grid(row=4, column=0)

    buttons = []
    i = 0
    for directory in sorted_directories:
        frame = tk.Frame(inner_frame)

        content_dictionary = {'Name': directory.name, 'Type': directory.file_type, 'Size': directory.fully_converted_size}
        j = 0
        for key in list(content_dictionary.keys()):
            l_box_name = tk.Listbox(frame, width=headers_dict[key], height=1, font=font.Font(family='Helvetica', size=10, weight='normal'))
            l_box_name.insert(0, content_dictionary[key])
            l_box_name.grid(row=0, column=j)
            j += 1

        if directory.file_type == 'folder':
            button = tk.Button(frame, text='OPEN', command=lambda c=i: [gui(partial(change, sorted_directories[c].path).args[0], elements_dictionary, window)])
            button.grid(row=0, column=i+3)
            buttons.append(button)

        frame.grid(row=i+7, column=0, sticky='W')
        i += 1

    previous_location = set_path_previous_location(path)
    if previous_location is not None:
        tk.Button(window, text='BACK', font=10, command=lambda: [gui(previous_location, elements_dictionary, window)]).grid(row=i+8, column=0)

    window_on_top_update(window)
    window_position_adjuster(window)
    window.mainloop()


def select_path(start=False):
    window = tk.Tk()
    window.withdraw()
    title = "Select the directory"
    if start:
        title = "Select the initial directory"
    initial_path = fix_path(filedialog.askdirectory(title=title))
    window.destroy()

    return initial_path


run_the_program(select_path(start=True))

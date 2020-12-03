import os
import re
import math as mth
import tkinter as tk
from tkinter import filedialog, font
from tkscrolledframe import ScrolledFrame
from functools import partial


class Path:
    def __init__(self, path):
        self.path = self.replace_slashes_with_backslashes_in_path_string(path)

    @staticmethod
    def replace_slashes_with_backslashes_in_path_string(path):
        path = list(path)
        for match in re.finditer('/', ''.join(path)):
            path[match.start()] = '\\'
        if len(path) > 3 and path[-1] == '\\':
            return ''.join(path[: -1])
        else:
            return ''.join(path)

    def get_path_previous_location(self):
        if len(self.path) > 3:
            if self.path.count('\\') > 1:
                return self.path[:self.path.rfind('\\')]
            else:
                return self.path[:self.path.rfind('\\') + 1]
        else:
            return None

    def merge_paths(self, new_element):
        if self.path[-1] == '\\':
            return f'{self.path}{new_element}'
        else:
            return self.path + '\\' + new_element

    def shorten_path_if_necessary(self, path_max_size=40):
        if len(self.path) > path_max_size:
            shorter_path = self.path
            if list(self.path).count('\\') > 1:
                shorter_path = self.path[:3] + '(...)' + self.path[self.path.rfind("\\"):]
            if len(shorter_path) > path_max_size:
                return f'{shorter_path[:path_max_size - 3]}...'
            else:
                return shorter_path

        else:
            return self.path

    def extract_disc_initial_path(self):
        return self.path[:3]


class Window:
    def __init__(self, window, window_title, width_adjuster=0.7, height_adjuster=0.7, alpha=1.0):
        self.window = window
        self.window_title = window_title
        self.window.title(self.window_title)
        self.window.update()

        self.width_adjuster = width_adjuster
        self.height_adjuster = height_adjuster
        self.alpha = alpha

    def adjust_window_position(self):
        self.window.geometry('%dx%d+%d+%d' % (self.window.winfo_width(), self.window.winfo_height(), self.width_adjuster * ((self.window.winfo_screenwidth() - self.window.winfo_width()) / 2), self.height_adjuster * ((self.window.winfo_screenheight() - self.window.winfo_height()) / 2)))
        self.window.update()

    def window_on_top_update(self):
        self.window.attributes('-topmost', True)
        self.window.attributes('-topmost', False)
        self.window.focus_force()
        self.window.update()

    def set_window_alpha(self):
        self.window.attributes('-alpha', self.alpha)
        self.window.update()

    def change_window_title(self, new_title):
        self.window.title(new_title)
        self.window.update()

    def restore_original_window_title(self):
        self.window.title(self.window_title)
        self.window.update()

    def create_new_window(self):
        self.window.destroy()
        self.window = tk.Tk()
        self.window.title(self.window_title)


class PathSelector(Window):
    def __init__(self, first_selection=False):
        super().__init__(tk.Tk(), 'Path Selector')
        self.window.withdraw()
        self.description = self.get_description(first_selection)
        self.initial_path = Path(self.get_initial_path()).path
        self.verify_input()
        self.window.destroy()

    @staticmethod
    def get_description(first_selection):
        if first_selection:
            return "Select the initial directory"
        else:
            return "Select the directory"

    def get_initial_path(self):
        return filedialog.askdirectory(title=self.description)

    def verify_input(self):
        if os.path.islink(self.initial_path):
            self.initial_path = os.path.realpath(self.initial_path)
        try:
            os.scandir(self.initial_path)
        except:
            self.initial_path = None


class ElementIdentificationNames:
    def __init__(self):
        self.folder_identification_name = 'folder'
        self.protected_folder_identification_name = 'protected folder'
        self.file_identification_name = 'file'


class NewElementsDictionaryEntry(ElementIdentificationNames):
    def __init__(self, element_name, element_type, element_byte_size=0):
        super().__init__()
        self.name = element_name
        self.type = element_type
        self.byte_size = element_byte_size
        if self.type != self.protected_folder_identification_name:
            self.size, self.size_unit = self.convert_size_in_bytes(element_byte_size)
        else:
            self.size = 'N/A'
            self.size_unit = ''
        if self.type == self.folder_identification_name:
            self.can_open = True
        else:
            self.can_open = False

    @staticmethod
    def convert_size_in_bytes(size_in_bytes, precision=2):
        size_units_symbols = ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z', 'Y']
        if size_in_bytes:
            times_to_divide = int(mth.log(size_in_bytes, 1024))
        else:
            times_to_divide = 0

        return round(size_in_bytes / (1024 ** times_to_divide), precision), f'{size_units_symbols[times_to_divide]}B'


class ElementsDictionary(ElementIdentificationNames):
    def __init__(self, initial_path):
        super().__init__()
        self.dictionary = {}
        self.get_all_elements_sizes(initial_path)

    def identify_element(self, path):
        try:
            os.scandir(path)
            return self.folder_identification_name
        except PermissionError:
            return self.protected_folder_identification_name
        except NotADirectoryError:
            return self.file_identification_name
        except FileNotFoundError:
            pass

    def get_all_elements_sizes(self, path, name=None, overall_size=0):
        for element in os.scandir(path):
            if element.is_symlink():
                continue
            element_type = self.identify_element(element.path)
            if element_type == self.file_identification_name:
                element_size = os.stat(element.path).st_size

                self.dictionary[element.path] = NewElementsDictionaryEntry(element.name, element_type, element_size)
                overall_size += element_size

            elif element_type == self.folder_identification_name:
                overall_size += self.get_all_elements_sizes(element.path, name=element.name)

            elif element_type == self.protected_folder_identification_name:
                self.dictionary[element.path] = NewElementsDictionaryEntry(element.name, element_type)

        self.dictionary[path] = NewElementsDictionaryEntry(name, self.folder_identification_name, overall_size)

        return overall_size


class SelectEntries:
    def __init__(self, current_path, all_elements_on_disc_dictionary):
        self.current_path = current_path
        self.all_elements_on_disc_dictionary = all_elements_on_disc_dictionary

        self.selected_data = self.select_elements()

    def select_elements(self):
        paths = [path.path for path in os.scandir(self.current_path) if not path.is_symlink()]
        entries = [self.all_elements_on_disc_dictionary[path] for path in paths]

        return dict(zip(paths, entries))


class SortEntries:
    def __init__(self, selected_elements_dictionary):
        self.selected_elements_dictionary = selected_elements_dictionary
        self.sorted_dictionary = self.sort_dictionary()

    def sort_dictionary(self):
        return {key: value for key, value in sorted(self.selected_elements_dictionary.items(), key=lambda item: item[1].byte_size, reverse=True)}


class DataPrepare:
    def __init__(self, current_path):
        self.current_path = current_path
        self.disc_initial_path_from_previous_path = None
        self.all_elements_on_disc_dictionary = {}
        self.selected_elements_dictionary = {}

        self.collect_new_data_if_necessary()
        self.set_sorted_elements_from_current_path()

    def set_new_current_path(self, new_path):
        self.disc_initial_path_from_previous_path = Path(self.current_path).extract_disc_initial_path()
        self.current_path = new_path

    def collect_new_data_if_necessary(self):
        if self.disc_initial_path_from_previous_path is None or Path(self.current_path).extract_disc_initial_path() != self.disc_initial_path_from_previous_path:
            self.all_elements_on_disc_dictionary = ElementsDictionary(Path(self.current_path).extract_disc_initial_path()).dictionary

    def set_sorted_elements_from_current_path(self):
        self.selected_elements_dictionary = SortEntries(SelectEntries(self.current_path, self.all_elements_on_disc_dictionary).selected_data).sorted_dictionary


class FileSizeInspector(Window):
    def __init__(self, current_path):
        super().__init__(tk.Tk(), 'File Size Inspector')
        self.change_window_title('Calculating...')
        self.data_prepare_object = DataPrepare(current_path)
        self.max_number_of_elements_on_screen = 100

        self.fields = ['Name', 'Type', 'Size']
        self.fields_width_dictionary = dict(zip(self.fields, [40, 15, 10]))
        self.restore_original_window_title()
        self.run()

    def change_button_function(self):
        new_path = PathSelector().initial_path
        if new_path is not None:
            self.create_new_window()
            self.change_window_title('Calculating...')
            self.data_prepare_object.set_new_current_path(new_path)
            self.data_prepare_object.collect_new_data_if_necessary()
            self.data_prepare_object.set_sorted_elements_from_current_path()
            self.restore_original_window_title()
            self.run()

    def move_function(self, new_path):
        self.create_new_window()
        self.data_prepare_object.set_new_current_path(new_path)
        self.data_prepare_object.set_sorted_elements_from_current_path()
        self.run()

    def run(self):
        def open_button_path_fun(path):
            return path

        tk.Label(self.window, text='File Size Inspector', font=font.Font(family='Helvetica', size=14, weight='bold')).grid(row=0, column=0)
        tk.Label(self.window, text='').grid(row=1, column=0)

        frame = tk.Frame(self.window)
        tk.Label(frame, text=f'Current path: {Path(self.data_prepare_object.current_path).shorten_path_if_necessary()}', font=font.Font(family='Helvetica', size=12, weight='normal')).grid(row=0, column=0)
        tk.Label(frame, text='   ').grid(row=0, column=1)
        tk.Button(frame, text='CHANGE', command=lambda: [self.change_button_function()]).grid(row=0, column=2)
        frame.grid(row=2, column=0)

        tk.Label(self.window, text='').grid(row=3, column=0)

        sf = ScrolledFrame(self.window, width=520, height=425)
        sf.grid(row=5, column=0)

        sf.bind_arrow_keys(self.window)
        sf.bind_scroll_wheel(self.window)
        sf.focus()

        inner_frame = sf.display_widget(tk.Frame)
        frame = tk.Frame(inner_frame)

        i = 0

        for header_name in list(self.fields_width_dictionary.keys()):
            l_box = tk.Listbox(frame, bg=self.window['bg'], justify=tk.CENTER, relief=tk.GROOVE, width=self.fields_width_dictionary[header_name], height=1, font=font.Font(family='Helvetica', size=10, weight='bold'))
            l_box.insert(0, header_name)
            l_box.grid(row=0, column=i)
            i += 1

        frame.grid(row=5, column=0, sticky='W')

        if len(list(self.data_prepare_object.selected_elements_dictionary.keys())) > self.max_number_of_elements_on_screen:
            tk.Label(self.window, text=f'Showing {self.max_number_of_elements_on_screen} largest elements from this directory.', fg='#e67300', font=font.Font(family='Helvetica', size=10, weight='normal')).grid(row=4, column=0)

        i = 0
        paths = list(self.data_prepare_object.selected_elements_dictionary.keys())
        for entry_path in paths:
            frame = tk.Frame(inner_frame)
            content_dictionary = dict(zip(self.fields, [self.data_prepare_object.selected_elements_dictionary[entry_path].name,
                                                        self.data_prepare_object.selected_elements_dictionary[entry_path].type,
                                                        f'{self.data_prepare_object.selected_elements_dictionary[entry_path].size} {self.data_prepare_object.selected_elements_dictionary[entry_path].size_unit}']))
            j = 0
            for column_name in list(content_dictionary.keys()):
                l_box_name = tk.Listbox(frame, width=self.fields_width_dictionary[column_name], height=1, font=font.Font(family='Helvetica', size=10, weight='normal'))
                l_box_name.insert(0, content_dictionary[column_name])
                l_box_name.grid(row=0, column=j)
                j += 1

            if self.data_prepare_object.selected_elements_dictionary[entry_path].can_open:
                button = tk.Button(frame, text='OPEN', command=lambda c=i: [self.move_function(partial(open_button_path_fun, paths[c]).args[0])])
                button.grid(row=0, column=i+3)

            frame.grid(row=i+7, column=0, sticky='W')
            i += 1

            if i > self.max_number_of_elements_on_screen:
                break

        previous_location = Path(self.data_prepare_object.current_path).get_path_previous_location()
        if previous_location is not None:
            tk.Button(self.window, text='BACK', font=10, command=lambda: [self.move_function(previous_location)]).grid(row=i+8, column=0)

        self.window_on_top_update()
        self.adjust_window_position()
        self.window.mainloop()


if __name__ == '__main__':
    starting_path = PathSelector(first_selection=True).initial_path
    if starting_path is not None:
        FileSizeInspector(starting_path)

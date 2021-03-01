"""
   Originally created by Fernando B.
   Updated and maintained by Fernando B. (fernandobe+git@protonmail.com)

   Copyright 2019 Fernando B.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

from pylogix import PLC
from ping3 import ping
import configparser, argparse
import sys
from pathlib import Path
from progress.bar import Bar
import datetime, time
import re
import shutil
import os
import logging
from logging.handlers import RotatingFileHandler

# variables are read from Settings.ini
main_controller_ip = ''
dp_save_remote_path = ''
dp_save_local_path = ''
paths_on_load = []
paths_on_save = []
tags_list = []
tag_types = ["BOOL", "BIT", "REAL", "DINT", "SINT"]
remote_files = []
local_files = []
file_extension = ''
comm = PLC()
CODE_VERSION = "1.3.0"
log_file = "log.txt"
log_formatter = logging.Formatter('%(asctime)s - %(message)s')
log_handler = RotatingFileHandler(log_file, mode='a', maxBytes=5*1024*1024, 
                                 backupCount=2, encoding=None, delay=0)
log_handler.setFormatter(log_formatter)
log_handler.setLevel(logging.DEBUG)
app_log = logging.getLogger('root')
app_log.setLevel(logging.DEBUG)
app_log.addHandler(log_handler)

now = datetime.datetime.now()
checkErrorLog = False


def get_data_preserve(path, file):
    global tags_list
    del tags_list[:]

    with open(path + "\\" + file + "." + file_extension) as f:
        all_lines = f.readlines()

    # need to check empty lines, and more than one tag in one line here
    all_lines = remove_empty(all_lines)
    all_lines = check_multiple(all_lines, file)

    print("Config file: {}".format(file))
    bar = Bar('Saving', max=len(all_lines))

    for index in range(len(all_lines)):
        process_line_save(all_lines[index] + "\n", index + 1, file)
        bar.next()
    bar.finish()
    print("\n")

    with open(path + "\\" + file + "_save." + file_extension, "w") as dp_save_file:
        dp_save_file.writelines(tags_list)


def load_verify_data_preserve(path, file, verify_only=False):

    with open(path + "\\" + file + "_save." + file_extension) as f:
        all_lines = f.readlines()

    all_lines = remove_empty(all_lines)
    print("Config file: {}".format(file))
    bar = Bar('Loading', max=len(all_lines))
    bar2 = Bar('Verifying', max=len(all_lines))

    # do not load if only doing verification
    if not verify_only:
        for index in range(len(all_lines)):
            process_line_load(all_lines[index], index + 1, file)
            bar.next()
        bar.finish()

    # Verify online data afterwards
    passed = 0
    failed = 0
    for index in range(len(all_lines)):
        tag_verification = process_line_verification(all_lines[index], index + 1, file)
        bar2.next()
        if tag_verification:
            passed += 1
        else:
            failed += 1
    bar2.finish()

    print("\rVerification results: %d+ %d-\n" % (passed, failed))


def read_tag(tag):
    return comm.Read(tag).Value


def remove_empty(lines):
    clean_list = []
    # first remove return line
    clean_list = [line.rstrip('\n') for line in lines]
    # remove empty items
    clean_list = list(filter(None, clean_list))
    return clean_list


def check_multiple(lines, file_name):
    clean_list = []
    # if the tag type is in the same line twice
    # search if there are more than two
    for index in range(len(lines)):
        if lines[index].count("|") > 2:
            app_log.info("Save Info: %s line %s Multiple tags in one line" % (file_name, index+1))
            # process line here, and split into more items
            clean_list.extend(split_tag_lines(lines[index]))
        else:
            clean_list.append(lines[index])

    return clean_list


def split_tag_lines(line):
    how_many_tags = 0
    split_tags = []
    clean_list = []
    # count how many tags for each two || is one tag
    how_many_tags = line.count("|") // 2

    split_tags = re.split(r'(DINT|BOOL|SINT|BIT|REAL)', line)

    # append to list
    for i in range(0, how_many_tags*2, 2):
        clean_list.append(split_tags[i] + split_tags[i+1])

    return clean_list


def process_line_save(line, line_number, file_name):
    global tags_list
    global checkErrorLog

    # split line
    plc_tag, dp_value, tag_type = line.split("|")

    # read online value, try, except in case tag doesn't exists
    try:
        dp_value = read_tag(plc_tag)
        put_string = plc_tag + "|" + str(dp_value) + "|" + str(tag_type)

        # append to list
        tags_list.append(put_string)

    except ValueError as e:
        app_log.error("Save Error: %s line %s tag %s %s" % (file_name, line_number, plc_tag, e))
        checkErrorLog = True


def process_line_load(line, line_number, file_name):
    global checkErrorLog
    # split line
    plc_tag, dp_value, tag_type = line.split("|")
    tag_type = tag_type.rstrip("\n")

    # write value to plc
    # bool are handled special
    # it expects True or False, 1 or 0, not a string
    if tag_type == "BOOL" or tag_type == "BIT":
        if dp_value == "True":
            dp_value = True
        if dp_value == "False":
            dp_value = False

    ret = comm.Write(plc_tag, dp_value)
   
    if ret.Status != "Success":
        app_log.error("Load Error: %s line %s tag  %s %s" % (file_name, line_number, plc_tag, ret.Status))
        checkErrorLog = True


def process_line_verification(line, line_number, file_name):
    global checkErrorLog
    # split line
    plc_tag, dp_value, tag_type = line.split("|")

    try:
        str_tag = str(read_tag(plc_tag))
    except ValueError as e:
        app_log.error("Verify Error: %s line %s tag %s %s" % (file_name, line_number, plc_tag, e))
        str_tag = "None"
        checkErrorLog = True

    # if it matches return true
    if str_tag == dp_value:
        return True
    else:
        app_log.error("Compare Error: %s line %s tag %s online value %s - dp value %s" % (file_name, line_number, plc_tag, str_tag, dp_value))
        checkErrorLog = True
        return False


def yes_or_no(question):
    while "the answer is invalid":
        reply = str(input(question+' (y/n): ')).lower().strip()
        if reply[0] == 'y':
            return True
        if reply[0] == 'n':
            return False


def copy_directory(src, dest):
    try:
        shutil.copytree(src, dest)
    # Directories are the same
    except shutil.Error as e:
        print('Directory not copied. Error: %s' % e)
    # Any error saying that the directory doesn't exist
    except OSError as e:
        print('Directory not copied. Error: %s' % e)


# Custom copytree2 in case folder is already created
# https://stackoverflow.com/a/12514470/1013828
def copytree2(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)

def convert(seconds): 
    min, sec = divmod(seconds, 60) 
    hour, min = divmod(min, 60) 
    return "%d:%02d:%02d" % (hour, min, sec) 


def print_header():
    ascii_art = """
        ____  ____  __  __
       / __ \/ __ \/ / / /
      / / / / /_/ / / / /
     / /_/ / ____/ /_/ /
    /_____/_/    \____/

    """
    print(ascii_art)
    print("Data Preserve Utility " + CODE_VERSION)
    print("Author: Fernando ***REMOVED***")
    print("Source: " + "https://github.com/TheFern2/Data_Preserve")


if __name__ == '__main__':

    config = configparser.ConfigParser()
    config.read('Settings.ini')
    main_controller_ip = config['Settings']['PLC_IP']
    comm.IPAddress = main_controller_ip
    comm.ProcessorSlot = int(config['Settings']['PLC_SLOT'])
    dp_save_remote_path = config['Settings']['Remote_Save_Path']
    dp_save_local_path = config['Settings']['Local_Save_Path']
    file_extension = config['Settings']['Files_Extension']

    # load remote file names from ini
    for key in config['Remote_Files']:
        remote_files.append(config['Remote_Files'][key])

     # load local file names from ini
    for key in config['Local_Files']:
        local_files.append(config['Local_Files'][key])

    for key in config['Folder_Copy_On_Load']:
        paths_on_load.append(config['Folder_Copy_On_Load'][key])

    for key in config['Folder_Copy_On_Save']:
        paths_on_save.append(config['Folder_Copy_On_Save'][key])

    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--save', action='store_true', help="Save data preserve")
    parser.add_argument('-l', '--load', action='store_true', help="Load data preserve")
    parser.add_argument('-b', '--bypass-prompt', action='store_true', help="Bypass yes/no prompt for loading")
    parser.add_argument('-v', '--verify', action='store_true', help="Verify data preserve")
    parser.add_argument('-a', '--auto-close', type=int, nargs='?', const=20, help="Auto close cmd prompt")
    parser.add_argument('-c', '--copy-to-local-dir', action='store_true', help="Copies data preserve to utility root dir")
    parser.add_argument('-r', '--copy-to-remote-dir', action='store_true', help="Copies data preserve from utility root dir to remote dir")
    args = parser.parse_args()

    # ping controller
    if ping(main_controller_ip) is None:
        print("Check Settings.ini or ethernet connection!")
        sys.exit()

    # if local path is empty use root dir
    if dp_save_local_path == "":            
        dp_save_local_path = os.getcwd()

    if args.load:
        proceed_to_load = False
        if not args.bypass_prompt:
            if yes_or_no("Are you sure?"):
                proceed_to_load = True
        if args.bypass_prompt:
            proceed_to_load = True

        if proceed_to_load:
            head, tail = os.path.split(dp_save_remote_path)
            path = os.getcwd() + "\\" + tail
            print_header()
            
            # copy util root dir to remote path
            if args.copy_to_remote_dir and os.path.exists(dp_save_remote_path):
                if os.path.exists(path):
                    copytree2(path, dp_save_remote_path)
                else:
                    print("Please save data preserve first with -c or --copy-to-local-dir argument")
                    sys.exit()
            if args.copy_to_remote_dir and not os.path.exists(dp_save_remote_path):
                if os.path.exists(path):
                    if not os.path.exists(dp_save_remote_path):
                        os.mkdir(dp_save_remote_path)
                    copytree2(path, dp_save_remote_path)
                else:
                    print("Please save data preserve first with -c or --copy-to-local-dir argument")
                    sys.exit()

            # ensure remote file names from ini have their save counterparts
            # also checks if files exist on util root dir
            for config_file in remote_files:            
                path = os.getcwd() + "\\" + tail
                root_file = Path(path + "\\" + config_file + "_save." + file_extension)
                temp_file = Path(dp_save_remote_path + "\\" + config_file + "_save." + file_extension)
                if not temp_file.is_file() and not root_file.is_file():
                    print("Please save data preserve first! (Remote path)")
                    sys.exit()

            # ensure local file names from ini have their save counterparts
            for config_file in local_files:
                temp_file = Path(dp_save_local_path + "\\" + config_file + "_save." + file_extension)
                if not temp_file.is_file():
                    print("Please save data preserve first! (Local path)")
                    sys.exit()

            print("Loading data preserve...\n")
            start = time.time()

            for config_file in remote_files:           
                path = os.getcwd() + "\\" + tail
                load_verify_data_preserve(dp_save_remote_path, config_file)

            for config_file in local_files:
                load_verify_data_preserve(dp_save_local_path, config_file)

            # copy folders from root to config path on load
            for config_path in paths_on_load:
                # make dir on util root dir           
                path = os.getcwd() + "\\" + tail
                if not os.path.exists(path):
                    os.mkdir(path)
                # copy root dir to config path
                copytree2(path, config_path)

            end = time.time()
            print("%s Time Elapsed" % (convert(end - start)))

            if checkErrorLog:
                print("Check %s\\log.txt for errors!" % (os.getcwd()))

            if args.auto_close:
                print("Cmd prompt auto closing in %d seconds" % (args.auto_close))
                time.sleep(args.auto_close)
            else:
                input("Press Enter to exit...")
        else:
            print("Exiting...")
            sys.exit()

    if args.save:
        print_header()
        # ensure remote file names exist
        for config_file in remote_files:
            temp_file = Path(dp_save_remote_path + "\\" + config_file + "." + file_extension)
            if not temp_file.is_file():
                print("Data preserve remote files not found!")
                sys.exit()

        # ensure local file names exist
        for config_file in local_files:
            temp_file = Path(dp_save_local_path + "\\" + config_file + "." + file_extension)
            if not temp_file.is_file():
                print("Data preserve local files not found!")
                sys.exit()

        print("Saving data preserve...\n")
        start = time.time()

        # save data for every file under Remote_Files
        for config_file in remote_files:
            get_data_preserve(dp_save_remote_path, config_file)
            # make dir on util root dir && copy remote dir to util root dir (local path)
            if args.copy_to_local_dir:                
                head, tail = os.path.split(dp_save_remote_path)            
                path = os.getcwd() + "\\" + tail
                if not os.path.exists(path):
                    os.mkdir(path)
                copytree2(dp_save_remote_path, path)

        # save data for every file under Local_Files
        for config_file in local_files:
            get_data_preserve(dp_save_local_path, config_file)

        # copy folders on save
        for config_path in paths_on_save:
            # make dir on util root dir
            head, tail = os.path.split(config_path)            
            path = os.getcwd() + "\\" + tail
            if not os.path.exists(path):
                os.mkdir(path)
            # copy dir to util root dir
            copytree2(config_path, path)

        end = time.time()
        print("%s Time Elapsed" % (convert(end - start)))

        if checkErrorLog:
            print("Check %s\\log.txt for errors!" % (os.getcwd()))

        if args.auto_close:
            print("Cmd prompt auto closing in %d seconds" % (args.auto_close))
            time.sleep(args.auto_close)
        else:
            input("Press Enter to exit...")

    if args.verify:
        print_header()
        # ensure remote file names from ini have their save counterparts
        for config_file in remote_files:
            temp_file = Path(dp_save_remote_path + "\\" + config_file + "_save." + file_extension)
            if not temp_file.is_file():
                print("Please save data preserve first! (Remote path)")
                sys.exit()

        # ensure local file names from ini have their save counterparts
        for config_file in local_files:
            temp_file = Path(dp_save_local_path + "\\" + config_file + "_save." + file_extension)
            if not temp_file.is_file():
                print("Please save data preserve first! (Local path)")
                sys.exit()

        print("Verifying data...\n")
        start = time.time()

        for config_file in remote_files:
            load_verify_data_preserve(dp_save_remote_path, config_file, True)

        for config_file in local_files:
            load_verify_data_preserve(dp_save_local_path, config_file, True)

        end = time.time()
        print("%s Time Elapsed" % (convert(end - start)))

        if checkErrorLog:
            print("Check %s\\log.txt for errors!" % (os.getcwd()))

        if args.auto_close:
            print("Cmd prompt auto closing in %d seconds" % (args.auto_close))
            time.sleep(args.auto_close)
        else:
            input("Press Enter to exit...")

import os
import sys
import argparse
import shutil
import tarfile
from datetime import datetime


def parse_args():
    parser = argparse.ArgumentParser(description='Backup Projects')
    parser.add_argument('-d', '--destination', required=True, help='Backup destination directory')
    parser.add_argument('-s', '--source', required=True, help='Backup source file/folder')
    parser.add_argument('-i', '--include', nargs='+', help='Files to transfer')
    parser.add_argument('-e', '--exclude', nargs='+', help='Files to ignore')
    parser.add_argument('-n', '--name', default=None, help='Destination base folder Name')
    parser.add_argument('-c', '--compress', action='store_true', default=False, help='Should compress source')
    parser.add_argument('-f', '--force', action='store_true', default=False, help='Skip checking for changes')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    return parser.parse_args()


def get_last_modified(directory, include, exclude):
    list_of_files = get_file_tree(directory, '', include, exclude)
    latest_file = max(list_of_files, key=lambda fn: os.path.getmtime(os.path.join(directory, fn)), default=0)
    return os.stat(os.path.join(directory, latest_file)).st_mtime


def is_newer(source_time, destination_time):
    return source_time - destination_time > 2


def has_version_changed(source, destination, name=None, include=None, exclude=None):
    if not (os.path.exists(source) and os.path.isdir(source)):
        return False
    if not (os.path.exists(destination) and os.path.isdir(destination)):
        return True

    source_basename = name if name else os.path.basename(source)
    list_of_backups = list(filter(lambda fn: os.path.basename(fn).startswith(source_basename), os.listdir(destination)))
    if len(list_of_backups) == 0:
        return True
    latest_backup = max(list_of_backups, key=lambda file: os.path.getctime(os.path.join(destination, file)))

    return is_newer(get_last_modified(source, include, exclude), os.path.getctime(os.path.join(destination, latest_backup)))


def transfer_file(source, destination):
    try:
        if os.path.isdir(source):
            if not os.path.exists(destination):
                os.mkdir(destination)
                shutil.copystat(source, destination)
        else:
            shutil.copy2(source, destination)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(destination))
        transfer_file(source, destination)


def should_copy(file_name, include=None, exclude=None):
    if include:
        for include_item in include:
            if file_name.startswith(include_item):
                return True
        return False

    if exclude:
        for exclude_item in exclude:
            if file_name.startswith(exclude_item):
                return False
        return True

    return True


def get_file_tree(directory, base, include=None, exclude=None):
    for item in os.listdir(directory):
        s = os.path.join(base, item)
        if should_copy(s, include, exclude):
            yield s
            if os.path.isdir(os.path.join(directory, item)):
                yield from get_file_tree(os.path.join(directory, item), s, include, exclude)


def print_progress(header, status, is_end=False):
    w, _ = shutil.get_terminal_size((80, 20))
    print('\r' + header + ' ' * (w-len(status)-len(header)) + status, end='\n' if is_end else '')


def print_backup_state(file, status, is_end=False):
    print_progress('Backing up ' + '\'' + file + '\'', status, is_end)


def backup(source, destination, name=None, include=None, exclude=None, compress=True, force=False):
    print_backup_state(source, 'WORKING')
    if not os.path.exists(source):
        print_backup_state(source, 'NOT FOUND', True)
        return

    if not os.path.exists(destination):
        os.makedirs(destination)
    
    backup_file = None

    if force or has_version_changed(source, destination, name, include, exclude):
        date = datetime.now().strftime('%Y_%m_%d_%H%M%S')
        if name:
            basename = name
        else:
            basename = os.path.basename(os.path.normpath(source))
        destination = os.path.join(destination, basename + '_' + date)

        file_list = get_file_tree(source, '', include, exclude)
        if compress:
            backup_file = destination + '.tgz'
            tar = tarfile.open(backup_file, 'w')
            for file_item in file_list:
                tar.add(os.path.join(source, file_item), arcname=file_item, recursive=False)
            tar.close()
        else:
            backup_file = destination
            for file_item in file_list:
                s = os.path.join(source, file_item)
                d = os.path.join(destination, file_item)
                if os.path.isdir(s):
                    os.makedirs(d)
                else:
                    transfer_file(s, d)
                shutil.copystat(s, d)
        print_backup_state(source, 'DONE', True)
    else:
        print_backup_state(source, 'UP TO DATE', True)
    return backup_file


def main():
    args = parse_args()
    backup(args.source, args.destination, args.name, args.include, args.exclude, args.compress, args.force)


if __name__ == '__main__':
    main()

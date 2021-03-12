import os
import sys
import argparse
import shutil
import tarfile
import datetime


def parse_args():
    parser = argparse.ArgumentParser(description='Backup Files')
    parser.add_argument('-d', '--destination', required=True, help='Backup destination directory')
    parser.add_argument('-s', '--source', required=True, help='Backup source file/folder')
    parser.add_argument('-i', '--include', nargs='+', help='Files to transfer')
    parser.add_argument('-e', '--exclude', nargs='+', help='Files to ignore')
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


def has_file_changed(source, destination):
    if not os.path.exists(source):
        return False
    if not os.path.exists(destination):
        return True
    return is_newer(os.stat(source).st_mtime, os.stat(destination).st_mtime)


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


def get_file_tree(directory, base, include=None, exclude=None, update_dirs=False):
    for item in os.listdir(directory):
        s = os.path.join(base, item)
        if should_copy(s, include, exclude):
            yield s
            if os.path.isdir(os.path.join(directory, item)):
                yield from get_file_tree(os.path.join(directory, item), s, include, exclude, update_dirs)
                if update_dirs:
                    yield s


def print_progress(header, status, is_end=False):
    w, _ = shutil.get_terminal_size((80, 20))
    print('\r' + header + ' ' * (w-len(status)-len(header)) + status, end='\n' if is_end else '')


def print_backup_state(file, status, is_end=False):
    print_progress('Backing up ' + '\'' + file + '\'', status, is_end)


def backup(source, destination, include=None, exclude=None, compress=False, compare_trees=False, force=False):
    print_backup_state(source, 'WORKING')
    if not os.path.exists(source):
        print_backup_state(source, 'NOT FOUND', True)
        return

    if not os.path.exists(destination):
        os.makedirs(destination)

    if os.path.isdir(source):
        if compress:
            destination_compressed = os.path.join(destination, os.path.basename(source) + '.tgz')
            last_modified = get_last_modified(source, include, exclude)
            if force or not os.path.exists(destination_compressed) or is_newer(last_modified, os.stat(destination_compressed).st_mtime):
                tar = tarfile.open(destination_compressed, 'w')
                for file_item in get_file_tree(source, '', include, exclude):
                    tar.add(os.path.join(source, file_item), arcname=file_item, recursive=False)
                tar.close()
                os.utime(destination_compressed, (last_modified, last_modified))
                print_backup_state(source, 'DONE', True)
            else:
                print_backup_state(source, 'UP TO DATE', True)
        else:
            if compare_trees:
                for file_item in get_file_tree(destination, '', None, None):
                    if not os.path.exists(os.path.join(source, file_item)) or not should_copy(file_item, include, exclude):
                        d = os.path.join(destination, file_item)
                        if os.path.isdir(d):
                            shutil.rmtree(d)
                        else:
                            os.remove(d)
            for file_item in get_file_tree(source, '', include, exclude, True):
                s = os.path.join(source, file_item)
                d = os.path.join(destination, file_item)
                if os.path.isdir(s):
                    if not os.path.exists(d):
                        os.makedirs(d)
                    shutil.copystat(s, d)
                else:
                    if force or has_file_changed(s, d):
                        transfer_file(s, d)
            print_backup_state(source, 'DONE', True)
    else:
        file_name, file_ext = os.path.splitext(source)
        if compress and file_ext != '.tgz':
            d = os.path.join(destination, os.path.basename(file_name) + '.tgz')
            if force or has_file_changed(source, d):
                tar = tarfile.open(d, 'w')
                tar.add(source, arcname=os.path.basename(source))
                tar.close()
                shutil.copystat(source, d)
                print_backup_state(source, 'DONE', True)
            else:
                print_backup_state(source, 'UP TO DATE', True)
        else:
            d = os.path.join(destination, os.path.basename(source))
            if force or has_file_changed(source, d):
                transfer_file(source, d)
                print_backup_state(source, 'DONE', True)
            else:
                print_backup_state(source, 'UP TO DATE', True)


def main() -> None:
    args = parse_args()
    perform_backup(args.source, args.destination, args.include, args.exclude, args.compress, args.force)


if __name__ == '__main__':
    main()

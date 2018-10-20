import os
import glob
import sys
import threading
import argparse
import shutil
import tarfile
import datetime


def parse_args():
    parser = argparse.ArgumentParser(description='Backup Projects')
    parser.add_argument('-d', '--destination', nargs=1, required=True, help='Backup Destination')
    parser.add_argument('-s', '--source', nargs=1, required=True, help='Backup Source Files')
    parser.add_argument('-w', '--whitelist', nargs='+', help='Files to Transfer')
    parser.add_argument('-b', '--blacklist', nargs='+', help='Files to Ignore')
    parser.add_argument('-n', '--name', nargs=1, default='', help='Destination Base Folder Name')
    parser.add_argument('-c', '--compress', action='store_true', default=False, help='Should Tar')
    parser.add_argument('-m', '--multithread', action='store_true', default=False, help='Should Use Threads')
    parser.add_argument('-t', '--threshold', nargs=1, type=int, default=0, help='Compression Threshold')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    return parser.parse_args()


def is_newer(source, destination):
    source_stat = os.stat(source)

    list_of_files = glob.glob(destination + '//*')
    if len(list_of_files) > 0:
        latest_file = max(list_of_files, key=os.path.getctime)
    else:
        return True

    return source_stat.st_mtime - os.path.getctime(latest_file) > 1


def transfer_file(source, destination, compression_threshold):
    try:
        size = os.stat(source).st_size
        if compression_threshold and (size > compression_threshold > 0):
            tar = tarfile.open(os.path.splitext(destination)[0] + ".tgz", "w:gz")
            tar.add(source, arcname=os.path.basename(source))
            tar.close()
        else:
            if os.path.isdir(source):
                print(source)
                if not os.path.exists(destination):
                    os.mkdir(destination)
                    shutil.copystat(source, destination)
            else:
                shutil.copy2(source, destination)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(destination))
        transfer_file(source, destination, compression_threshold)


def backup_source_threaded(source, destination, compression_threshold):
    thread = threading.Thread(target=transfer_file, args=(source, destination, compression_threshold))
    thread.start()
    return thread


def copy_file_tree(base, source, destination, whitelist, blacklist, compression_threshold):
    for item in os.listdir(source):
        should_copy = False
        s = os.path.join(source, item)

        if whitelist:
            for whitelist_item in whitelist:
                if s.startswith(os.path.join(base, whitelist_item)):
                    should_copy = True
                    break
            if not should_copy:
                continue
        else:
            should_copy = True

        if blacklist:
            for blacklist_item in blacklist:
                if s.startswith(os.path.join(base, blacklist_item)):
                    should_copy = False
                    break

        if should_copy:
            d = os.path.join(destination, item)
            if os.path.isdir(s):
                if not os.path.exists(d):
                    os.makedirs(d)
                copy_file_tree(base, s, d, whitelist, blacklist, compression_threshold)
            else:
                transfer_file(s, d, compression_threshold)
            shutil.copystat(s, d)


def get_file_tree(base, source, destination, whitelist, blacklist, compress):
    files = []
    for item in os.listdir(source):
        should_copy = False
        s = os.path.join(source, item)

        if whitelist:
            for whitelist_item in whitelist:
                if s.startswith(os.path.join(base, whitelist_item)):
                    should_copy = True
                    break
            if not should_copy:
                continue
        else:
            should_copy = True

        if blacklist:
            for blacklist_item in blacklist:
                if s.startswith(os.path.join(base, blacklist_item)):
                    should_copy = False
                    break

        if should_copy:
            d = os.path.join(destination, item)
            if os.path.isdir(s):
                if not compress and not os.path.exists(d):
                    os.makedirs(d)
                if len(os.listdir(s)) == 0:
                    files.append([s, d])
                else:
                    files = files + get_file_tree(base, s, d, whitelist, blacklist, compress)
            else:
                files.append([s, d])
    return files


def backup_source(source, destination, name, whitelist, blacklist, compress, compression_threshold, multithread):
    if not os.path.exists(source):
        print('SOURCE NOT FOUND \'' + source + '\'')
        return

    if compress and multithread:
        print('CANNOT COMPRESS IN THREADED MODE')
        return

    if not os.path.exists(destination):
        os.makedirs(destination)

    if is_newer(source, destination):
        date = str(datetime.datetime.now())[:16]
        date = date.replace(' ', '_').replace(':', '')
        basename = os.path.basename(os.path.normpath(source))
        if name:
            basename = name[0]
        destination = destination + '/' + basename + '_' + date

        if multithread:
            threads = []
            for file in get_file_tree(source, source, destination, whitelist, blacklist, False):
                threads.append(backup_source_threaded(file[0], file[1], compression_threshold))

            for thread in threads:
                thread.join()
        else:
            if compress:
                tar = tarfile.open(destination + ".tgz", "w:gz")
                for file in get_file_tree(source, source, destination, whitelist, blacklist, True):
                    tar.add(file[0], arcname=file[1].replace(destination, ""))
                tar.close()
            else:
                copy_file_tree(source, source, destination, whitelist, blacklist, compression_threshold)
    else:
        print('FILE IS UP TO DATE')


def perform_backup(source, destination, name, whitelist, blacklist, compress, compression_threshold, multithread):
    print('### STARTING BACKUP ####')
    print('BACKING UP ' + '\'' + source + '\'' + ' TO ' + '\'' + destination + '\'')
    backup_source(source, destination, name, whitelist, blacklist, compress, compression_threshold, multithread)
    print('### BACKUP COMPLETE ###')


def main():
    args = parse_args()
    perform_backup(args.source[0], args.destination[0], args.name, args.whitelist, args.blacklist, args.compress,
                   args.threshold[0], args.multithread)


if __name__ == '__main__':
    main()

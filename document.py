import os
import sys
import threading
import argparse
import shutil
import tarfile


def parse_args():
    parser = argparse.ArgumentParser(description='Backup Documents')
    parser.add_argument('-d', '--destination', nargs=1, required=True, help='Document Destination')
    parser.add_argument('-s', '--source', nargs='+', required=True, help='Document Source Files')
    parser.add_argument('-w', '--whitelist', nargs='+', help='Files to Transfer')
    parser.add_argument('-b', '--blacklist', nargs='+', help='Files to Ignore')
    parser.add_argument('-c', '--compress', action='store_true', default=False, help='Should Tar')
    parser.add_argument('-t', '--threshold', nargs=1, type=int, default=0, help='Compression Threshold')
    parser.add_argument('-m', '--multithread', action='store_true', default=False, help='Should Use Threads')
    parser.add_argument('-r', '--replace', action='store_true', default=False, help='Should Replace Old Files')

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    return parser.parse_args()


def is_newer(source, destination):
    if not os.path.exists(source):
        return False
    if not os.path.exists(destination):
        return True
    return os.stat(source).st_mtime - os.stat(destination).st_mtime > 1


def transfer_file(source, destination, compression_threshold):
    try:
        size = os.stat(source).st_size
        if compression_threshold and (size > compression_threshold > 0):
            tar = tarfile.open(os.path.splitext(destination)[0] + ".tgz", "w:gz")
            tar.add(source, arcname=os.path.basename(source))
            tar.close()
        else:
            if os.path.isdir(source):
                if not os.path.exists(destination):
                    os.mkdir(destination)
                    shutil.copystat(source, destination)
            else:
                shutil.copy2(source, destination)
    except FileNotFoundError:
        os.makedirs(os.path.dirname(destination))
        transfer_file(source, destination, compression_threshold)


def document_source_threaded(source, destination, whitelist, blacklist, compress, compression_threshold):
    thread = threading.Thread(target=document_source,
                              args=(source, destination, whitelist, blacklist, compress, compression_threshold))
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


def get_file_tree(base, file, whitelist, blacklist, compress, compression_threshold):
    files = []
    for item in os.listdir(file):
        should_copy = False
        s = os.path.join(file, item)

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
            if os.path.isdir(s):
                if compress:
                    files.append(s + '.tgz')
                else:
                    if len(os.listdir(s)) == 0:
                        files.append(s)
                    else:
                        files = files + get_file_tree(base, s, whitelist, blacklist, compress, compression_threshold)
                        files.append(s)
            else:
                if compress or (compression_threshold and (os.stat(s).st_size > compression_threshold > 0)):
                    files.append(os.path.join(base, os.path.basename(s) + '.tgz'))
                else:
                    files.append(s)
    return files


def get_transfer_tree(base, source, destination, whitelist, blacklist, compress):
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
                    files = files + get_transfer_tree(base, s, d, whitelist, blacklist, compress)
            else:
                files.append([s, d])
    return files


def document_source(source, destination, whitelist, blacklist, compress, compression_threshold):
    print('DOCUMENTING ' + '\'' + source + '\'' + ' TO ' + '\'' + destination + '\'')
    name = os.path.basename(source)
    destination_normal = os.path.join(destination, name)
    destination_compressed = os.path.join(destination, name + ".tgz")

    if (not os.path.exists(destination_normal) and not os.path.exists(destination_compressed)) \
            or (compress and os.path.exists(destination_normal)) \
            or (os.path.exists(destination_normal) and is_newer(source, destination_normal)) \
            or (not compress and os.path.exists(destination_compressed)) \
            or (os.path.exists(destination_compressed)) and is_newer(source, destination_compressed):
        if os.path.isdir(source):
            if not compress and os.path.exists(destination_normal):
                shutil.rmtree(destination_normal)
            if compress and os.path.exists(destination_compressed):
                os.remove(destination_compressed)
            if compress:
                tar = tarfile.open(destination_compressed, "w:gz")
                for file in get_transfer_tree(source, source, destination, whitelist, blacklist, True):
                    tar.add(file[0], arcname=file[1].replace(destination, ""))
                tar.close()
                shutil.copystat(source, destination_compressed)
            else:
                copy_file_tree(source, source, destination_normal, whitelist, blacklist, compression_threshold)
                shutil.copystat(source, destination_normal)
        else:
            if not compress and os.path.exists(destination_normal):
                os.remove(destination_normal)
            if compress and os.path.exists(destination_compressed):
                os.remove(destination_compressed)

            if compress and os.path.splitext(name)[1] != 'tgz':
                tar = tarfile.open(destination_compressed, "w:gz")
                tar.add(source, arcname=name)
                tar.close()
                shutil.copystat(source, destination_compressed)
            else:
                transfer_file(source, destination, compression_threshold)
        print('DOCUMENTED \'' + source + '\'')
    else:
        print('FILE \'' + source + '\' IS UP TO DATE')


def perform_document(sources, destination, whitelist, blacklist, compress, compression_threshold, multithread, replace):
    print('### STARTING DOCUMENTATION ####')
    for source in sources:
        if not os.path.exists(source):
            print('SOURCE NOT FOUND \'' + source + '\'')
            return

        if not os.path.exists(destination):
            os.makedirs(destination)

        if os.path.isdir(source):
            if replace:
                destination_tree = get_file_tree(destination, destination, [], [], False, None)
                source_tree = get_file_tree(source, source, whitelist, blacklist, compress, compression_threshold)
                for file in destination_tree:
                    found = False
                    for i in range(0, len(source_tree)):
                        if file[len(destination):] == source_tree[i][len(source):]:
                            source_tree.pop(i)
                            found = True
                            break
                    if not found:
                        if os.path.isdir(file):
                            shutil.rmtree(file)
                        else:
                            os.remove(file)

            if multithread:
                threads = []
                for item in os.listdir(source):
                    threads.append(
                        document_source_threaded(os.path.join(source, item), destination, whitelist, blacklist, compress,
                                                 compression_threshold))

                for thread in threads:
                    thread.join()
            else:
                for item in os.listdir(source):
                    document_source(os.path.join(source, item), destination, whitelist, blacklist, compress,
                                    compression_threshold)
        elif os.path.isfile(source):
            document_source(source, destination, whitelist, blacklist, compress, compression_threshold)
    print('### DOCUMENTATION COMPLETE ###')


def main():
    args = parse_args()
    perform_document(args.source, args.destination[0], args.whitelist, args.blacklist, args.compress,
                     args.threshold[0], args.multithread, args.replace)


if __name__ == '__main__':
    main()

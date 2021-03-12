import os
import time
import shutil
import tarfile
import backup
import backup_version

test_dir = 'test'
dir_name = 'project'
from_dir = os.path.join(test_dir, dir_name)
to_dir = os.path.join(test_dir, dir_name + '_backup')


# Pause for a while so backups can be differentiated
def tick():
    time.sleep(2)


def write_file(file_name, text):
    f = open(os.path.join(from_dir, file_name), 'w')
    f.write(text)
    f.close()


def read_file(file_name):
    f = open(os.path.join(to_dir, file_name), 'r')
    text = f.read()
    f.close()
    return text


def mkdir(directory_name):
    os.mkdir(os.path.join(from_dir, directory_name))


def delete_file(file_name):
    file_name = os.path.join(from_dir, file_name)
    if os.path.isdir(file_name):
        shutil.rmtree(file_name)
    else:
        os.remove(file_name)


def get_tar_members(file_name):
    f = tarfile.open(os.path.join(to_dir, file_name), 'r')
    members = f.getnames()
    f.close()
    return members


# Properly back up a new project
def version_new():
    os.mkdir(from_dir)
    write_file('1.txt', '1')
    mkdir('folder')
    write_file(os.path.join('folder', 'a.txt'), 'a')
    b = backup_version.backup(from_dir, to_dir, compress=False)
    return b and \
           os.path.exists(to_dir) and \
           os.path.exists(b) and \
           os.path.exists(os.path.join(b, 'folder')) and \
           os.path.exists(os.path.join(b, '1.txt')) and \
           os.path.exists(os.path.join(b, 'folder', 'a.txt'))


# Properly back up an existing project
def version_existing():
    write_file(os.path.join('folder', 'a.txt'), 'b')
    b1 = backup_version.backup(from_dir, to_dir, compress=False)
    tick()
    b2 = backup_version.backup(from_dir, to_dir, compress=False)
    return b1 and os.path.exists(b1) and not b2


# Support specifying files to include
def version_include():
    write_file('2.txt', '1')
    b = backup_version.backup(from_dir, to_dir, include=['2.txt'], compress=False)
    return b and \
        os.path.exists(b) and \
        os.path.exists(os.path.join(b, '2.txt')) and \
        len(os.listdir(b)) == 1


# Support specifying files to exclude
def version_exclude():
    write_file('2.txt', '2')
    b = backup_version.backup(from_dir, to_dir,
                              exclude=['1.txt', os.path.join('folder', 'a.txt')], compress=False)
    return b and \
        os.path.exists(b) and \
        os.path.exists(os.path.join(b, '2.txt')) and \
        os.path.exists(os.path.join(b, 'folder')) and \
        len(os.listdir(b)) == 2 and \
        len(os.listdir(os.path.join(b, 'folder'))) == 0


# Support compressing projects
def version_compress():
    b1 = backup_version.backup(from_dir, to_dir, compress=True)
    write_file('1.txt', '2')
    delete_file('2.txt')
    tick()
    b2 = backup_version.backup(from_dir, to_dir, compress=True)
    f = tarfile.open(b2, 'r')
    members = f.getnames()
    f.close()
    return not b1 and b2 and \
        os.path.exists(b2) and \
        os.path.splitext(b2)[1] == '.tgz' and \
        '1.txt' in members and \
        'folder' in members and \
        'folder/a.txt' in members and \
        len(members) == 3


# Support includes while compressing projects
def version_compress_include():
    write_file('1.txt', '3')
    tick()
    b = backup_version.backup(from_dir, to_dir, include=['1.txt'], compress=True)
    f = tarfile.open(b, 'r')
    members = f.getnames()
    f.close()
    return b and \
        os.path.exists(b) and \
        os.path.splitext(b)[1] == '.tgz' and \
        '1.txt' in members and \
        len(members) == 1


# Support excludes while compressing projects
def version_compress_exclude():
    write_file('1.txt', '3')
    tick()
    b = backup_version.backup(from_dir, to_dir, exclude=['folder'], compress=True)
    f = tarfile.open(b, 'r')
    members = f.getnames()
    f.close()
    return b and \
        os.path.exists(b) and \
        os.path.splitext(b)[1] == '.tgz' and \
        '1.txt' in members and \
        len(members) == 1


# Support backup without checking changes
def version_force():
    b = backup_version.backup(from_dir, to_dir, compress=True, force=True)
    return b and os.path.exists(b)


# Support custom naming for a new project
def version_name_new():
    write_file('1.txt', '5')
    b1 = backup_version.backup(from_dir, to_dir, compress=False, name='test_project')
    tick()
    write_file('1.txt', '6')
    b2 = backup_version.backup(from_dir, to_dir, compress=True, name='test_project')
    return b1 and \
        'test_project' in b1 and \
        os.path.exists(b1) and \
        b2 and \
        'test_project' in b2 and \
        b2.endswith('.tgz') and \
        os.path.exists(b2)


# Support custom naming for existing project
def version_name_existing():
    b1 = backup_version.backup(from_dir, to_dir, compress=False, name='test_project')
    tick()
    write_file('1.txt', '7')
    b2 = backup_version.backup(from_dir, to_dir, compress=False, name='test_project')
    return not b1 and b2 and os.path.exists(b2)


def test_version():
    if os.path.exists(f'{test_dir}'):
        shutil.rmtree(f'{test_dir}')
    os.mkdir(f'{test_dir}')

    try:
        tests = [
            ('new', version_new),
            ('existing', version_existing),
            ('include', version_include),
            ('exclude', version_exclude),
            ('compress', version_compress),
            ('compress include', version_compress_include),
            ('compress exclude', version_compress_exclude),
            ('force', version_force),
            ('name new', version_name_new),
            ('name existing', version_name_existing)
        ]
        for test in tests:
            if not test[1]():
                print(f'Failed test \'{test[0]}\'')
                break
            tick()
    except IOError:
        print('An error occurred')
    finally:
        shutil.rmtree(f'{test_dir}')


# Properly back up a new directory
def default_dir_new():
    os.mkdir(from_dir)
    write_file('1.txt', '1')
    mkdir('folder')
    write_file(os.path.join('folder', 'a.txt'), 'a')
    backup.backup(from_dir, to_dir, compress=False)
    return os.path.exists(to_dir) and \
        os.path.exists(os.path.join(to_dir, '1.txt')) and \
        os.path.exists(os.path.join(to_dir, 'folder')) and \
        os.path.exists(os.path.join(to_dir, 'folder', 'a.txt')) and \
        os.stat(os.path.join(to_dir, '1.txt')).st_mtime == os.stat(os.path.join(from_dir, '1.txt')).st_mtime and \
        os.stat(os.path.join(to_dir, 'folder')).st_mtime == os.stat(os.path.join(from_dir, 'folder')).st_mtime and \
        os.stat(os.path.join(to_dir, 'folder', 'a.txt')).st_mtime == os.stat(os.path.join(from_dir, 'folder', 'a.txt')).st_mtime


# Properly back up an existing directory
def default_dir_existing():
    write_file(os.path.join('folder', 'a.txt'), 'b')
    backup.backup(from_dir, to_dir, compress=False)
    return read_file(os.path.join('folder', 'a.txt')) == 'b' and \
        os.stat(os.path.join(to_dir, 'folder', 'a.txt')).st_mtime == os.stat(os.path.join(from_dir, 'folder', 'a.txt')).st_mtime and \
        os.stat(os.path.join(to_dir, '1.txt')).st_mtime == os.stat(os.path.join(from_dir, '1.txt')).st_mtime


# Support compressing directories
def default_dir_compress():
    backup.backup(from_dir, to_dir, compress=True)
    members = get_tar_members(dir_name + '.tgz')
    return os.path.exists(os.path.join(to_dir, dir_name + '.tgz')) and \
        '1.txt' in members and \
        'folder' in members and \
        'folder/a.txt' in members and \
        len(members) == 3


# Properly remove deleted files from backup directory
def default_dir_compare_trees():
    delete_file(os.path.join('folder', 'a.txt'))
    backup.backup(from_dir, to_dir, compare_trees=True, compress=False)
    return not os.path.exists(os.path.join(to_dir, 'folder', 'a.txt'))


# Support directory backup without checking changes
def default_dir_force():
    old_time = os.stat(os.path.join(from_dir, '1.txt')).st_mtime
    write_file('1.txt', '2')
    os.utime(os.path.join(from_dir, '1.txt'), (old_time, old_time))
    backup.backup(from_dir, to_dir, compress=False, force=True)
    return os.path.exists(os.path.join(to_dir, '1.txt')) and read_file('1.txt') == '2'


# Support specifying files to include
def default_dir_include():
    backup.backup(from_dir, to_dir, include=['1.txt'], compress=False, compare_trees=True)
    return os.path.exists(os.path.join(to_dir, '1.txt')) and \
        len(os.listdir(to_dir)) == 1


# Support specifying files to include while compressing
def default_dir_include_compressed():
    backup.backup(from_dir, to_dir, include=['1.txt'], compress=True, force=True)
    members = get_tar_members(dir_name + '.tgz')
    return os.path.exists(os.path.join(to_dir, dir_name + '.tgz')) and \
        '1.txt' in members and \
        len(members) == 1


# Support specifying files to exclude
def default_dir_exclude():
    backup.backup(from_dir, to_dir, exclude=['folder'], compress=False, compare_trees=True)
    return os.path.exists(os.path.join(to_dir, '1.txt')) and \
        len(os.listdir(to_dir)) == 1


# Support specifying files to exclude while compressing
def default_dir_exclude_compressed():
    backup.backup(from_dir, to_dir, exclude=['folder'], compress=True, force=True)
    members = get_tar_members(dir_name + '.tgz')
    return os.path.exists(os.path.join(to_dir, dir_name + '.tgz')) and \
        '1.txt' in members and \
        len(members) == 1


# Properly back up a new file
def default_file_new():
    write_file('a.txt', 'a')
    backup.backup(os.path.join(from_dir, 'a.txt'), to_dir, compress=False)
    return os.path.exists(os.path.join(to_dir, 'a.txt')) and \
        os.stat(os.path.join(from_dir, 'a.txt')).st_mtime == os.stat(os.path.join(to_dir, 'a.txt')).st_mtime


# Properly back up an existing file
def default_file_existing():
    old_time = os.stat(os.path.join(from_dir, 'a.txt')).st_mtime
    backup.backup(os.path.join(from_dir, 'a.txt'), to_dir, compress=False)
    b1_time = os.stat(os.path.join(from_dir, 'a.txt')).st_mtime
    tick()
    write_file('a.txt', 'b')
    backup.backup(os.path.join(from_dir, 'a.txt'), to_dir, compress=False)
    b2_time = os.stat(os.path.join(from_dir, 'a.txt')).st_mtime
    return os.path.exists(os.path.join(from_dir, 'a.txt')) and \
        b1_time == old_time and b2_time > old_time


# Support compressing files
def default_file_compress():
    write_file('a.txt', 'c')
    backup.backup(os.path.join(from_dir, 'a.txt'), to_dir, compress=True)
    return os.path.exists(os.path.join(to_dir, 'a.tgz')) and \
        os.stat(os.path.join(from_dir, 'a.txt')).st_mtime == os.stat(os.path.join(to_dir, 'a.tgz')).st_mtime


# Support compressing files
def default_file_compress():
    write_file('a.txt', 'c')
    backup.backup(os.path.join(from_dir, 'a.txt'), to_dir, compress=True)
    members = get_tar_members('a.tgz')
    return os.path.exists(os.path.join(to_dir, 'a.tgz')) and \
        os.stat(os.path.join(from_dir, 'a.txt')).st_mtime == os.stat(os.path.join(to_dir, 'a.tgz')).st_mtime and \
        'a.txt' in members and len(members) == 1


# Support backup without checking changes
def default_file_force():
    old_time = os.stat(os.path.join(from_dir, 'a.txt')).st_mtime
    write_file('a.txt', 'd')
    os.utime(os.path.join(from_dir, 'a.txt'), (old_time, old_time))
    backup.backup(os.path.join(from_dir, 'a.txt'), to_dir, compress=False, force=True)
    return os.path.exists(os.path.join(to_dir, 'a.txt')) and \
        read_file('a.txt') == 'd' and \
        os.stat(os.path.join(from_dir, 'a.txt')).st_mtime == os.stat(os.path.join(to_dir, 'a.tgz')).st_mtime


def test_default():
    if os.path.exists(f'{test_dir}'):
        shutil.rmtree(f'{test_dir}')
    os.mkdir(f'{test_dir}')

    try:
        tests = [
            ('dir new', default_dir_new),
            ('dir existing', default_dir_existing),
            ('dir compress', default_dir_compress),
            ('dir compare trees', default_dir_compare_trees),
            ('dir force', default_dir_force),
            ('dir include', default_dir_include),
            ('dir include compressed', default_dir_include_compressed),
            ('dir exclude', default_dir_exclude),
            ('dir exclude compressed', default_dir_exclude_compressed),
            ('file new', default_file_new),
            ('file existing', default_file_existing),
            ('file compress', default_file_compress),
            ('file force', default_file_force)
        ]
        for test in tests:
            if not test[1]():
                print(f'Failed test \'{test[0]}\'')
                break
            tick()
    except IOError:
        print('An error occurred')
    finally:
        shutil.rmtree(f'{test_dir}')


if __name__ == '__main__':
    test_version()
    test_default()

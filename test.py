import os
import backup
import document


def main():
    backup.perform_backup(os.getcwd() + '\\Tests\\test_backup', os.getcwd() + '\\Archive\\test_backup', None,
                          None, ['build'], True, None, False)
    document.perform_document([os.getcwd() + '\\Tests\\test_document'], os.getcwd() + "\\Archive\\test_document", None,
                              None, False, None, False, False)

if __name__ == '__main__':
    main()
import os
import backup
import document


def main():
    backup.perform_backup(os.getcwd() + '\\Tests\\test_backup', os.getcwd() + '\\Archive\\test_backup', None,
                          None, ['build'], True, None, False)
    document.perform_document([os.getcwd() + '\\Tests\\test_document_1'], os.getcwd() + "\\Archive\\test_document_1", None,
                              None, False, None, False, False)
    document.perform_document([os.getcwd() + '\\Tests\\test_document_2'], os.getcwd() + "\\Archive\\test_document_2", None,
                              None, True, None, False, True)


if __name__ == '__main__':
    main()

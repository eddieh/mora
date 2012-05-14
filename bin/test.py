#!/usr/bin/python
import optparse
import sys
# Install the Python unittest2 package before you run this script.
import unittest2

USAGE = """%prog SDK_PATH LIB_PATH TEST_PATH
Run unit tests for App Engine apps.

SDK_PATH    Path to the SDK installation
LIB_PATH    Path to project libraries
TEST_PATH   Path to package containing test modules"""


def main(sdk_path, lib_path, test_path):
    sys.path.insert(0, sdk_path)
    sys.path.append(lib_path)
    import dev_appserver
    dev_appserver.fix_sys_path()
    suite = unittest2.loader.TestLoader().discover(test_path)
    unittest2.TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    parser = optparse.OptionParser(USAGE)
    options, args = parser.parse_args()
    if len(args) != 3:
        print 'Error: Exactly 3 arguments required.'
        parser.print_help()
        sys.exit(1)
    SDK_PATH = args[0]
    LIB_PATH = args[1]
    TEST_PATH = args[2]
    main(SDK_PATH, LIB_PATH, TEST_PATH)

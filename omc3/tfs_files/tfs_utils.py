from tfs_files import tfs_pandas as tfs
from utils import logging_tools as logtools
import numpy as np
LOG = logtools.get_logger(__name__)


def significant_numbers(value, error):
    digits = -int(np.floor(np.log10(error)))
    if np.floor(error * 10 ** digits) == 1:
        digits = digits + 1
    return f"{round(value,digits):.{max(digits, 0)}f}", f"{round(error, digits):.{max(digits, 0)}f}"


def remove_nan_from_files(list_of_files, replace=False):
    """ Remove NAN-Entries from files in list_of_files.

    If replace=False a new file with .dropna in it's name is created, otherwise the file is
    overwritten.
    """
    for filepath in list_of_files:
        try:
            df = tfs.read_tfs(filepath)
            LOG.info(f"Read file {filepath:s}")
        except (IOError, tfs.TfsFormatError):
            LOG.info(f"Skipped file {filepath:s}")
        else:
            df = df.dropna(axis='index')
            if not replace:
                filepath += ".dropna"
            tfs.write_tfs(filepath, df)


def remove_header_comments_from_files(list_of_files):
    """ Check the files in list for invalid headers (no type defined) and removes them. """
    for filepath in list_of_files:
        LOG.info(f"Checking file: {filepath:s}")
        with open(filepath, "r") as f:
            f_lines = f.readlines()

        del_idcs = []
        for idx, line in enumerate(f_lines):
            if line.startswith("*"):
                break

            if line.startswith("@") and len(line.split("%")) == 1:
                del_idcs.append(idx)

        if len(del_idcs) > 0:
            LOG.info("    Found {:d} lines to delete.".format(len(del_idcs)))
            for idx in reversed(del_idcs):
                deleted_line = f_lines.pop(idx)
                LOG.info("    Deleted line: '{:s}'".format(deleted_line.strip()))

            with open(filepath, "w") as f:
                f.writelines(f_lines)


# Script Mode ##################################################################


if __name__ == '__main__':
    raise EnvironmentError("{:s} is not supposed to run as main.".format(__file__))


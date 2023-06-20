"""Provides a command line interface to the ``otoole`` package

The key functions are **convert**, **cplex** and **viz**.

The ``convert`` command allows convertion of multiple different OSeMOSYS input formats
including from/to csv, an AMPL format datafile, a folder of
CSVs, an Excel workbook with one tab per parameter, an SQLite database

The ``cplex`` command provides access to scripts which transform and process a CPLEX
solution file into a format which is more readily processed - either to CBC or CSV
format.

The ``validate`` command checks the technology and fuel names
against a standard or user defined configuration file.

The **viz** command allows you to produce a Reference Energy System diagram

Example
-------

Ask for help on the command line::

    >>> $ otoole --help
    usage: otoole [-h] [--verbose] [--version] {convert,cplex,validate,viz} ...

    otoole: Python toolkit of OSeMOSYS users

    positional arguments:
    {convert,cplex,validate,viz}
        convert             Convert from one input format to another
        cplex               Process a CPLEX solution file
        validate            Validate an OSeMOSYS model
        viz                 Visualise the model

    optional arguments:
    -h, --help            show this help message and exit
    --verbose, -v         Enable debug mode
    --version, -V         The version of otoole

"""
import argparse
import logging
import os
import shutil
import sys

from otoole import __version__, convert, convert_results
from otoole.exceptions import OtooleSetupError
from otoole.preprocess.setup import get_config_setup_data, get_csv_setup_data
from otoole.read_strategies import ReadCsv, ReadDatafile, ReadExcel
from otoole.utils import (
    _read_file,
    read_deprecated_datapackage,
    read_packaged_file,
    validate_config,
)
from otoole.validate import main as validate
from otoole.visualise import create_res
from otoole.write_strategies import WriteCsv

logger = logging.getLogger(__name__)


def validate_model(args):
    data_format = args.data_format
    data_file = args.data_file
    user_config = args.user_config

    _, ending = os.path.splitext(user_config)
    with open(user_config, "r") as user_config_file:
        config = _read_file(user_config_file, ending)
    validate_config(config)

    if data_format == "datafile":
        read_strategy = ReadDatafile(user_config=config)
    elif data_format == "datapackage":
        logger.warning(
            "Reading from datapackage is deprecated, trying to read from CSVs"
        )
        data_file = read_deprecated_datapackage(data_file)
        logger.info("Successfully read folder of CSVs")
        read_strategy = ReadCsv(user_config=config)
    elif data_format == "csv":
        read_strategy = ReadCsv(user_config=config)
    elif data_format == "excel":
        read_strategy = ReadExcel(user_config=config)

    input_data, _ = read_strategy.read(data_file)

    if args.validate_config:
        validation_config = read_packaged_file(args.validate_config)
        validate(input_data, validation_config)
    else:
        validate(input_data)


def _result_matrix(args):
    convert_results(
        args.config,
        args.input_datapackage,
        args.input_csvs,
        args.input_datafile,
        args.to_path,
        args.from_path,
        args.from_format,
        args.to_format,
        args.write_defaults,
    )


def _conversion_matrix(args):
    """Convert from one format to another

    Implemented conversion functions::

        from\to     ex cs df
        --------------------
        excel       -- yy --
        csv         nn -- nn
        datafile    nn -- --

    """
    convert(
        args.config,
        args.from_format,
        args.to_format,
        args.from_path,
        args.to_path,
        args.write_defaults,
    )


def data2res(args):
    """Get input data and call res creation."""

    data_format = args.data_format
    data_path = args.data_path

    _, ending = os.path.splitext(args.config)
    with open(args.config, "r") as config_file:
        config = _read_file(config_file, ending)
    validate_config(config)

    if data_format == "datafile":
        read_strategy = ReadDatafile(user_config=config)
    elif data_format == "datapackage":
        logger.warning(
            "Reading from datapackage is deprecated, trying to read from CSVs"
        )
        data_path = read_deprecated_datapackage(data_path)
        read_strategy = ReadCsv(user_config=config)
    elif data_format == "csv":
        read_strategy = ReadCsv(user_config=config)
    elif data_format == "excel":
        read_strategy = ReadExcel(user_config=config)

    input_data, _ = read_strategy.read(data_path)

    create_res(input_data, args.resfile)


def setup(args):
    """Creates template data"""

    data_type = args.data_type
    data_path = args.data_path
    write_defaults = args.write_defaults
    overwrite = args.overwrite

    if os.path.exists(data_path) and not overwrite:
        raise OtooleSetupError(resource=data_path)

    if data_type == "config":
        shutil.copyfile(
            os.path.join(os.path.dirname(__file__), "preprocess", "config.yaml"),
            data_path,
        )
    elif data_type == "csv":
        config = get_config_setup_data()
        input_data, default_values = get_csv_setup_data(config)
        WriteCsv(user_config=config).write(
            input_data, data_path, default_values, write_defaults=write_defaults
        )


def get_parser():
    parser = argparse.ArgumentParser(
        description="otoole: Python toolkit of OSeMOSYS users"
    )

    parser.add_argument(
        "--verbose", "-v", help="Enable debug mode", action="count", default=0
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=__version__,
        help="The version of otoole",
    )

    subparsers = parser.add_subparsers()

    # Parser for results
    result_parser = subparsers.add_parser("results", help="Post-process solution files")
    result_parser.add_argument(
        "from_format",
        help="Result data format to convert from",
        choices=sorted(["cbc", "cplex", "gurobi"]),
    )
    result_parser.add_argument(
        "to_format",
        help="Result data format to convert to",
        choices=sorted(["csv"]),
    )
    result_parser.add_argument(
        "from_path", help="Path to file or folder to convert from"
    )
    result_parser.add_argument("to_path", help="Path to file or folder to convert to")
    result_parser.add_argument(
        "--input_datafile",
        help="Input GNUMathProg datafile required for OSeMOSYS short or fast results",
        default=None,
    )
    result_parser.add_argument(
        "--input_datapackage",
        help="Deprecated",
        default=None,
    )
    result_parser.add_argument("config", help="Path to config YAML file")
    result_parser.add_argument(
        "--write_defaults",
        help="Writes default values",
        default=False,
        action="store_true",
    )
    result_parser.set_defaults(func=_result_matrix)

    # Parser for conversion
    convert_parser = subparsers.add_parser(
        "convert", help="Convert from one input format to another"
    )
    convert_parser.add_argument(
        "from_format",
        help="Input data format to convert from",
        choices=sorted(["datafile", "excel", "csv"]),
    )
    convert_parser.add_argument(
        "to_format",
        help="Input data format to convert to",
        choices=sorted(["datafile", "csv", "excel"]),
    )
    convert_parser.add_argument(
        "from_path", help="Path to file or folder to convert from"
    )
    convert_parser.add_argument("to_path", help="Path to file or folder to convert to")
    convert_parser.add_argument("config", help="Path to config YAML file")
    convert_parser.add_argument(
        "--write_defaults",
        help="Writes default values",
        default=False,
        action="store_true",
    )
    convert_parser.add_argument(
        "--keep_whitespace",
        help="Keeps leading/trailing whitespace",
        default=False,
        action="store_true",
    )
    convert_parser.set_defaults(func=_conversion_matrix)

    # Parser for validation
    valid_parser = subparsers.add_parser("validate", help="Validate an OSeMOSYS model")
    valid_parser.add_argument(
        "data_format",
        help="Input data format",
        choices=sorted(["datafile", "excel", "csv"]),
    )
    valid_parser.add_argument(
        "data_file", help="Path to the OSeMOSYS data file to validate"
    )
    valid_parser.add_argument("user_config", help="Path to config YAML file")
    valid_parser.add_argument(
        "--validate_config", help="Path to a user-defined validation-config file"
    )
    valid_parser.set_defaults(func=validate_model)

    # Parser for visualisation
    viz_parser = subparsers.add_parser("viz", help="Visualise the model")
    viz_subparsers = viz_parser.add_subparsers()

    res_parser = viz_subparsers.add_parser(
        "res", help="Generate a reference energy system"
    )
    res_parser.add_argument(
        "data_format",
        help="Input data format",
        choices=sorted(["datafile", "excel", "csv"]),
    )
    res_parser.add_argument("data_path", help="Input data path")
    res_parser.add_argument("resfile", help="Path to reference energy system")
    res_parser.add_argument("config", help="Path to config YAML file")
    res_parser.set_defaults(func=data2res)

    # parser for setup
    setup_parser = subparsers.add_parser("setup", help="Setup template files")
    setup_parser.add_argument(
        "data_type", help="Type of file to setup", choices=sorted(["config", "csv"])
    )
    setup_parser.add_argument("data_path", help="Path to file or folder to save to")
    setup_parser.add_argument(
        "--write_defaults",
        help="Writes default values",
        default=False,
        action="store_true",
    )
    setup_parser.add_argument(
        "--overwrite",
        help="Overwrites existing data",
        default=False,
        action="store_true",
    )
    setup_parser.set_defaults(func=setup)

    return parser


class DeprecateAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        logger.warning(f"Argument {self.option_strings} is deprecated and is ignored.")
        delattr(namespace, self.dest)


def main():

    parser = get_parser()
    args = parser.parse_args(sys.argv[1:])

    if args.verbose >= 1 and args.verbose < 2:
        logging.basicConfig(level=logging.INFO)
    if args.verbose > 2:
        logging.basicConfig(level=logging.DEBUG)

    def exception_handler(
        exception_type, exception, traceback, debug_hook=sys.excepthook
    ):
        if args.verbose:
            debug_hook(exception_type, exception, traceback)
        else:
            print("{}: {}".format(exception_type.__name__, str(exception)))

    sys.excepthook = exception_handler

    if "func" in args:
        args.func(args)
    else:
        parser.print_help()

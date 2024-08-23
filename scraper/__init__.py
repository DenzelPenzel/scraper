import logging
import os
import sys
from os.path import join, realpath
from pathlib import Path
from typing import Optional

from scraper.logger.struct_logger import StructLogger, StructLogRecord

_data_path = None
STRUCT_LOGGER_SET = False
_prefix_path = None
_independent_package: Optional[bool] = None

# Do not raise exceptions during log handling
logging.setLogRecordFactory(StructLogRecord)
logging.setLoggerClass(StructLogger)


def root_path() -> Path:
    return Path(realpath(join(__file__, "../../")))


def data_path():
    global _data_path
    if _data_path is None:
        _data_path = realpath(join(root_path(), "data"))

    if not os.path.exists(_data_path):
        os.makedirs(_data_path)
    return _data_path


def prefix_path() -> str:
    global _prefix_path
    if _prefix_path is None:
        from os.path import join, realpath
        _prefix_path = realpath(join(__file__, "../../"))
    return _prefix_path


def set_prefix_path(p: str):
    global _prefix_path
    _prefix_path = p


def log_path():
    global _data_path
    if _data_path is None:
        _data_path = realpath(join(root_path(), "logs"))

    if not os.path.exists(_data_path):
        os.makedirs(_data_path)
    return _data_path


def is_independent_package() -> bool:
    global _independent_package
    import os
    if _independent_package is None:
        _independent_package = not os.path.basename(sys.executable).startswith("python")
    return _independent_package


def chdir_to_data_directory():
    if not is_independent_package():
        # Do nothing.
        return

    import os

    import appdirs
    app_data_dir: str = appdirs.user_data_dir("Scraper", "scraper.io")
    os.makedirs(os.path.join(app_data_dir, "logs"), 0o711, exist_ok=True)
    os.chdir(app_data_dir)
    set_prefix_path(app_data_dir)


def init_logging(conf_filename: str):
    import io
    import logging.config
    from os.path import join
    from typing import Dict

    from ruamel.yaml import YAML

    from scraper.logger.struct_logger import StructLogger, StructLogRecord
    global STRUCT_LOGGER_SET
    if not STRUCT_LOGGER_SET:
        logging.setLogRecordFactory(StructLogRecord)
        logging.setLoggerClass(StructLogger)
        STRUCT_LOGGER_SET = True

    # Do not raise exceptions during log handling
    logging.raiseExceptions = False

    file_path: str = join(prefix_path(), "conf", conf_filename)
    yaml_parser: YAML = YAML()
    with open(file_path) as fd:
        yml_source: str = fd.read()
        yml_source = yml_source.replace("$PROJECT_DIR", prefix_path())
        # yml_source = yml_source.replace("$DATETIME", pd.Timestamp.now().strftime("%Y-%m-%d-%H-%M-%S"))
        io_stream: io.StringIO = io.StringIO(yml_source)
        config_dict: Dict = yaml_parser.load(io_stream)
        logging.config.dictConfig(config_dict)

import configargparse

CONFIG = None

arg_parser = configargparse.ArgParser(default_config_files=["config.txt"])

arg_parser.add("-c", "--config", is_config_file=True, help="Config file")

arg_parser.add("-t", "--secret_token", help="Discord bot login token")

arg_parser.add(
    "-p", "--command_prefix", default="$", help="The symbol used before commands"
)

arg_parser.add(
    "-d",
    "--database_connection",
    default="sqlite:///data.db",
    help="An SQLAlchemy connection string",
)

arg_parser.add("--host", default="127.0.0.1", help="Bind socket to this host")

arg_parser.add("--port", default="8000", help="Bind socket to this port")

arg_parser.add("--cache_max", default="2500", help="Maximun entries to store in cache")


def parse_args():
    global CONFIG
    CONFIG = arg_parser.parse_args()

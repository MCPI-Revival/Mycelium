from typing import Callable


COMMANDS = {

}

def primeCommand(name: str) -> Callable:
    def wrap(func: Callable):
        COMMANDS[name] = func
    return wrap

def processMessage(context, connection, message: str) -> None:
    username = connection["username"]

    if message.startswith("/"):
        message = message[1:]
        name = message.split(" ")[0]
        args = message.split(" ")[1:]

        try:
            COMMANDS[name](context, connection, args)
        except KeyError:
            print(f"[CHAT ({username}) Command not found: {name}")
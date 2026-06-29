"""Small CLI delegation helpers for skill command maps."""

from __future__ import annotations

import importlib
import inspect
import sys
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class SkillCommand:
    module: str
    description: str
    default_args: tuple[str, ...] = ()
    requires_flag: str = ""


def run_module_main(module_name: str, argv: Sequence[str] | None = None) -> int:
    """Run a module's main function with an argv-compatible surface."""
    args = list(argv or [])
    old_argv = sys.argv[:]
    sys.argv = [module_name, *args]
    try:
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError:
            from investment_system.core.skill_module_loader import add_skill_src_paths

            add_skill_src_paths()
            module = importlib.import_module(module_name)
        main = getattr(module, "main", None)
        if main is None:
            raise AttributeError(f"{module_name} has no main()")
        try:
            if len(inspect.signature(main).parameters) == 0:
                result = main()
            else:
                result = main(args)
        except SystemExit as exc:
            code = exc.code
            if code is None:
                return 0
            if isinstance(code, int):
                return code
            print(code, file=sys.stderr)
            return 1
        return 0 if result is None else int(result)
    finally:
        sys.argv = old_argv


def print_command_help(skill_name: str, commands: Mapping[str, SkillCommand]) -> None:
    print(f"Usage: {skill_name} <command> [args]\n")
    print("Commands:")
    for name in sorted(commands):
        print(f"  {name:<24} {commands[name].description}")
    print("\nRun '<command> --help' to see the delegated command options.")


def dispatch_skill_commands(
    skill_name: str,
    commands: Mapping[str, SkillCommand],
    argv: Sequence[str] | None = None,
) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        print_command_help(skill_name, commands)
        return 0

    command_name = args[0]
    command = commands.get(command_name)
    if command is None:
        print(f"Unknown command for {skill_name}: {command_name}", file=sys.stderr)
        print_command_help(skill_name, commands)
        return 2

    delegated_args = list(args[1:])
    if command.requires_flag:
        if "-h" not in delegated_args and "--help" not in delegated_args:
            if command.requires_flag not in delegated_args:
                print(
                    f"{skill_name} {command_name} may write files. "
                    f"Pass {command.requires_flag} to continue.",
                    file=sys.stderr,
                )
                return 0
            delegated_args.remove(command.requires_flag)

    return run_module_main(command.module, [*command.default_args, *delegated_args])

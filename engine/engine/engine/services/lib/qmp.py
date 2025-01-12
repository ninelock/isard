#
#   IsardVDI - Open Source KVM Virtual Desktops based on KVM Linux and dockers
#   Copyright (C) 2022 Simó Albert i Beltran
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU Affero General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU Affero General Public License for more details.
#
#   You should have received a copy of the GNU Affero General Public License
#   along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import base64
import json
import os
import pathlib
import subprocess
from shlex import quote

from engine.services.db.domains import PersonalUnit as DbPersonalUnit
from engine.services.db.domains import get_personal_unit_from_domain
from engine.services.log import logs
from libvirt import libvirtError, virDomain
from libvirt_qemu import qemuAgentCommand

NOTIFIER_CMD_LINUX = None
with open(
    os.path.join(pathlib.Path(__file__).parent.resolve(), "./qmp/notifier_linux.sh")
) as f:
    NOTIFIER_CMD_LINUX = f.read()

NOTIFIER_CMD_WINDOWS = None
with open(
    os.path.join(pathlib.Path(__file__).parent.resolve(), "./qmp/notifier_windows.bat")
) as f:
    NOTIFIER_CMD_WINDOWS = f.read()

PERSONAL_UNIT_CMD_LINUX = None
with open(
    os.path.join(
        pathlib.Path(__file__).parent.resolve(), "./qmp/personal_unit_linux.sh"
    )
) as f:
    PERSONAL_UNIT_CMD_LINUX = f.read()

PERSONAL_UNIT_CMD_WINDOWS = None
with open(
    os.path.join(
        pathlib.Path(__file__).parent.resolve(), "./qmp/personal_unit_windows.bat"
    )
) as f:
    PERSONAL_UNIT_CMD_WINDOWS = f.read()


class QMP:
    @staticmethod
    def exec_command(domain: virDomain, desktop_id: str, cmd) -> str:
        logs.workers.debug(f"Running QMP command in '{desktop_id}': {cmd}")
        raw_cmd = [
            "virsh",
            f"--connect={domain._conn.getURI()}",
            "qemu-agent-command",
            f"--domain={desktop_id}",
            f"--cmd={json.dumps(cmd)}",
        ]
        result = subprocess.run(raw_cmd, capture_output=True, text=True)
        logs.workers.debug(f"Running QMP command in '{desktop_id}': {cmd}")

        result.check_returncode()

        command_status = {
            "execute": "guest-exec-status",
            "arguments": {
                "pid": json.loads(str(result.stdout)).get("return", {}).get("pid"),
            },
        }
        raw_cmd = [
            "virsh",
            f"--connect={domain._conn.getURI()}",
            "qemu-agent-command",
            f"--domain={domain.name()}",
            f"--cmd={json.dumps(command_status)}",
        ]

        result = subprocess.run(raw_cmd, capture_output=True, text=True)
        result.check_returncode()

        logs.workers.debug("RESULT => " + str(result.stdout))

        return str(result.stdout) if result.stdout else ""

    @staticmethod
    def exec_commands(domain: virDomain, desktop_id: str, cmds):
        """
        Execute a list of commands in the specified domain
        :param domain: domain where the commands are going to be executed
        :param cmds: commands that are going to be executed
        """
        failed = True
        cmd = 0

        while failed and cmd <= len(cmds) - 1:
            command_exec = cmds[cmd]
            cmd = cmd + 1

            try:
                QMP.exec_command(domain, desktop_id, command_exec)
                failed = False

            except Exception as error:
                logs.workers.error(
                    f"libvirt error trying to execute command in desktop {desktop_id} "
                    f"with: {error}"
                )

        if failed:
            raise Exception("all commands have failed")

    @staticmethod
    def get_encoding(domain: virDomain, desktop_id: str) -> str:
        """
        Get the correct encoding for the desktop
        """
        # Attempt to get the encoding for the Windows machines
        try:
            result = QMP.exec_command(
                domain,
                desktop_id,
                {
                    "execute": "guest-exec",
                    "arguments": {
                        "path": "cmd.exe",
                        "arg": ["/C", "chcp"],
                        "capture-output": True,
                    },
                },
            )

            logs.workers.error(
                base64.b64decode(json.loads(result)["return"]["out-data"])
                .split(b": ")[1]
                .strip()
                .decode()
            )

            encoding = (
                base64.b64decode(json.loads(result)["return"]["out-data"])
                .split(b": ")[1]
                .strip()
                .decode()
            )

            logs.workers.debug("Using encoding: cp" + encoding)
            return "cp" + encoding

        # Default to utf-8 if non Windows or if there was an error getting the encoding
        except Exception as error:
            logs.workers.debug(
                "Error getting the encodig, falling back to utf-8: " f"{error}"
            )
            return "utf-8"


class Notifier:
    @staticmethod
    def notify_desktop(domain: virDomain, message: bytes):
        """
        Notify desktop with a message

        Guest should have qemu-guest-agent and libnotify-bin installed
        and the following libvirt xml.

        <channel type="unix">
            <source mode="bind"/>
            <target type="virtio" name="org.qemu.guest_agent.0"/>
        </channel>

        :param domain: domain to be notified
        :type domain: libvirt.virDomain
        :param message: message to notify
        "type message: bytes
        """
        desktop_id = domain.name()
        message_decoded = base64.b64decode(message).decode()

        logs.workers.info(
            f'Notifying desktop {desktop_id} with message "{message_decoded}"'
        )

        cmds = [
            Notifier.cmd_linux(domain, desktop_id, message_decoded),
            Notifier.cmd_windows(domain, desktop_id, message_decoded),
        ]

        try:
            QMP.exec_commands(domain, desktop_id, cmds)
            logs.workers.info(f"Domain {desktop_id} was successfully notified ")

        except Exception as error:
            logs.workers.error(
                f"Failed to notify desktop {desktop_id} "
                f'with message "{message_decoded}" with '
                f'error "{err}"'
            )

    def cmd_windows(domain: virDomain, desktop_id: str, message):
        shellscript = NOTIFIER_CMD_WINDOWS.format(
            message="^" + "^".join(message),  # Escape the characters for Windows
        ).encode(QMP.get_encoding(domain, desktop_id))

        return {
            "execute": "guest-exec",
            "arguments": {
                "path": "cmd.exe",
                "arg": ["/U"],
                "input-data": base64.b64encode(shellscript).decode(),
                "capture-output": True,
            },
        }

    def cmd_linux(domain: virDomain, desktop_id: str, message):
        shellscript = NOTIFIER_CMD_LINUX.format(
            title=quote("IsardVDI Notification"),
            message=quote(message),
        ).encode(QMP.get_encoding(domain, desktop_id))

        return {
            "execute": "guest-exec",
            "arguments": {
                "path": "/bin/sh",
                "input-data": base64.b64encode(shellscript).decode(),
                "capture-output": True,
            },
        }


class PersonalUnit:
    @staticmethod
    def connect_personal_unit(domain: virDomain):
        """
        Attempts to connect the personal unit of the user to the desktop
        """
        desktop_id = domain.name()

        unit = get_personal_unit_from_domain(desktop_id)
        if not unit:
            return

        logs.workers.info(f'Attempting to connect {desktop_id} to the personal unit!"')

        cmds = [
            PersonalUnit.cmd_linux(domain, desktop_id, unit),
            PersonalUnit.cmd_windows(domain, desktop_id, unit),
        ]

        try:
            QMP.exec_commands(domain, desktop_id, cmds)
            logs.workers.error(
                f"Desktop {desktop_id} was successfully connected to the personal unit"
            )

        except Exception as error:
            logs.workers.error(
                f"Failed to connect the desktop {desktop_id} "
                f"to the personal unit with"
                f'error "{error}"'
            )

    def cmd_windows(domain: virDomain, desktop_id: str, unit: DbPersonalUnit):
        shellscript = PERSONAL_UNIT_CMD_WINDOWS.format(
            protocol="s" if unit.get("tls", False) else "",
            verify_cert=unit["verify_cert"],
            user=unit["user_id"],
            password=unit["password"],
            host=unit["dav"],
        ).encode(QMP.get_encoding(domain, desktop_id))

        return {
            "execute": "guest-exec",
            "arguments": {
                "path": "cmd.exe",
                "arg": ["/U"],
                "input-data": base64.b64encode(shellscript).decode(),
                "capture-output": True,
            },
        }

    def cmd_linux(domain: virDomain, desktop_id: str, unit: DbPersonalUnit):
        shellscript = PERSONAL_UNIT_CMD_LINUX.format(
            protocol="s" if unit.get("tls", False) else "",
            verify_cert=unit["verify_cert"],
            user=unit["user_id"],
            password=unit["password"],
            host=unit["dav"],
        ).encode(QMP.get_encoding(domain, desktop_id))

        return {
            "execute": "guest-exec",
            "arguments": {
                "path": "/bin/sh",
                "input-data": base64.b64encode(shellscript).decode(),
                "capture-output": True,
            },
        }

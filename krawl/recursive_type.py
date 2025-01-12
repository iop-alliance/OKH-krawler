# SPDX-FileCopyrightText: 2024 Robin Vobruba <hoijui.quaero@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

from typing import Any, Union

RecVal = Union[bool, float, int, str, list["RecVal"], dict[str, "RecVal"]]

# RecDict = dict[str, RecVal]
RecDict = dict[str, Any]

RecDictStr = dict[str, Union["RecDictStr", str]]

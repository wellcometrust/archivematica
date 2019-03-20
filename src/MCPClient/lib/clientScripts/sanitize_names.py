#!/usr/bin/env python2

# This file is part of Archivematica.
#
# Copyright 2010-2013 Artefactual Systems Inc. <http://artefactual.com>
#
# Archivematica is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Archivematica is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Archivematica.  If not, see <http://www.gnu.org/licenses/>.

# @package Archivematica
# @subpackage MCPClient
# @author Joseph Perry <joseph@artefactual.com>

import string
import os
import re
from shutil import move as rename
import sys
import unicodedata
from unidecode import unidecode
from archivematicaFunctions import strToUnicode, unicodeToStr

VERSION = "1.10." + "$Id$".split(" ")[1]

# Letters, digits and a few punctuation characters
ALLOWED_CHARS = re.compile(r'[^a-zA-Z0-9\-_.\(\)]')
REPLACEMENT_CHAR = "_"


def sanitizeName(basename):
    unicode_name = unidecode(strToUnicode(basename))
    return ALLOWED_CHARS.sub("_", unicode_name)


class RenameFailed(Exception):
    def __init__(self, code):
        self.code = code


def sanitizePath(path):
    basename = os.path.basename(path)
    dirname = os.path.dirname(path)
    sanitizedName = sanitizeName(basename)

    if basename == sanitizedName:
        return path
    else:
        n = 1
        fileTitle, fileExtension = os.path.splitext(sanitizedName)
        sanitizedName = os.path.join(dirname, fileTitle + fileExtension)

        while os.path.exists(sanitizedName):
            sanitizedName = os.path.join(
                dirname, fileTitle + REPLACEMENT_CHAR + str(n) + fileExtension
            )
            n += 1
        exit_status = rename(path, sanitizedName)
        if exit_status:
            raise RenameFailed(exit_status)

        return sanitizedName


def sanitizeRecursively(path):
    path = os.path.abspath(path)
    sanitizations = {}

    sanitizedName = sanitizePath(path)
    if sanitizedName != path:
        path_key = unicodeToStr(unicodedata.normalize("NFC", path.decode("utf8")))
        sanitizations[path_key] = sanitizedName
    if os.path.isdir(sanitizedName):
        for f in os.listdir(sanitizedName):
            sanitizations.update(
                sanitizeRecursively(os.path.join(sanitizedName, f))
            )

    return sanitizations


def call(jobs):
    for job in jobs:
        with job.JobContext():
            try:
                path = job.args[1]
                if not os.path.isdir(path):
                    job.pyprint("Not a directory: " + path, file=sys.stderr)
                    job.set_status(255)
                    continue
                job.pyprint("Scanning: ", path)
                sanitizations = sanitizeRecursively(path)
                for oldfile, newfile in sanitizations.items():
                    job.pyprint(oldfile, " -> ", newfile)
                job.pyprint(
                    "TEST DEBUG CLEAR DON'T INCLUDE IN RELEASE", file=sys.stderr
                )
            except RenameFailed as e:
                job.set_status(e.code)

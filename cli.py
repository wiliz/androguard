#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Androguard is a full Python tool to play with Android files."""


# core modules
import sys, json
from loguru import logger


# 3rd party modules
import click

import androguard.core.apk

# local modules
import androguard

from androguard.core.androconf import show_logging
from main import (androarsc_main,
                  androaxml_main,
                  export_apps_to_format,
                  androsign_main,
                  androlyze_main,
                  androgui_main,
                  androdis_main,
                  androstrace_main,
                  androtrace_main,
                  androdump_main,
)

class MyFilter:

    def __init__(self, level):
        self.level = level

    def __call__(self, record):
        levelno = logger.level(self.level).no
        return record["level"].no >= levelno

@click.group(help=__doc__)
@click.version_option(version=androguard.__version__)
@click.option("--verbose", "--debug", 'verbosity', flag_value='verbose', help="Print more")
def entry_point(verbosity):
    if verbosity == None:
       logger.remove(0)
       my_filter = MyFilter("INFO")
       logger.add(sys.stderr, filter=my_filter, level=0)
    

@entry_point.command()
@click.option(
    '--input', '-i', 'input_',
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    help='AndroidManifest.xml or APK to parse (legacy option)',
)
@click.option(
    '--output', '-o',
    help='filename to save the decoded AndroidManifest.xml to, default stdout',
)
@click.option("--resource", "-r",
        help="Resource (any binary XML file) inside the APK to parse instead of AndroidManifest.xml"
)
@click.argument(
    'file_',
    required=False,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
def axml(input_, output, file_, resource):
    """
    Parse the AndroidManifest.xml.

    Parsing is either direct or from a given APK and prints in XML format or
    saves to file.

    This tool can also be used to process any AXML encoded file, for example
    from the layout directory.

    Example:

    \b
        $ androguard axml AndroidManifest.xml
    """
    if file_ is not None and input_ is not None:
        print("Can not give --input and positional argument! "
              "Please use only one of them!")
        sys.exit(1)

    if file_ is None and input_ is None:
        print("Give one file to decode!")
        sys.exit(1)

    if file_ is not None:
        androaxml_main(file_, output, resource)
    elif input_ is not None:
        androaxml_main(input_, output, resource)


@entry_point.command()
@click.option(
    '--input', '-i', 'input_',
    type=click.Path(exists=True),
    help='resources.arsc or APK to parse (legacy option)',
)
@click.argument(
    'file_',
    required=False,
)
@click.option(
    '--output', '-o',
    # required=True,  #  not required due to --list-types
    help='filename to save the decoded resources to',
)
@click.option(
    '--package', '-p',
    help='Show only resources for the given package name '
         '(default: the first package name found)',
)
@click.option(
    '--locale', '-l',
    help='Show only resources for the given locale (default: \'\\x00\\x00\')',
)
@click.option(
    '--type', '-t', 'type_',
    help='Show only resources of the given type (default: public)',
)
@click.option(
    '--id', 'id_',
    help="Resolve the given ID for the given locale and package. Provide the hex ID!"
)
@click.option(
    '--list-packages', is_flag=True,
    default=False,
    help='List all package names and exit',
)
@click.option(
    '--list-locales', is_flag=True,
    default=False,
    help='List all package names and exit',
)
@click.option(
    '--list-types', is_flag=True,
    default=False,
    help='List all types and exit',
)
def arsc(input_,
         file_,
         output,
         package,
         locale,
         type_,
         id_,
         list_packages,
         list_locales,
         list_types):
    """
    Decode resources.arsc either directly from a given file or from an APK.

    Example:

    \b
        $ androguard arsc app.apk
    """

    from androguard.core import androconf
    from androguard.core import axml, apk

    if file_ and input_:
        logger.info("Can not give --input and positional argument! Please use only one of them!")
        sys.exit(1)

    if not input_ and not file_:
        logger.info("Give one file to decode!")
        sys.exit(1)

    if input_:
        fname = input_
    else:
        fname = file_

    ret_type = androconf.is_android(fname)
    if ret_type == "APK":
        a = apk.APK(fname)
        arscobj = a.get_android_resources()
        if not arscobj:
            logger.error("The APK does not contain a resources file!")
            sys.exit(0)
    elif ret_type == "ARSC":
        with open(fname, 'rb') as fp:
            arscobj = axml.ARSCParser(fp.read())
            if not arscobj:
                logger.error("The resources file seems to be invalid!")
                sys.exit(1)
    else:
        logger.error("Unknown file type!")
        sys.exit(1)

    if id_:
        # Strip the @, if any
        if id_[0] == "@":
            id_ = id_[1:]
        try:
            i_id = int(id_, 16)
        except ValueError:
            print("ID '{}' could not be parsed! have you supplied the correct hex ID?".format(id_))
            sys.exit(1)

        name = arscobj.get_resource_xml_name(i_id)
        if not name:
            print("Specified resource was not found!")
            sys.exit(1)

        print("@{:08x} resolves to '{}'".format(i_id, name))
        print()

        # All the information is in the config.
        # we simply need to get the actual value of the entry
        for config, entry in arscobj.get_resolved_res_configs(i_id):
            print("{} = '{}'".format(config.get_qualifier() if not config.is_default() else "<default>", entry))

        sys.exit(0)

    if list_packages:
        print("\n".join(arscobj.get_packages_names()))
        sys.exit(0)

    if list_locales:
        for p in arscobj.get_packages_names():
            print("In Package:", p)
            print("\n".join(map(lambda x: "  \\x00\\x00"
                                if x == "\x00\x00"
                                else "  {}".format(x),
                                     sorted(arscobj.get_locales(p)))))
        sys.exit(0)

    if list_types:
        for p in arscobj.get_packages_names():
            print("In Package:", p)
            for locale in sorted(arscobj.get_locales(p)):
                print("  In Locale: {}".format("\\x00\\x00"
                      if locale == "\x00\x00" else locale))
                print("\n".join(map("    {}".format,
                                    sorted(arscobj.get_types(p, locale)))))
        sys.exit(0)

    androarsc_main(arscobj,
                   outp=output,
                   package=package,
                   typ=type_,
                   locale=locale)


@entry_point.command()
@click.option(
    '--input', '-i', 'input_',
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
    help='APK to parse (legacy option)',
)
@click.argument(
    'file_',
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
    required=False,
)
@click.option(
    '--output', '-o',
    required=True,
    help='output directory. If the output folder already exsist, '
         'it will be overwritten!',
)
@click.option(
    '--format', '-f', 'format_',
    help='Additionally write control flow graphs for each method, specify '
         'the format for example png, jpg, raw (write dot file), ...',
)
@click.option(
    '--jar', '-j',
    is_flag=True,
    default=False,
    help='Use DEX2JAR to create a JAR file',
)
@click.option(
    '--limit', '-l',
    help='Limit to certain methods only by regex (default: \'.*\')',
)
@click.option(
    '--decompiler', '-d',
    help='Use a different decompiler (default: DAD)',
)
def decompile(input_, file_, output, format_, jar, limit, decompiler):
    """
    Decompile an APK and create Control Flow Graphs.

    Example:

    \b
        $ androguard resources.arsc
    """
    from androguard import session
    if file_ and input_:
        print("Can not give --input and positional argument! "
              "Please use only one of them!", file=sys.stderr)
        sys.exit(1)

    if not input_ and not file_:
        print("Give one file to decode!", file=sys.stderr)
        sys.exit(1)

    if input_:
        fname = input_
    else:
        fname = file_

    s = session.Session()
    with open(fname, "rb") as fd:
        s.add(fname, fd.read())
    export_apps_to_format(fname, s, output, limit,
                          jar, decompiler, format_)


@entry_point.command()
@click.option(
    '--hash', 'hash_',
    type=click.Choice(['md5', 'sha1', 'sha256', 'sha512']),
    default='sha1', show_default=True,
    help='Fingerprint Hash algorithm',
)
@click.option(
    '--all', '-a', 'print_all_hashes',
    is_flag=True,
    default=False, show_default=True,
    help='Print all supported hashes',
)
@click.option(
    '--show', '-s',
    is_flag=True,
    default=False, show_default=True,
    help='Additionally of printing the fingerprints, show more '
         'certificate information',
)
@click.argument(
    'apk',
    nargs=-1,
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
)
def sign(hash_, print_all_hashes, show, apk):
    """Return the fingerprint(s) of all certificates inside an APK."""
    androsign_main(apk, hash_, print_all_hashes, show)


@entry_point.command()
@click.argument(
    'apks',
    nargs=-1,
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
)
def apkid(apks):
    """Return the packageName/versionCode/versionName per APK as JSON."""
    from androguard.core.apk import get_apkid

    logger.debug("APKID")

    results = dict()
    for apk in apks:
        results[apk] = get_apkid(apk)
    print(json.dumps(results, indent=2))


@entry_point.command()
@click.option(
    '--input_file', '-i',
    help="Specify the inital file to load in the GUI",
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
)
@click.option(
    '--input_plugin', '-p',
    help="Additional Plugin (currently unused)",
    type=click.Path(exists=True),
)
def gui(input_file, input_plugin):
    """Androguard GUI"""
    androgui_main(input_file, input_plugin)


@entry_point.command()
@click.option(
    '--session',
    help='Previously saved session to load instead of a file',
    type=click.Path(exists=True),
)
@click.argument(
    'apk',
    default=None,
    required=False,
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
)
def analyze(session, apk):
    """Open a IPython Shell and start reverse engineering."""
    androlyze_main(session, apk)


@entry_point.command()
@click.option("-o", "--offset",
        default=0,
        type=int,
        help="Offset to start dissassembly inside the file")
@click.option("-s", "--size",
        default=0,
        type=int,
        help="Number of bytes from offset to disassemble, 0 for whole file")
@click.argument(
        "DEX",
        type=click.Path(exists=True, dir_okay=False, file_okay=True),
        )
def disassemble(offset, size, dex):
    """
    Disassemble Dalvik Code with size SIZE starting from an offset
    """
    androdis_main(offset, size, dex)


@entry_point.command()
@click.argument(
    'apk',
    default=None,
    required=False,
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
)
def strace(apk):
    """
    Push an APK on the phone and start to trace all syscalls.

    Example:

    \b
        $ androguard strace test.APK
    """
    androstrace_main(apk)

@entry_point.command()
@click.argument(
    'apk',
    default=None,
    required=False,
    type=click.Path(exists=True, dir_okay=False, file_okay=True),
)
@click.option("-m", "--modules",
        multiple=True, default=[],
        help="A list of modules to load in frida")

def trace(apk, modules):
    """
    Push an APK on the phone and start to trace all interesting methods from the modules list

    Example:

    \b
        $ androguard trace test.APK -m "ipc/*"  -m "webviews/*" -m "modules/**"
    """
    androtrace_main(apk, modules, False)

@entry_point.command()
@click.argument(
    'package_name',
    default=None,
    required=False,
)
@click.option("-m", "--modules",
        multiple=True, default=[],
        help="A list of modules to load in frida")

def dtrace(package_name, modules):
    """
    Start dynamically an installed APK on the phone and start to trace all interesting methods from the modules list

    Example:

    \b
        $ androguard dtrace package_name -m "ipc/*"  -m "webviews/*" -m "modules/**"
    """
    androtrace_main(package_name, modules, True)

@entry_point.command()
@click.argument(
    'package_name',
    default=None,
    required=False,
)
@click.option("-m", "--modules",
        multiple=True, default=["androguard/pentest/modules/helpers/dump/dexdump.js"],
        help="A list of modules to load in frida")

def dump(package_name, modules):
    """
    Start dynamically an installed APK on the phone and start to trace all interesting methods from the modules list

    Example:

    \b
        $ androguard dump package_name
    """
    androdump_main(package_name, modules)

if __name__ == '__main__':
    entry_point()


import binaryninja as binja
import logging
import os

import CFG_pb2
import util

BINJA_DIR = os.path.dirname(os.path.abspath(__file__))
DISASS_DIR = os.path.dirname(BINJA_DIR)

EXT_MAP = {}
EXT_DATA_MAP = {}

CCONV_TYPES = {
    'C': CFG_pb2.ExternalFunction.CallerCleanup,
    'E': CFG_pb2.ExternalFunction.CalleeCleanup,
    'F': CFG_pb2.ExternalFunction.FastCall
}


def recover_cfg(bv, args):
    pb_mod = CFG_pb2.Module()
    pb_mod.name = os.path.basename(bv.file.filename)

    return pb_mod


def parse_defs_file(bv, path):
    logging.debug('  Parsing %s', path)
    with open(path) as f:
        for line in f.readlines():
            # Skip comments/empty lines
            if len(line.strip()) == 0 or line[0] == '#':
                continue

            if line.startswith('DATA:'):
                # DATA: (name) (PTR | size)
                _, dname, dsize = line.split()
                if 'PTR' in dsize:
                    dsize = bv.address_size
                EXT_DATA_MAP[dname] = int(dsize)
            else:
                # (name) (# args) (cconv) (ret) [(sign) | None]
                fname, args, cconv, ret, sign = (line.split() + [None])[:5]

                if cconv not in CCONV_TYPES:
                    logging.fatal('Unknown calling convention: %s', cconv)
                    exit(1)

                if ret not in ['Y', 'N']:
                    logging.fatal('Unknown return type: %s', ret)
                    exit(1)

                EXT_MAP[fname] = (int(args), CCONV_TYPES[cconv], ret, sign)


def get_cfg(args):
    # Setup logger
    logging.basicConfig(format='[%(levelname)s] %(message)s',
                        filename=args.log_file,
                        level=logging.DEBUG)

    # Load the binary in binja
    bv = util.load_binary(args.binary)

    # Collect all paths to defs files
    logging.debug('Parsing definitions files')
    def_paths = set(map(os.path.abspath, args.std_defs))
    def_paths.add(os.path.join(DISASS_DIR, 'defs', '{}.txt'.format(args.os)))  # default defs file

    # Parse all of the defs files
    for fpath in def_paths:
        if os.path.isfile(fpath):
            parse_defs_file(bv, fpath)
        else:
            logging.warn('%s is not a file', fpath)

    # Recover module
    logging.debug('Starting analysis')
    pb_mod = recover_cfg(bv, args)

    # Save cfg
    logging.debug('Saving to file: %s', args.output)
    with open(args.output, 'wb') as f:
        f.write(pb_mod.SerializeToString())

    return 0

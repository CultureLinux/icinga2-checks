#!/usr/bin/env python3

import argparse
import sys
from typing import NoReturn, Tuple

# Heavily based on the script from:
# check_mem.pl Copyright (C) 2000 Dan Larsson <dl@tyfon.net>
# heavily modified by
# Justin Ellison <justin@techadvise.com>
#
# The MIT License (MIT)
# Copyright (c) 2011 justin@techadvise.com

# Translate from perl to python with chatgpt in 2 copy/paste (we're doomed)
# dev@clinux.fr



exit_codes = {
    'UNKNOWN': 3,
    'OK': 0,
    'WARNING': 1,
    'CRITICAL': 2
}

# Initialisation des options d'arguments
def init() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Nagios Plugin - Check Memory')
    parser.add_argument('-c', type=int, required=True, help='Niveau critique en pourcentage')
    parser.add_argument('-f', action='store_true', help='Vérifie la mémoire libre')
    parser.add_argument('-u', action='store_true', help='Vérifie la mémoire utilisée')
    parser.add_argument('-C', action='store_true', help='Compter les caches OS comme mémoire libre')
    parser.add_argument('-H', action='store_true', help='Retirer les hugepages de la mémoire totale')
    parser.add_argument('-w', type=int, required=True, help='Niveau d’avertissement en pourcentage')
    parser.add_argument('-v', action='store_true', help='Mode verbeux')
    args = parser.parse_args()

    if not (args.f or args.u):
        parser.error("Vous devez sélectionner soit la mémoire libre (-f) ou utilisée (-u) à surveiller.")
    if args.f and args.w <= args.c:
        parser.error("Le niveau d'avertissement doit être supérieur au niveau critique pour la mémoire libre.")
    if args.u and args.w >= args.c:
        parser.error("Le niveau d'avertissement doit être inférieur au niveau critique pour la mémoire utilisée.")

    return args

# Récupère les informations de mémoire du système
def get_memory_info() -> Tuple[int, int, int, int]:
    """Lit les compteurs nécessaires dans /proc/meminfo."""
    if sys.platform != 'linux':
        raise ValueError("ce check est limité à Linux")

    fields = {
        'MemTotal', 'MemFree', 'Buffers', 'Cached', 'SReclaimable',
        'Shmem', 'HugePages_Total', 'Hugepagesize',
    }
    values = {}
    with open('/proc/meminfo') as f:
        for line in f:
            name, _, value = line.partition(':')
            if name in fields:
                values[name] = int(value.split(maxsplit=1)[0])

    total_memory_kb = values['MemTotal']
    free_memory_kb = values['MemFree']
    used_memory_kb = total_memory_kb - free_memory_kb
    caches_kb = sum(values.get(name, 0) for name in ('Buffers', 'Cached', 'SReclaimable'))
    caches_kb -= values.get('Shmem', 0)
    hugepages_count = values.get('HugePages_Total', 0)
    hugepages_kb = hugepages_count * values['Hugepagesize'] if hugepages_count else 0

    return free_memory_kb, used_memory_kb, caches_kb, hugepages_kb

# Afficher les informations à Nagios
def tell_nagios(used_memory: int, free_memory: int, args: argparse.Namespace) -> None:
    total_memory = used_memory + free_memory
    if total_memory <= 0 or min(used_memory, free_memory) < 0:
        finish("UNKNOWN - Compteurs mémoire incohérents", exit_codes['UNKNOWN'])

    if args.f:
        free_percent = free_memory / total_memory * 100
        if free_percent <= args.c:
            finish(f"CRITICAL - {free_percent:.1f}% ({free_memory} kB) libre", exit_codes['CRITICAL'])
        elif free_percent <= args.w:
            finish(f"WARNING - {free_percent:.1f}% ({free_memory} kB) libre", exit_codes['WARNING'])
        else:
            finish(f"OK - {free_percent:.1f}% ({free_memory} kB) libre", exit_codes['OK'])
    elif args.u:
        used_percent = used_memory / total_memory * 100
        if used_percent >= args.c:
            finish(f"CRITICAL - {used_percent:.1f}% ({used_memory} kB) utilisé", exit_codes['CRITICAL'])
        elif used_percent >= args.w:
            finish(f"WARNING - {used_percent:.1f}% ({used_memory} kB) utilisé", exit_codes['WARNING'])
        else:
            finish(f"OK - {used_percent:.1f}% ({used_memory} kB) utilisé", exit_codes['OK'])

# Afficher le message et quitter
def finish(msg: str, state: int) -> NoReturn:
    print(msg)
    sys.exit(state)

# Exécution du script
if __name__ == "__main__":
    args = init()
    try:
        free_memory_kb, used_memory_kb, caches_kb, hugepages_kb = get_memory_info()
    except (OSError, KeyError, ValueError, IndexError) as exc:
        finish(f"UNKNOWN - Lecture des compteurs mémoire impossible ({exc})", exit_codes['UNKNOWN'])

    if args.v:
        print(
            f"MemFree={free_memory_kb} kB MemUsed={used_memory_kb} kB "
            f"Caches={caches_kb} kB HugePages={hugepages_kb} kB",
            file=sys.stderr,
        )

    if args.C:
        used_memory_kb -= caches_kb
        free_memory_kb += caches_kb
    if args.H:
        used_memory_kb -= hugepages_kb

    tell_nagios(used_memory_kb, free_memory_kb, args)


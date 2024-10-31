#!/usr/bin/env python3

import argparse
import os
import sys

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
def init():
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
def get_memory_info():
    total_memory_kb = free_memory_kb = used_memory_kb = caches_kb = hugepages_kb = 0

    # Vérifie si le système est sous Linux
    if sys.platform == 'linux':
        with open('/proc/meminfo') as f:
            for line in f:
                if 'MemTotal' in line:
                    total_memory_kb = int(line.split()[1])
                elif 'MemFree' in line:
                    free_memory_kb = int(line.split()[1])
                elif 'Buffers' in line or 'Cached' in line or 'SReclaimable' in line:
                    caches_kb += int(line.split()[1])
                elif 'HugePages_Total' in line:
                    hugepages_kb += int(line.split()[1]) * int(line.split()[1])

        used_memory_kb = total_memory_kb - free_memory_kb

    return free_memory_kb, used_memory_kb, caches_kb, hugepages_kb

# Afficher les informations à Nagios
def tell_nagios(used_memory, free_memory, caches, hugepages, args):
    total_memory = used_memory + free_memory
    perf_warn = int(total_memory * (args.w / 100))
    perf_crit = int(total_memory * (args.c / 100))

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
def finish(msg, state):
    print(msg)
    sys.exit(state)

# Exécution du script
if __name__ == "__main__":
    args = init()
    free_memory_kb, used_memory_kb, caches_kb, hugepages_kb = get_memory_info()

    if args.C:
        used_memory_kb -= caches_kb
        free_memory_kb += caches_kb
    if args.H:
        used_memory_kb -= hugepages_kb

    tell_nagios(used_memory_kb, free_memory_kb, caches_kb, hugepages_kb, args)


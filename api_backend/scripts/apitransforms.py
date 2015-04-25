# coding: utf-8
import logging
# TODO Remove only for testing
import json
import io
from utils import get_percentage, format_percentage, sort_results_by_percentage
from config import JSON_EXAMPLE_PATH, SPECIAL_PARTIES
log = logging.getLogger('paso.%s' % (__name__))

PERC_KEY = "pct"

RESUMEN_RENAME = {
  'Electores': 'e',
  'VotantesJef': 'v',
  'Mesas': 'mt',
  'MesasInformadas': 'mi',
  'UltimaActualizacion': 'ut'
}

RESULTS_CAND_RENAME = {
    "id_candidato": "id",
    "votos": "v",
    "pct": "p"
}

RESULTS_PARTY_RENAME = {
    "votos": "v",
    "pct": "p",
    "id_partido": "id",
}

RESULTS_PARTY_SUMM_RENAME = {
    "votos": "v",
    "pct": "p",
}


def to_json(fname=None, d=None):
    '''For testing purposes'''
    with io.open('%s/%s.json'
                 % (JSON_EXAMPLE_PATH, fname),
                 'w', encoding='utf8') as f:
        log.debug("writing output JSON: %s.json" % (fname))
        f.write(json.dumps(d, ensure_ascii=False))


def t_rename_data(d=None, translation=None, p_key=None):
    '''translate desired data'''
    target_dict = {}
    try:
        for k, v in translation.iteritems():
            if (k == p_key):
                d[k] = format_percentage(d[k])
            target_dict[v] = d[k]
    except KeyError:
        log.error("Could not find required key %s in %s" % (k, d))
        # Stop execution abruptly
        exit(1)
    return target_dict


def t_resumen_API(origin_dict=None):
    '''get the desired data'''
    target_dict = {}
    try:
        for k, v in RESUMEN_RENAME.iteritems():
            target_dict[v] = origin_dict['resumen'][k]
    except KeyError:
        log.error("Could not find required key %s in %s" % (k, origin_dict))
        # Stop execution abruptly
        exit(1)

    # Calculate table percentage
    mp = get_percentage(target_dict, 'mi', 'mt')
    if mp:
        target_dict["mp"] = mp
    else:
        return None

    # Calculate voting percentage
    vp = get_percentage(target_dict, 'v', 'e')
    if vp:
        target_dict["vp"] = vp
    else:
        return None
    return target_dict


def t_results_section_API(d=None, comuna=None, dest_dict=None):
    '''Transform the received data
       to the desired format'''
    a99 = []
    a00 = []
    if not comuna:
        data = d["general"][0]["partidos"]
    else:
        data = d["general"][0]["comunas"]["partidos"]
        # 0 stores the global results for the election
    try:
        for idx, row in enumerate(data):
            a00.append(t_rename_data(row, RESULTS_PARTY_RENAME, PERC_KEY))
            if len(row["listas"]) == 1:
                # Do not include special parties inside "Listas únicas"
                if row["id_partido"] not in SPECIAL_PARTIES:
                    a99.append(t_rename_data(row, RESULTS_PARTY_RENAME, PERC_KEY))
            else:
                # Create transformed array for parties with many candidates
                t_a = [t_rename_data(l, RESULTS_CAND_RENAME, PERC_KEY)
                       for l in row["listas"]]
                if not comuna:
                    # First time we see the party create a dictionary for it
                    # and append results
                    t_d = {"r": t_rename_data(row,
                                              RESULTS_PARTY_SUMM_RENAME,
                                              PERC_KEY),
                           "c_%02d" % (comuna): t_a}
                    # Create the key for the policitical party
                    # inside the target dict
                    dest_dict["partido_%s"
                              % (row["id_partido"])] = t_d
                else:
                    # For every other section
                    # We only need to create a section key
                    # with the candidates array
                    dest_dict["partido_%s"
                              % (row["id_partido"])]["c_%02d" % (comuna)] = t_a
    except KeyError, e:
        log.error("Error processing key reason %s" % (str(e)))
        return False
    except IndexError, e:
        log.error("Error processing index reason %s" % (str(e)))
        return False
    dest_dict["partido_99"]["c_%02d" % (comuna)] = a99
    dest_dict["partido_00"]["c_%02d" % (comuna)] = a00
    return True


def t_sort_results_API(d_d=None):
    ''' sort the results by descending percentage
        taking into account special parties at the bottom'''
    for k, v in d_d.iteritems():
        if k == "resumen": continue
        if k == "partido_00":
            if not sort_results_by_percentage(v, special=True):
                return False
        else:
            if not sort_results_by_percentage(v, special=False):
                return False
    return True


def t_results_API(origin_list=None, dest_dict=None):
    '''main transformation
       we need to switch from section based driven data
       to political party driven data'''
    for i, v in enumerate(origin_list):
        log.debug("transform results for section %s" % (i))
        if not t_results_section_API(v, i, dest_dict):
            return False
        
    # Sort special party results
    # Write to file to preview intermediate result
    to_json("datos_completos",dest_dict)
    if not t_sort_results_API(dest_dict):
        return False
    return True

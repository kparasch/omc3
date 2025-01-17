"""
 :module: twiss_to_lin

 Created on 18/02/18

 :author: Lukas Malina


This module generates the .linx/y (both on-momentum and off-momentum) from two twiss files,
for free motion and for driven motion. The twisses should contain the chromatic functions as well.

"""
from collections import OrderedDict
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import tfs

from omc3.definitions import formats
from omc3.definitions.constants import PLANES

MOTION = dict(free="_f", driven="_d")
PLANE_TO_NUM = dict(X=1, Y=2)
COUPLING_INDICES = dict(X="01", Y="10")
OTHER = dict(X="Y", Y="X")
NOISE = 1e-4
NTURNS = 6600
ACTION = 5e-9
ERRTUNE = 3e-7
NAT_OVER_DRV = 0.01
MAGIC_NUMBER = 6   # SVD cleaning effect + main lobe size effect
COUPLING = 0.1


def optics_measurement_test_files(modeldir, dpps, motion, beam_direction):
    """

    Args:
        modeldir: path to model directory
        dpps: list of required dpp values for simulated lin files

    Returns:

    """
    if beam_direction not in (-1, 1):
        raise ValueError("Beam direction has to be either 1 or -1")
    model, tune, nattune = get_combined_model_and_tunes(modeldir)
    lins = []
    for dpp_value in dpps:
        lins.append(
            generate_lin_files(model, tune, nattune, MOTION[motion],
                               dpp=dpp_value, beam_direction=beam_direction)
        )
    return lins


def generate_lin_files(model, tune, nattune, motion='_d', dpp=0.0, beam_direction=1):
    nbpms = len(model.index.to_numpy())
    lins = {}
    for plane in PLANES:
        lin = model.loc[:, ['NAME', 'S']]
        noise_freq_domain = NOISE / np.sqrt(NTURNS) / MAGIC_NUMBER
        lin['NOISE'] = noise_freq_domain
        lin['CO'] = dpp * model.loc[:, f"D{plane}{motion}"] + np.random.randn(nbpms) * (NOISE / np.sqrt(NTURNS))
        lin['CORMS'] = np.abs(np.random.randn(nbpms) * 3e-6 + 3e-6)  # TODO
        lin['PK2PK'] = 2 * (np.sqrt(model.loc[:, f"BET{plane}{motion}"] * ACTION) + 3 * NOISE)
        lin[f"TUNE{plane}"] = tune[plane] + ERRTUNE * np.random.randn(nbpms)
        lin[f"NATTUNE{plane}"] = nattune[plane] + (ERRTUNE / np.sqrt(NAT_OVER_DRV)) * np.random.randn(nbpms)
        lin[f"MU{plane}"] = np.remainder(model.loc[:, f"MU{plane}{motion}"]
                                         + dpp * model.loc[:, f"DMU{plane}{motion}"]
                                         + (noise_freq_domain / (2 * np.pi)) *np.random.randn(nbpms) + np.random.rand(), 1) * beam_direction
        lin[f"ERRMU{plane}"] = noise_freq_domain / (2 * np.pi)

        lin[f"ERRAMP{plane}"] = noise_freq_domain * np.random.randn(nbpms)

        lin[f"AMP{plane}"] = np.sqrt(model.loc[:, f"BET{plane}{motion}"] * ACTION *
                                     (1 + dpp * np.sin(2 * np.pi * model.loc[:, f"PHI{plane}{motion}"])
                                      * model.loc[:, f"W{plane}{motion}"])) + lin[f"ERRAMP{plane}"]

        lin[f"ERRAMP{plane}"] = np.abs(lin[f"ERRAMP{plane}"])  # * 2  divided by two removed?

        lin[f"NATMU{plane}"] = np.remainder(model.loc[:, f"MU{plane}{MOTION['free']}"]
                                            + (NAT_OVER_DRV * noise_freq_domain / (2 * np.pi)) * np.random.randn(nbpms) + np.random.rand(), 1) * beam_direction

        lin[f"ERRNATAMP{plane}"] = noise_freq_domain * np.random.randn(nbpms)

        lin[f"NATAMP{plane}"] = NAT_OVER_DRV * np.sqrt(ACTION * model.loc[:, f"BET{plane}{MOTION['free']}"]) + lin[f"ERRNATAMP{plane}"]

        lin[f"ERRNATAMP{plane}"] = np.abs(lin[f"ERRNATAMP{plane}"])  # * 2  divided by two removed?

        lin[f"PHASE{COUPLING_INDICES[plane]}"] = np.remainder(model.loc[:, f"MU{OTHER[plane]}{motion}"] + dpp * model.loc[:, f"DMU{OTHER[plane]}{motion}"]
                                                  + (COUPLING * noise_freq_domain / (2 * np.pi)) * np.random.randn(nbpms) + np.random.rand(), 1) * beam_direction
        lin[f"AMP{COUPLING_INDICES[plane]}"] = COUPLING * np.sqrt(ACTION *model.loc[:, f"BET{OTHER[plane]}{motion}"]
                                                  * (1 + dpp * np.sin(model.loc[:, f"PHI{OTHER[plane]}{motion}"]) * model.loc[:, f"W{OTHER[plane]}{motion}"])) + COUPLING * noise_freq_domain * np.random.randn(nbpms)

        # backwards compatibility with drive  TODO remove
        lin[f"AMP{plane}"] = lin.loc[:, f"AMP{plane}"].to_numpy() / 2
        lin[f"NATAMP{plane}"] = lin.loc[:, f"NATAMP{plane}"].to_numpy() / 2

        lins[plane] = tfs.TfsDataFrame(lin, headers=_get_header(tune, nattune, plane)).set_index("NAME", drop=False)
    return lins


def get_combined_model_and_tunes(model_dir: Path):
    free = tfs.read(model_dir / 'twiss.dat')
    driven = tfs.read(model_dir / 'twiss_ac.dat')
    nattune = {"X": np.remainder(free.headers['Q1'], 1), "Y": np.remainder(free.headers['Q2'], 1)}
    tune = {"X": np.remainder(driven.headers['Q1'], 1), "Y": np.remainder(driven.headers['Q2'], 1)}
    model = pd.merge(free, driven, how='inner', on='NAME', suffixes=MOTION.values())
    model['S'] = model.loc[:, 'S_f']
    return model, tune, nattune


def _get_header(tunes, nattunes, plane):
    return {
        f"Q{PLANE_TO_NUM[plane]}": tunes[plane],
        f"Q{PLANE_TO_NUM[plane]}RMS": 1e-7,
        f"NATQ{PLANE_TO_NUM[plane]}": nattunes[plane],
        f"NATQ{PLANE_TO_NUM[plane]}RMS": 1e-6,
        "TIME": datetime.utcnow().strftime(formats.TIME),
    }

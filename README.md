# <img src="https://raw.githubusercontent.com/pylhc/pylhc.github.io/master/docs/assets/logos/OMC_logo.svg" height="28"> 3

[![Tests](https://github.com/pylhc/omc3/actions/workflows/coverage.yml/badge.svg?branch=master)](https://github.com/pylhc/omc3/actions/workflows/coverage.yml)
[![Code Climate coverage](https://img.shields.io/codeclimate/coverage/pylhc/omc3.svg?style=popout)](https://codeclimate.com/github/pylhc/omc3)
[![Code Climate maintainability (percentage)](https://img.shields.io/codeclimate/maintainability-percentage/pylhc/omc3.svg?style=popout)](https://codeclimate.com/github/pylhc/omc3)
[![GitHub last commit](https://img.shields.io/github/last-commit/pylhc/omc3.svg?style=popout)](https://github.com/pylhc/omc3/)
[![GitHub release](https://img.shields.io/github/release/pylhc/omc3.svg?style=popout)](https://github.com/pylhc/omc3/)

This is the python-tool package of the Optics Measurements and Corrections team (OMC) at CERN.

Most of the codes are generic and not limited to CERN accelerators, and the package can easily be used for your favourite circular accelerator.
To see how to adapt this for your machine, see our [documentation](https://pylhc.github.io/omc3/), `Model` section. 
To contribute, see [our guidelines](https://pylhc.github.io/packages/development/contributing/) on the OMC website.

## Documentation

- Autogenerated docs via `Sphinx` can be found at <https://pylhc.github.io/omc3/>.
- General documentation of the OMC Team is located at <https://pylhc.github.io/>.

## Installing

The `omc3` package is `Python 3.7+` compatible, but not yet deployed to `PyPI`.
The best way to install it is through pip from the online `master` branch, which is stable:
```bash
pip install git+https://github.com/pylhc/omc3.git#egg=omc3
```

For development purposes, we recommend creating a new virtual environment and installing from VCS in editable mode with all extra dependencies (`cern` for packages only available in the CERN GPN, `test` for `pytest` and relevant plugins, and `doc` for packages needed to build documentation)
```bash
git clone https://github.com/pylhc/omc3
pip install --editable "omc3[all]"
```

Codes can then be run with either `python -m omc3.SCRIPT --FLAG ARGUMENT` or calling the `.py` file directly.

## Functionality

#### Main Scripts

Main scripts to be executed lie in the [`/omc3`](omc3) directory. These include:
- `global_correction.py` to calculate corrections from measurement files.
- `hole_in_one.py` to perform frequency analysis on turn by turn BPM data and infer optics (and more) for a given accelerator.
- `madx_wrapper.py` to start a `MAD-X` run with a file or string as input.
- `model_creator.py` to generate optics models required for optics analysis.
- `response_creator.py` to provide correction response files.
- `run_kmod.py` to analyse data from K-modulation and return the measured optics functions.
- `tbt_converter.py` to convert different turn by turn datatypes to `SDDS`, potentially adding noise.
- `amplitude_detuning_analysis.py` to perform amp. det. analysis on optics data with tune correction.

#### Plotting Scripts

Plotting scripts for analysis outputs can be found in [`/omc3/plotting`](omc3/plotting):
- `plot_spectrum.py` to generate plots from files generated by frequency analysis.
- `plot_bbq.py` to generate plots from files generated by BBQ analysis.
- `plot_amplitude_detuning.py` to generate plots from files generated by amplitude detuning analysis.
- `plot_optics_measurements.py` to generate plots from files generated by optics_measurements.
- `plot_tfs.py` all purpose tfs-file plotter.

#### Other Scripts

Other general utility scripts are in [`/omc3/scripts`](omc3/scripts):
- `update_nattune_in_linfile.py` to update the natural tune columns in the lin files by finding the highest peak in the spectrum in a given interval.
- `write_madx_macros.py` to generate `MAD-X` tracking macros with observation points from a twiss file.
- `merge_kmod_results.py` to merge lsa_results files created by kmod, and add the luminosity imbalance if the 4 needed IP/Beam files combination are present.
- `fake_measurement_from_model.py` to create a fake measurement based on a model twiss file.
- `betabeatsrc_output_converter.py` to convert outputs from our old codes to `omc3`'s new standardized format.

Example use for these scripts can be found in the [`tests`](tests) files.
Documentation including relevant flags and parameters can be found at <https://pylhc.github.io/omc3/>.

## License

This project is licensed under the `GNU GPLv3` License.
Please take a moment to check its permissivity - see the [LICENSE](LICENSE) file for details.
"""
LHC
---

Accelerator-Class for the ``LHC`` collider.

Model Creation Keyword Args:
    *--Required--*

    - **beam** *(int)*:

        Beam to use.

        choices: ``(1, 2)``


    - **year** *(str)*:

        Year of the optics (or hllhc1.3).

        choices: ``('2012', '2015', '2016', '2017', '2018', 'hllhc1.3')``


    *--Optional--*

    - **ats**:

        Marks ATS optics

        action: ``store_true``


    - **dpp** *(float)*:

        Delta p/p to use.

        default: ``0.0``


    - **driven_excitation** *(str)*:

        Denotes driven excitation by AC-dipole (acd) or by ADT (adt)

        choices: ``('acd', 'adt')``


    - **drv_tunes** *(float)*:

        Driven tunes without integer part.


    - **energy** *(float)*:

        Energy in Tev.


    - **model_dir** *(str)*:

        Path to model directory; loads tunes and excitation from model!


    - **modifiers** *(str)*:

        Path to the optics file to use (modifiers file).


    - **nat_tunes** *(float)*:

        Natural tunes without integer part.


    - **xing**:

        If True, x-ing angles will be applied to model

        action: ``store_true``


"""
import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Iterator, List, Sequence, Tuple

import tfs
from generic_parser import EntryPoint

from omc3.model.accelerators.accelerator import (
    AccElementTypes,
    Accelerator,
    AcceleratorDefinitionError,
    AccExcitationMode,
)
from omc3.model.constants import (
    B2_ERRORS_TFS,
    B2_SETTINGS_MADX,
    GENERAL_MACROS,
    LHC_MACROS,
    MACROS_DIR,
    MODIFIER_TAG,
)
from omc3.utils import logging_tools

LOGGER = logging_tools.get_logger(__name__)
CURRENT_DIR = Path(__file__).parent
LHC_DIR = CURRENT_DIR / "lhc"


class Lhc(Accelerator):
    """
    Parent Class for LHC-types.
    """

    NAME = "lhc"
    RE_DICT: Dict[str, str] = {
        AccElementTypes.BPMS: r"BPM",
        AccElementTypes.MAGNETS: r"M",
        AccElementTypes.ARC_BPMS: r"BPM.*\.0*(1[5-9]|[2-9]\d|[1-9]\d{2,})[RL]",
    }  # bpms > 14 L or R of IP

    LHC_IPS = ("1", "2", "5", "8")
    NORMAL_IP_BPMS = "BPMSW.1{side}{ip}.B{beam}"
    DOROS_IP_BPMS = "LHC.BPM.1{side}{ip}.B{beam}_DOROS"

    @staticmethod
    def get_parameters():
        params = super(Lhc, Lhc).get_parameters()
        params.add_parameter(
            name="beam", type=int, choices=(1, 2), required=True, help="Beam to use."
        )
        params.add_parameter(
            name="year",
            type=str,
            required=True,
            choices=("2012", "2015", "2016", "2017", "2018", "2022", "hllhc1.3"),
            help="Year of the optics (or hllhc1.3).",
        )
        params.add_parameter(name="ats", action="store_true", help="Marks ATS optics")
        return params

    def __init__(self, *args, **kwargs):
        parser = EntryPoint(self.get_parameters(), strict=True)
        opt = parser.parse(*args, **kwargs)
        super().__init__(opt)
        self.correctors_dir = "2012"
        self.year = opt.year
        self.ats = opt.ats
        if self.year == "hllhc1.3":
            self.correctors_dir = "hllhc1.3"
        self.beam = opt.beam
        beam_to_beam_direction = {1: 1, 2: -1}
        self.beam_direction = beam_to_beam_direction[self.beam]
        self.verify_object()

    def verify_object(self) -> None:  # TODO: Maybe more checks?
        """
        Verifies if everything is defined which should be defined.
        Will Raise an ``AcceleratorDefinitionError`` if one of the checks is invalid.
        """
        LOGGER.debug("Accelerator class verification")
        _ = self.beam

        if self.model_dir is None and self.xing is None:
            raise AcceleratorDefinitionError("Crossing on or off not set.")

        if self.excitation is None:
            raise AcceleratorDefinitionError("Excitation mode not set.")
        if (self.excitation != AccExcitationMode.FREE) and (self.drv_tunes is None):
            raise AcceleratorDefinitionError("An excitation mode was given but driven tunes are not set.")

        # TODO: write more output prints
        LOGGER.debug("... verification passed. \nSome information about the accelerator:")
        LOGGER.debug(f"Class name       {self.__class__.__name__}")
        LOGGER.debug(f"Beam             {self.beam}")
        LOGGER.debug(f"Beam direction   {self.beam_direction}")
        if self.modifiers:
            LOGGER.debug(f"Modifiers        {', '.join([str(m) for m in self.modifiers])}")

    @property
    def beam(self) -> int:
        if self._beam is None:
            raise AcceleratorDefinitionError(
                "The accelerator definition is incomplete, beam "
                "has to be specified (--beam option missing?)."
            )
        return self._beam

    @beam.setter
    def beam(self, value) -> None:
        if value not in (1, 2):
            raise AcceleratorDefinitionError("Beam parameter has to be one of (1, 2)")
        self._beam = value

    @staticmethod
    def get_lhc_error_dir() -> Path:
        return LHC_DIR / "systematic_errors"

    def get_variables(self, frm=None, to=None, classes=None):
        correctors_dir = LHC_DIR / "2012" / "correctors"
        all_corrs = _merge_jsons(
            correctors_dir / f"correctors_b{self.beam}" / "beta_correctors.json",
            correctors_dir / f"correctors_b{self.beam}" / "coupling_correctors.json",
            self._get_triplet_correctors_file(),
        )
        my_classes = classes
        if my_classes is None:
            my_classes = all_corrs.keys()
        vars_by_class = set(
            _flatten_list([all_corrs[corr_cls] for corr_cls in my_classes if corr_cls in all_corrs])
        )
        if frm is None and to is None:
            return list(vars_by_class)
        elems_matrix = tfs.read(self._get_corrector_elems()).sort_values("S")
        if frm is not None and to is not None:
            if frm > to:
                elems_matrix = elems_matrix[(elems_matrix.S >= frm) | (elems_matrix.S <= to)]
            else:
                elems_matrix = elems_matrix[(elems_matrix.S >= frm) & (elems_matrix.S <= to)]
        elif frm is not None:
            elems_matrix = elems_matrix[elems_matrix.S >= frm]
        elif to is not None:
            elems_matrix = elems_matrix[elems_matrix.S <= to]

        vars_by_position = _remove_dups_keep_order(
            _flatten_list([raw_vars.split(",") for raw_vars in elems_matrix.loc[:, "VARS"]])
        )
        return _list_intersect_keep_order(vars_by_position, vars_by_class)

    def get_ips(self) -> Iterator[Tuple[str]]:
        """
        Returns an iterable with this accelerator's IPs.

        Returns:
            An iterator returning `tuples` with:
                (``ip name``, ``left BPM name``, ``right BPM name``)
        """
        for ip in Lhc.LHC_IPS:
            yield (
                f"IP{ip}",
                Lhc.NORMAL_IP_BPMS.format(side="L", ip=ip, beam=self.beam),
                Lhc.NORMAL_IP_BPMS.format(side="R", ip=ip, beam=self.beam),
            )
            yield (
                f"IP{ip}_DOROS",
                Lhc.DOROS_IP_BPMS.format(side="L", ip=ip, beam=self.beam),
                Lhc.DOROS_IP_BPMS.format(side="R", ip=ip, beam=self.beam),
            )

    def log_status(self) -> None:
        LOGGER.info(f"  model dir = {self.model_dir}")
        LOGGER.info(f"Natural Tune X      [{self.nat_tunes[0]:10.3f}]")
        LOGGER.info(f"Natural Tune Y      [{self.nat_tunes[1]:10.3f}]")
        LOGGER.info(
            f"Best Knowledge Model     "
            f"[{'NO' if self.model_best_knowledge is None else 'OK':>10s}]"
        )

        if self.excitation == AccExcitationMode.FREE:
            LOGGER.info(f"Excitation          [{'NO':>10s}]")
            return
        LOGGER.info(
            f"Excitation          "
            f"[{'ACD' if self.excitation == AccExcitationMode.ACD else 'ADT':>10s}]"
        )
        LOGGER.info(f"> Driven Tune X     [{self.drv_tunes[0]:10.3f}]")
        LOGGER.info(f"> Driven Tune Y     [{self.drv_tunes[1]:10.3f}]")

    def load_main_seq_madx(self) -> str:
        try:
            return _get_call_main_for_year(self.year)
        except AttributeError:
            raise AcceleratorDefinitionError(
                "The accelerator definition is incomplete, mode "
                "has to be specified (--lhcmode option missing?)."
            )

    # Private Methods ##########################################################

    def _get_triplet_correctors_file(self) -> Path:
        correctors_dir = LHC_DIR / self.correctors_dir / "correctors"
        return correctors_dir / "triplet_correctors.json"

    def _get_corrector_elems(self) -> Path:
        correctors_dir = LHC_DIR / self.correctors_dir / "correctors"
        return correctors_dir / f"corrector_elems_b{self.beam}.tfs"

    def get_exciter_bpm(self, plane: str, commonbpms: List[str]):
        beam = self.beam
        adt = "H.C" if plane == "X" else "V.B"
        l_r = "L" if (beam == 1 != plane == "Y") else "R"
        a_b = "B" if beam == 1 else "A"
        if self.excitation == AccExcitationMode.ACD:
            return (
                _is_one_of_in([f"BPMY{a_b}.6L4.B{beam}", f"BPM.7L4.B{beam}"], commonbpms),
                f"MKQA.6L4.B{beam}",
            )
        if self.excitation == AccExcitationMode.ADT:
            return (
                _is_one_of_in([f"BPMWA.B5{l_r}4.B{beam}", f"BPMWA.A5{l_r}4.B{beam}"], commonbpms),
                f"ADTK{adt}5{l_r}4.B{beam}",
            )
        return None

    def important_phase_advances(self) -> List[List[str]]:
        if self.beam == 2:
            return [["MKD.O5R6.B2", "TCTPH.4R1.B2"], ["MKD.O5R6.B2", "TCTPH.4R5.B2"]]
        if self.beam == 1:
            return [["MKD.O5L6.B1", "TCTPH.4L1.B1"], ["MKD.O5L6.B1", "TCTPH.4L5.B1"]]

    def get_synch_BPMs(self, index):
        # expect passing index.to_numpy()
        if self.beam == 1:
            return [i in index for i in self.model.loc["BPMSW.33L2.B1":].index]
        elif self.beam == 2:
            return [i in index for i in self.model.loc["BPMSW.33R8.B2":].index]

    def get_base_madx_script(self, best_knowledge: bool = False) -> str:
        ats_md = False
        high_beta = False
        ats_suffix = "_ats" if self.ats else ""
        madx_script = (
            # f"option, -echo;\n"
            f"call, file = '{self.model_dir / MACROS_DIR / GENERAL_MACROS}';\n"
            f"call, file = '{self.model_dir / MACROS_DIR / LHC_MACROS}';\n"
            f'title, "LHC Model created by OMC3";\n'
            f"{self.load_main_seq_madx()}\n"
            f"exec, define_nominal_beams();\n"
        )
        madx_script += "".join(
            f"call, file = '{self.model_dir / modifier}'; {MODIFIER_TAG}\n"
            for modifier in self.modifiers
        )
        madx_script += (
            f"exec, cycle_sequences();\n"
            f"xing_angles = {'1' if self.xing else '0'};\n"
            f"if(xing_angles==1){{\n"
            f"    exec, set_crossing_scheme_ON();\n"
            f"}}else{{\n"
            f"    exec, set_default_crossing_scheme();\n"
            f"}}\n"
            f"use, sequence = LHCB{self.beam};\n"
            f"option, echo;\n"
        )
        if best_knowledge:
            # madx_script += f"exec, load_average_error_table({self.energy}, {self.beam});\n"
            madx_script += (
                f"readmytable, file = '{self.model_dir / B2_ERRORS_TFS}', table=errtab;\n"
                f"seterr, table=errtab;\n"
                f"call, file = '{self.model_dir / B2_SETTINGS_MADX}';\n"
            )
        if high_beta:
            madx_script += "exec, high_beta_matcher();\n"

        if self.year == "2018":  # to be checked for 2022 (jdilly, 2021)
            madx_script += f"exec, match_tunes_ats({self.nat_tunes[0]}, {self.nat_tunes[1]}, {self.beam});\n"
        else:
            madx_script += f"exec, match_tunes{ats_suffix}({self.nat_tunes[0]}, {self.nat_tunes[1]}, {self.beam});\n"

        if ats_md:
            madx_script += "exec, full_response_ats();\n"

        madx_script += f"exec, coupling_knob{ats_suffix}({self.beam});\n"
        return madx_script

    def get_update_correction_script(self, outpath: Path, corr_file: Path) -> str:
        madx_script = self.get_base_madx_script()
        madx_script += (
            f"call, file = '{str(corr_file)}';\n"
            f"exec, do_twiss_elements(LHCB{self.beam}, '{str(outpath)}', {self.dpp});\n"
        )
        return madx_script


# General functions ##########################################################


def _get_call_main_for_year(year: str) -> str:
    call_main = f"call, file = '{_get_file_for_year(year, 'main.seq')}';\n"
    if year == "2012":
        call_main += f"call, file = '{LHC_DIR / '2012' / 'install_additional_elements.madx'}';\n"
    if year == "hllhc1.3":
        call_main += f"call, file = '{LHC_DIR / 'hllhc1.3' / 'main_update.seq'}';\n"
    return call_main


def _get_file_for_year(year: str, filename: str) -> Path:
    return LHC_DIR / year / filename


def _merge_jsons(*files) -> dict:
    full_dict = {}
    for json_file in files:
        with open(json_file, "r") as json_data:
            json_dict = json.load(json_data)
            for key in json_dict.keys():
                full_dict[key] = json_dict[key]
    return full_dict


def _flatten_list(my_list: List) -> List:
    return [item for sublist in my_list for item in sublist]


def _remove_dups_keep_order(my_list: List) -> List:
    return list(OrderedDict.fromkeys(my_list))


def _list_intersect_keep_order(primary_list: List, secondary_list: List) -> List:
    return [elem for elem in primary_list if elem in secondary_list]


def _is_one_of_in(bpms_to_find: Sequence[str], bpms: Sequence[str]):
    found_bpms = [bpm for bpm in bpms_to_find if bpm in bpms]
    if len(found_bpms):
        return list(bpms).index(found_bpms[0]), found_bpms[0]
    raise KeyError


class _LhcSegmentMixin:
    def __init__(self):
        self._start = None
        self._end = None

    def get_segment_vars(self, classes=None):
        return self.get_variables(frm=self.start.s, to=self.end.s, classes=classes)

    def verify_object(self) -> None:
        try:
            self.beam
        except AttributeError:
            raise AcceleratorDefinitionError(
                "The accelerator definition is incomplete, beam "
                "has to be specified (--beam option missing?)."
            )
        if self.modifiers is None or not len(self.modifiers):
            raise AcceleratorDefinitionError(
                "The accelerator definition is incomplete, no modifiers could be found."
            )
        if self.xing is None:
            raise AcceleratorDefinitionError("Crossing on or off not set.")
        if self.label is None:
            raise AcceleratorDefinitionError("Segment label not set.")
        if self.start is None:
            raise AcceleratorDefinitionError("Segment start not set.")
        if self.end is None:
            raise AcceleratorDefinitionError("Segment end not set.")

import numpy as np
from ctypes import Structure, POINTER, pointer, c_int, c_void_p
from audioflux.type import CepstralRectifyType, CepstralEnergyType
from audioflux.base import Base
from audioflux.utils import ascontiguous_T

__all__ = ["XXCC"]


class OpaqueXXCC(Structure):
    _fields_ = []


class XXCC(Base):
    """
    Cepstrum coefficients, supports all spectrum types.

    Parameters
    ----------
    num: int
        Number of frequency bins to generate. It must be the same as the
        `num` parameter of the transformation (same as the spectrogram matrix).

    Examples
    --------

    Get a 220Hz's audio file

    >>> import audioflux as af
    >>> sample_path = af.utils.sample_path('220')
    >>> audio_arr, sr = af.read(sample_path)

    Create BFT object and extract mel spectrogram

    >>> import numpy as np
    >>> from audioflux.type import SpectralFilterBankScaleType, SpectralDataType
    >>> bft_obj = af.BFT(num=128, radix2_exp=12, samplate=sr,
    >>>                  scale_type=SpectralFilterBankScaleType.MEL,
    >>>                  data_type=SpectralDataType.POWER)
    >>> spec_arr = bft_obj.bft(audio_arr)
    >>> spec_arr = np.abs(spec_arr)

    Create XXCC object and extract mfcc

    >>> xxcc_obj = af.XXCC(bft_obj.num)
    >>> xxcc_obj.set_time_length(time_length=spec_arr.shape[1])
    >>> mfcc_arr = xxcc_obj.xxcc(spec_arr)

    Display MFCC

    >>> import matplotlib.pyplot as plt
    >>> from audioflux.display import fill_spec
    >>> audio_len = audio_arr.shape[0]
    >>> fig, ax = plt.subplots()
    >>> img = fill_spec(mfcc_arr, axes=ax,
    >>>           x_coords=bft_obj.x_coords(audio_len), x_axis='time',
    >>>           title='MFCC')
    >>> fig.colorbar(img, ax=ax)
    """

    def __init__(self, num):
        super(XXCC, self).__init__(pointer(OpaqueXXCC()))

        self.num = num

        fn = self._lib['xxccObj_new']
        fn.argtypes = [POINTER(POINTER(OpaqueXXCC)), c_int]
        fn(self._obj, c_int(self.num))
        self._is_created = True

    def set_time_length(self, time_length):
        """
        Set time length

        Parameters
        ----------
        time_length: int
        """

        fn = self._lib['xxccObj_setTimeLength']
        fn.argtypes = [
            POINTER(OpaqueXXCC),
            c_int
        ]
        fn(self._obj, c_int(time_length))

    def xxcc(self, m_data_arr, cc_num=13, rectify_type=CepstralRectifyType.LOG):
        """
        Get XX cepstral coefficients.

        Parameters
        ----------
        m_data_arr: np.ndarray [shape=(fre, time)]
            Spectrogram data

        cc_num: int
            xxcc num, usually set to 13, 20 or 40

        rectify_type: CepstralRectifyType

        Returns
        -------
        out: np.ndarray [shape=(cc_num, time)]
        """
        if cc_num > self.num:
            raise ValueError(f'cc_num={cc_num} must be less than num={self.num}')
        m_data_arr = ascontiguous_T(m_data_arr)
        if np.iscomplexobj(m_data_arr):
            m_data_arr = np.abs(m_data_arr)

        fn = self._lib['xxccObj_xxcc']
        fn.argtypes = [
            POINTER(OpaqueXXCC),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=2, flags='C_CONTIGUOUS'),
            c_int,
            POINTER(c_int),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=2, flags='C_CONTIGUOUS')
        ]

        time_len, _ = m_data_arr.shape
        ret = np.zeros((time_len, cc_num), dtype=np.float32)
        fn(self._obj, m_data_arr, c_int(cc_num), pointer(c_int(rectify_type.value)), ret)
        return ascontiguous_T(ret)

    def xxcc_standard(self, m_data_arr, energy_arr, cc_num=13,
                      delta_window_length=9, energy_type=CepstralEnergyType.REPLACE,
                      rectify_type=CepstralRectifyType.LOG):
        """
        Get XX cepstral coefficients standard

        Parameters
        ----------
        m_data_arr: np.ndarray [shape=(fre, time)]
            Spectrogram data
        energy_arr: np.ndarray [shape=(time,]
            energy data
        cc_num: int
            xxcc num, usually set to 13, 20 or 40
        delta_window_length: int
            must odd>=3
        energy_type: CepstralEnergyType
        rectify_type: CepstralRectifyType

        Returns
        -------
        coe_arr: np.ndarray [shape=(cc_num, time) or ()]
        m_delta_arr1: np.ndarray [shape=(cc_num, time) or ()]
        m_delta_arr2: np.ndarray [shape=(cc_num, time) or ()]
        """
        if cc_num > self.num:
            raise ValueError(f'cc_num={cc_num} must be less than num={self.num}')
        if delta_window_length < 3 or delta_window_length % 2 != 1:
            raise ValueError(f'delta_window_length={delta_window_length} must be a strange number greater than 3.')

        m_data_arr = ascontiguous_T(m_data_arr)
        if np.iscomplexobj(m_data_arr):
            m_data_arr = np.abs(m_data_arr)

        fn = self._lib['xxccObj_xxccStandard']
        fn.argtypes = [
            POINTER(OpaqueXXCC),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=2, flags='C_CONTIGUOUS'),
            c_int,
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=1, flags='C_CONTIGUOUS'),
            POINTER(c_int),
            POINTER(c_int),
            POINTER(c_int),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=2, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=2, flags='C_CONTIGUOUS'),
            np.ctypeslib.ndpointer(dtype=np.float32, ndim=2, flags='C_CONTIGUOUS')
        ]

        time_len, _ = m_data_arr.shape
        if energy_type == CepstralEnergyType.APPEND:
            shape = (time_len, cc_num + 1)
        else:
            shape = (time_len, cc_num)

        m_coe_arr = np.zeros(shape, dtype=np.float32)
        m_delta_arr1 = np.zeros(shape, dtype=np.float32)
        m_delta_arr2 = np.zeros(shape, dtype=np.float32)

        fn(self._obj,
           m_data_arr,
           c_int(cc_num),
           energy_arr,
           pointer(c_int(delta_window_length)),
           pointer(c_int(energy_type.value)),
           pointer(c_int(rectify_type.value)),
           m_coe_arr,
           m_delta_arr1,
           m_delta_arr2
           )
        m_coe_arr = ascontiguous_T(m_coe_arr)
        m_delta_arr1 = ascontiguous_T(m_delta_arr1)
        m_delta_arr2 = ascontiguous_T(m_delta_arr2)
        return m_coe_arr, m_delta_arr1, m_delta_arr2

    def __del__(self):
        if self._is_created:
            fn = self._lib['xxccObj_free']
            fn.argtypes = [POINTER(OpaqueXXCC)]
            fn.restype = c_void_p
            fn(self._obj)

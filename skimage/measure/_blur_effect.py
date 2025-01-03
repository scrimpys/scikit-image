import warnings

import numpy as np
import scipy.ndimage as ndi

from ..color import rgb2gray
from ..util import img_as_float

# TODO: when minimum numpy dependency is 1.25 use:
# np..exceptions.AxisError instead of AxisError
# and remove this try-except
try:
    from numpy import AxisError
except ImportError:
    from numpy.exceptions import AxisError


__all__ = ['blur_effect']


def blur_effect(image, h_size=11, channel_axis=None, reduce_func=np.max):
    """Estimate the strength of a blur in an image as a metric.

    Parameters
    ----------
    image : ndarray
        RGB or grayscale nD image. The input image is converted to grayscale
        before computing the blur metric.
    h_size : int, optional
        Size of the re-blurring filter.
    channel_axis : int or None, optional
        If None, the image is assumed to be grayscale (single-channel).
        Otherwise, this parameter indicates which axis of the array
        corresponds to color channels.
    reduce_func : callable, optional
        Function used to calculate the aggregation of blur metrics along all
        axes. If set to None, the entire list is returned, where the i-th
        element is the blur metric along the i-th axis.

    Returns
    -------
    blur : float (0 to 1) or list of floats
        An estimate for the images blurriness in the range [0, 1]. Lower values
        indicate a lower blurriness. `reduce_func` may be used to combine the
        estimates for each dimension into a single value, by default the highest
        estimate is returned.

    Warns
    -----
    RuntimeWarning
        When the blur couldn't be estimated because no edges where detected
        in `image`, e.g., if `image` is uniform. In this case, NaN is returned
        instead of an estimate.

    Notes
    -----
    `h_size` must keep the same value in order to compare results between
    images. Most of the time, the default size (11) is enough. This means that
    the metric can clearly discriminate blur up to an average 11x11 filter; if
    blur is higher, the metric still gives good results but its values tend
    towards an asymptote.

    References
    ----------
    .. [1] Frederique Crete, Thierry Dolmiere, Patricia Ladret, and Marina
       Nicolas "The blur effect: perception and estimation with a new
       no-reference perceptual blur metric" Proc. SPIE 6492, Human Vision and
       Electronic Imaging XII, 64920I (2007)
       https://hal.archives-ouvertes.fr/hal-00232709
       :DOI:`10.1117/12.702790`
    """

    if channel_axis is not None:
        try:
            # ensure color channels are in the final dimension
            image = np.moveaxis(image, channel_axis, -1)
        except AxisError:
            print('channel_axis must be one of the image array dimensions')
            raise
        except TypeError:
            print('channel_axis must be an integer')
            raise
        image = rgb2gray(image)
    n_axes = image.ndim
    image = img_as_float(image)
    shape = image.shape
    B = []

    from ..filters import sobel

    slices = tuple([slice(2, s - 1) for s in shape])
    for ax in range(n_axes):
        filt_im = ndi.uniform_filter1d(image, h_size, axis=ax)
        im_sharp = np.abs(sobel(image, axis=ax))
        im_blur = np.abs(sobel(filt_im, axis=ax))
        T = np.maximum(0, im_sharp - im_blur)
        M1 = np.sum(im_sharp[slices])
        if M1 == 0:
            warnings.warn(
                "Couldn't estimate blur for `image` without edges, "
                "`image` may be uniform, using NaN as a blur metric",
                RuntimeWarning,
                stacklevel=2,
            )
            B.append(np.nan)
        else:
            M2 = np.sum(T[slices])
            B.append(np.abs(M1 - M2) / M1)

    return B if reduce_func is None else reduce_func(B)

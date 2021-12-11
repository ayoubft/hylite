from hylite import HyLibrary, HyData
import numpy as np
from gfit.util import remove_hull

def polynomial(data, degree = 1, method='div'):

    """
    Detrend an image data array using a polynomial fit and np.polyfit( ... ).

    *Arguments*:
     - data = numpy array of the format image[x][y][b].
     - degree = the degree of the polynomial to fit. Default is 2.
     - method = 'divide' or 'subtract'. Default is 'divide'.

    *Returns*:
     - corr = the corrected (detrended) data.
     - trend = the trend that was removed.
    """

    #calculate trend
    y = np.array(data.reshape( -1, data.shape[-1] )) #reshape array so each pixel is a column
    y[np.logical_not(np.isfinite(y))] = 0 #kill NaNs
    _x = np.arange(data.shape[-1])
    fit = np.polynomial.polynomial.polyfit(_x, y.T, degree) # fit polynomial
    t = np.polynomial.polynomial.polyval(_x, fit) # evaluate it

    #apply correction
    if 'div' in method:
        y /= t
    elif 'sub' in method.lower():
        y -= t
        y += np.min(y) #map to positive

    return y.reshape(data.shape), t.reshape(data.shape)


def get_hull_corrected(data, band_range=None, method='div', smooth=0, vb=True):
    """
    Apply a hull correction to an entire HyData instance (HyImage, HyCloud or HyLibrary). Returns a corrected copy of
    the input dataset.

    *Arguments*:
     - data = a numpy array or HyData instance to detrend.
     - band_range = Tuple containing the (min,max) band indices or wavelengths to run the correction between. If None
                     (default) then the correction is run of the entire range. Only works if data is a HyData instance.
     - method = Trend removal method: 'divide' or 'subtract'. Default is 'divide'.
     - smooth = the window size of a smoothing median-filter to apply before extracting the hull. Note that this can allow
                hull corrected values to be > 1. Default is 0 (no smoothing). Todo - implement this!
     - vb = True if this should print output.
    """

    if isinstance(data, HyData):

        # create copy containing the bands of interest
        if band_range is None:
            band_range = (0, -1)
        else:
            band_range = (data.get_band_index(band_range[0]), data.get_band_index(band_range[1]))
        corrected = data.export_bands(band_range)

        # convert integer data to floating point (we need floats for the hull correction)
        comp = False
        if corrected.is_int():
            if np.nanmax( corrected.data ) > 100: # check large number used in compressed form
                corrected.decompress()
            else:
                corrected.data = corrected.data.astype(np.float32) # cast to float for hull correction
            comp = True

        # get valid pixels
        D = corrected.get_raveled()
        nan = corrected.header.get_data_ignore_value()
    else:
        shape = data.shape
        D = data.reshape((-1, shape[-1]))
        nan = np.inf

    valid = (np.isfinite(D) & (D != nan)).all(axis=1)  # drop nans/no-data values
    valid = valid & (D != D[:, 0][:, None]).any(axis=1)  # drop flat spectra (e.g. all zeros)
    if len(valid) == 0:
        return corrected  # quick exit for empty images

    # do hull correction
    X = remove_hull( D[valid],upper=True, div=('div' in method), vb=vb)
    D[valid] = X  # copy data back into original array

    # do housekeeping and return
    if isinstance(data, HyData):
        if isinstance(corrected, HyLibrary):
            corrected.upper = None # reset upper and lower limits as these will now be incorrect
            corrected.lower = None # reset upper and lower limits as these will now be incorrect
        corrected.set_raveled(D)
        # convert back to integer if need be
        if comp:
            corrected.compress()
        return corrected
    else:
        return D.reshape( shape )
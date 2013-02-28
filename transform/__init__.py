import numpy as np

from functools import partial

from matplotlib.mlab import specgram
from scipy.stats import skew

from sklearn.base import BaseEstimator
from sklearn.base import TransformerMixin
from sklearn.decomposition import PCA

import IPython


class SpectrogramTransformer(BaseEstimator, TransformerMixin):
    """Creates a flattened spectrogram representation of X.

    Arguments
    ---------
    Fs : int
        The nr. of frames.
    pad_to : int or None
        The number of points to which the data segment is padded when
        performing the FFT. If None same as ``NFFT``.
    NFFT : int
        The number of data points used in each block for the FFT.
    noverlap : int
        overlap of sliding windows - must be smaller than NFFT.
        The higher the smoother but the more comp intensive.
    clip_upper : float
        Clip frequencies higher than ``clip_upper``.
    clip_lower : float
        Clip frequencies lower than ``clip_lower``.
    dtype : np.dtype
        The dtype of the resulting array.
    whiten : int or None
        Whether to whiten the spectrogram or not.
        If whiten is not None its an int holding the number
        of components.
    """

    def __init__(self, Fs=2000, pad_to=None, NFFT=256, noverlap=200,
                 clip_upper=1000.0, clip_lower=0.0, dtype=np.float32,
                 whiten=None, log=True, flatten=True):
        self.Fs = Fs
        self.pad_to = pad_to
        self.NFFT = NFFT
        if noverlap < 1:
            noverlap = int(NFFT * noverlap)
        self.noverlap = noverlap
        self.clip_upper = clip_upper
        self.clip_lower = clip_lower
        self.dtype = dtype
        self.whiten = whiten
        self.log = log
        self.flatten = flatten

    def fit(self, X, y=None, **fit_args):
        return self

    def transform(self, X):
        X_prime = None
        for i, X_i in enumerate(X):
            s = specgram(X_i, NFFT=self.NFFT, Fs=self.Fs, pad_to=self.pad_to,
                         noverlap=self.noverlap)
            Pxx = s[0]
            if self.log:
                Pxx = 10. * np.log10(Pxx)
            #Pxx = np.flipud(Pxx)
            if self.clip_upper < 1000.0:
                freqs = s[1]
                n_fx = freqs.searchsorted(self.clip_upper, side='right')
                Pxx = Pxx[:n_fx]
            if self.clip_lower > 0.0:
                freqs = s[1]
                n_fx = freqs.searchsorted(self.clip_lower, side='left')
                Pxx = Pxx[n_fx:]

            if self.whiten:
                pca = PCA(n_components=self.whiten, whiten=True)
                Pxx = pca.fit_transform(Pxx)

            if X_prime is None:
                if self.flatten:
                    X_prime = np.empty((X.shape[0], Pxx.size), self.dtype)
                else:
                    X_prime = np.empty((X.shape[0], Pxx.shape[0],
                                        Pxx.shape[1]), self.dtype)

            if self.flatten:
                Pxx = Pxx.flatten()
                X_prime[i, :] = Pxx
            else:
                X_prime[i, :, :] = Pxx
        return X_prime


class FlattenTransformer(BaseEstimator, TransformerMixin):

    def __init__(self, scale=1.0):
        self.scale = scale

    def fit(self, X, y=None, **fit_args):
        return self

    def transform(self, X):
        out = np.empty((X.shape[0], X.shape[1] * X.shape[2]), dtype=np.float32)
        for i, X_i in enumerate(X):
            out[i, :] = X_i.flatten()

        out *= self.scale
        return out


class SpectrogramStatsTransformer(BaseEstimator, TransformerMixin):
    """Creates summary statistics from the spectrogram representation of X.

    Arguments
    ---------

    """
    def __init__(self, axis=1, delta=False, delta_delta=False):
        def percentile(a, axis=0, p=50):
            return np.percentile(a, p, axis=axis)

        self.stats = [np.min, np.max,
                      np.mean, np.var,
                      np.median,
                      ]
        self.axis = axis
        self.delta = delta
        self.delta_delta = delta_delta

    def fit(self, X, y=None, **fit_args):
        return self

    def transform(self, X):
        n_stats = len(self.stats)
        if self.axis == 0:
            n_bins = X.shape[2]
        elif self.axis == 1:
            n_bins = X.shape[1]

        if self.delta:
            n_delta = n_bins - 1
            n_bins += n_delta
        if self.delta_delta:
            n_delta_delta = n_delta - 1
            n_bins += n_delta_delta

        out = np.empty((X.shape[0], n_stats * n_bins),
                       dtype=np.float32)
        for i in xrange(X.shape[0]):
            X_i = X[i]
            for j, stat in enumerate(self.stats):
                vals = stat(X_i, axis=self.axis)
                if self.delta:
                    delta = np.diff(vals)
                    vals = np.r_[vals, delta]
                if self.delta_delta:
                    delta_delta = np.diff(delta)
                    vals = np.r_[vals, delta_delta]
                out[i, n_bins * j: n_bins * (j + 1)] = vals
        return out


StatsTransformer = SpectrogramStatsTransformer

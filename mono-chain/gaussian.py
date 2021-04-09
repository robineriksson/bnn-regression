import numpy as np
import numpy.random as rng
import scipy.stats
import scipy.misc
#from itertools import izip

#import helper



class Gaussian:
    """Implements a gaussian pdf. Focus is on efficient multiplication, division and sampling."""

    def __init__(self, m=None, P=None, U=None, S=None, Pm=None):
        """
        Initialize a gaussian pdf given a valid combination of its parameters. Valid combinations are:
        m-P, m-U, m-S, Pm-P, Pm-U, Pm-S
        :param m: mean
        :param P: precision =
        :param U: upper triangular precision factor such that U'U = P
        :param S: covariance
        :param Pm: precision times mean such that P*m = Pm
        """

        if m is not None:
            m = np.asarray(m)
            self.m = m
            self.ndim = m.size

            if P is not None:
                P = np.asarray(P)
                L = np.linalg.cholesky(P)
                self.P = P
                self.C = np.linalg.inv(L)
                self.S = np.dot(self.C.T, self.C)
                self.Pm = np.dot(P, m)
                self.logdetP = 2.0 * np.sum(np.log(np.diagonal(L)))

            elif U is not None:
                U = np.asarray(U)
                self.P = np.dot(U.T, U)
                self.C = np.linalg.inv(U.T)
                self.S = np.dot(self.C.T, self.C)
                self.Pm = np.dot(self.P, m)
                self.logdetP = 2.0 * np.sum(np.log(np.diagonal(U)))

            elif S is not None:
                S = np.asarray(S)
                self.P = np.linalg.inv(S)
                self.C = np.linalg.cholesky(S).T
                self.S = S
                self.Pm = np.dot(self.P, m)
                self.logdetP = -2.0 * np.sum(np.log(np.diagonal(self.C)))

            else:
                raise ValueError('Precision information missing.')

        elif Pm is not None:
            Pm = np.asarray(Pm)
            self.Pm = Pm
            self.ndim = Pm.size

            if P is not None:
                P = np.asarray(P)
                L = np.linalg.cholesky(P)
                self.P = P
                self.C = np.linalg.inv(L)
                self.S = np.dot(self.C.T, self.C)
                self.m = np.linalg.solve(P, Pm)
                self.logdetP = 2.0 * np.sum(np.log(np.diagonal(L)))

            elif U is not None:
                U = np.asarray(U)
                self.P = np.dot(U.T, U)
                self.C = np.linalg.inv(U.T)
                self.S = np.dot(self.C.T, self.C)
                self.m = np.linalg.solve(self.P, Pm)
                self.logdetP = 2.0 * np.sum(np.log(np.diagonal(U)))

            elif S is not None:
                S = np.asarray(S)
                self.P = np.linalg.inv(S)
                self.C = np.linalg.cholesky(S).T
                self.S = S
                self.m = np.dot(S, Pm)
                self.logdetP = -2.0 * np.sum(np.log(np.diagonal(self.C)))
            else:
                raise ValueError('Precision information missing.')

        else:
            raise ValueError('Mean information missing.')

    def gen(self, n_samples=1):
        """Returns independent samples from the gaussian."""

        z = rng.randn(n_samples, self.ndim)
        samples = np.dot(z, self.C) + self.m

        return samples

    def eval(self, x, ii=None, log=True):
        """
        Evaluates the gaussian pdf.
        :param x: rows are inputs to evaluate at
        :param ii: a list of indices specifying which marginal to evaluate. if None, the joint pdf is evaluated
        :param log: if True, the log pdf is evaluated
        :return: pdf or log pdf
        """

        if ii is None:
            xm = x - self.m
            lp = -np.sum(np.dot(xm, self.P) * xm, axis=1)
            lp += self.logdetP - self.ndim * np.log(2.0 * np.pi)
            lp *= 0.5

        else:
            m = self.m[ii]
            S = self.S[ii][:, ii]
            lp = scipy.stats.multivariate_normal.logpdf(x, m, S)
            lp = np.array([lp]) if x.shape[0] == 1 else lp

        res = lp if log else np.exp(lp)
        return res

    def __mul__(self, other):
        """Multiply with another gaussian."""

        assert isinstance(other, Gaussian)

        P = self.P + other.P
        Pm = self.Pm + other.Pm

        return Gaussian(P=P, Pm=Pm)

    def __imul__(self, other):
        """Incrementally multiply with another gaussian."""

        assert isinstance(other, Gaussian)

        res = self * other

        self.m = res.m
        self.P = res.P
        self.C = res.C
        self.S = res.S
        self.Pm = res.Pm
        self.logdetP = res.logdetP

        return res

    def __div__(self, other):
        """Divide by another gaussian. Note that the resulting gaussian might be improper."""

        assert isinstance(other, Gaussian)

        P = self.P - other.P
        Pm = self.Pm - other.Pm

        return Gaussian(P=P, Pm=Pm)

    def __idiv__(self, other):
        """Incrementally divide by another gaussian. Note that the resulting gaussian might be improper."""

        assert isinstance(other, Gaussian)

        res = self / other

        self.m = res.m
        self.P = res.P
        self.C = res.C
        self.S = res.S
        self.Pm = res.Pm
        self.logdetP = res.logdetP

        return res

    def __pow__(self, power, modulo=None):
        """Raise gaussian to a power and get another gaussian."""

        P = power * self.P
        Pm = power * self.Pm

        return Gaussian(P=P, Pm=Pm)

    def __ipow__(self, power):
        """Incrementally raise gaussian to a power."""

        res = self ** power

        self.m = res.m
        self.P = res.P
        self.C = res.C
        self.S = res.S
        self.Pm = res.Pm
        self.logdetP = res.logdetP

        return res

    def kl(self, other):
        """Calculates the kl divergence from this to another gaussian, i.e. KL(this | other)."""

        assert isinstance(other, Gaussian)
        assert self.ndim == other.ndim

        t1 = np.sum(other.P * self.S)

        m = other.m - self.m
        t2 = np.dot(m, np.dot(other.P, m))

        t3 = self.logdetP - other.logdetP

        t = 0.5 * (t1 + t2 + t3 - self.ndim)

        return tray(P)
          
    def gen(self, n_samples=1):
        """Returns independent samples from the gaussian."""

        z = rng.randn(n_samples, self.ndim)
        samples = np.dot(z, self.C) + self.m

        return samples

    def eval(self, x, ii=None, log=True):
        """
        Evaluates the gaussian pdf.
        :param x: rows are inputs to evaluate at
        :param ii: a list of indices specifying which marginal to evaluate. if None, the joint pdf is evaluated
        :param log: if True, the log pdf is evaluated
        :return: pdf or log pdf
        """

        if ii is None:
            xm = x - self.m
            lp = -np.sum(np.dot(xm, self.P) * xm, axis=1)
            lp += self.logdetP - self.ndim * np.log(2.0 * np.pi)
            lp *= 0.5

        else:
            m = self.m[ii]
            S = self.S[ii][:, ii]
            lp = scipy.stats.multivariate_normal.logpdf(x, m, S)
            lp = np.array([lp]) if x.shape[0] == 1 else lp

        res = lp if log else np.exp(lp)
        return res

    def __mul__(self, other):
        """Multiply with another gaussian."""

        assert isinstance(other, Gaussian)

        P = self.P + other.P
        Pm = self.Pm + other.Pm

        return Gaussian(P=P, Pm=Pm)

    def __imul__(self, other):
        """Incrementally multiply with another gaussian."""

        assert isinstance(other, Gaussian)

        res = self * other

        self.m = res.m
        self.P = res.P
        self.C = res.C
        self.S = res.S
        self.Pm = res.Pm
        self.logdetP = res.logdetP

        return res

    def __div__(self, other):
        """Divide by another gaussian. Note that the resulting gaussian might be improper."""

        assert isinstance(other, Gaussian)

        P = self.P - other.P
        Pm = self.Pm - other.Pm

        return Gaussian(P=P, Pm=Pm)

    def __idiv__(self, other):
        """Incrementally divide by another gaussian. Note that the resulting gaussian might be improper."""

        assert isinstance(other, Gaussian)

        res = self / other

        self.m = res.m
        self.P = res.P
        self.C = res.C
        self.S = res.S
        self.Pm = res.Pm
        self.logdetP = res.logdetP

        return res

    def __pow__(self, power, modulo=None):
        """Raise gaussian to a power and get another gaussian."""

        P = power * self.P
        Pm = power * self.Pm

        return Gaussian(P=P, Pm=Pm)

    def __ipow__(self, power):
        """Incrementally raise gaussian to a power."""

        res = self ** power

        self.m = res.m
        self.P = res.P
        self.C = res.C
        self.S = res.S
        self.Pm = res.Pm
        self.logdetP = res.logdetP

        return res

    def kl(self, other):
        """Calculates the kl divergence from this to another gaussian, i.e. KL(this | other)."""

        assert isinstance(other, Gaussian)
        assert self.ndim == other.ndim

        t1 = np.sum(other.P * self.S)

        m = other.m - self.m
        t2 = np.dot(m, np.dot(other.P, m))

        t3 = self.logdetP - other.logdetP

        t = 0.5 * (t1 + t2 + t3 - self.ndim)

        return t
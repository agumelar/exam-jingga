"""Pytest fixtures and Python 3.14 compatibility patches."""
import copy
from django.template.context import BaseContext


def _patched_basecontext_copy(self):
    cls = self.__class__
    duplicate = cls.__new__(cls)
    duplicate.__dict__.update(self.__dict__)
    duplicate.dicts = self.dicts[:]
    return duplicate


# Apply Python 3.14 copy(super()) compatibility fix for Django BaseContext
BaseContext.__copy__ = _patched_basecontext_copy

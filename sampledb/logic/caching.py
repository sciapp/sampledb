# coding: utf-8
"""

"""
import functools
import typing

import flask

_T = typing.TypeVar('_T')


def cache_per_request(key: typing.Optional[typing.Callable[..., typing.Any]] = None) -> typing.Callable[..., typing.Any]:
    def decorator(function: typing.Callable[..., _T]) -> typing.Callable[..., _T]:
        @functools.wraps(function)
        def wrapper(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
            if not hasattr(flask.g, 'cache'):
                flask.g.cache = {}
            cached_func = flask.g.cache.get(function, None)
            if cached_func is None:
                flask.g.cache[function] = {}
                cached_func = flask.g.cache[function]

            if key:
                dict_key = key(*args, **kwargs)
            else:
                dict_key = make_key(*args, **kwargs)

            if dict_key in cached_func:
                return cached_func[dict_key]

            res = function(*args, **kwargs)
            cached_func[dict_key] = res
            return res
        return wrapper
    return decorator


def make_key(
        *args: typing.Any,
        **kwargs: typing.Any
) -> typing.Tuple[
    typing.Tuple[typing.Any, ...],
    typing.FrozenSet[
        typing.Tuple[str, typing.Any]
    ]
]:
    return args, frozenset(kwargs.items())

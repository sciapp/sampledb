# coding: utf-8
"""

"""
import functools
import typing
from collections.abc import Callable

import flask


class _CachingFunctionProtocol[**P, T](typing.Protocol):
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        ...

    def clear_cache(self, key: typing.Any = None) -> None:
        ...


def cache_per_request[**P, T](key: Callable[..., typing.Any] | None = None) -> Callable[[Callable[P, T]], _CachingFunctionProtocol[P, T]]:
    def decorator(function: Callable[P, T]) -> _CachingFunctionProtocol[P, T]:
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
                return typing.cast(T, cached_func[dict_key])

            res = function(*args, **kwargs)
            cached_func[dict_key] = res
            return res

        def clear_cache(key: typing.Optional[typing.Any] = None) -> None:
            if hasattr(flask.g, 'cache') and function in flask.g.cache:
                if key is None:
                    del flask.g.cache[function]
                elif key in flask.g.cache[function]:
                    del flask.g.cache[function][key]

        caching_wrapper = typing.cast(_CachingFunctionProtocol[P, T], wrapper)

        caching_wrapper.clear_cache = clear_cache  # type: ignore[method-assign]

        return caching_wrapper
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

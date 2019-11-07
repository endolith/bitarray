"""
Useful utilities for working with bitarrays.

Not sure if I should put this into the bitarray package itself :-/
"""
import sys
import binascii

from bitarray import bitarray, frozenbitarray, bits2bytes


__all__ = ['zeros', 'rindex', 'strip',
           'ba2hex', 'hex2ba', 'ba2int', 'int2ba']


is_py2 = bool(sys.version_info[0] == 2)


def zeros(length, endian='big'):
    """zeros(length, /, endian='big') -> bitarray

Create a bitarray of length, with all values 0.
"""
    if not isinstance(length, (int, long) if is_py2 else int):
        raise TypeError("integer expected")
    if length < 0:
        raise ValueError("non-negative integer expected")

    a = bitarray(length, endian)
    a.setall(0)
    return a


def rindex(a, value=True):
    """rindex(bitarray, value=True, /) -> int

Return the rightmost index of bool(value).
Raises ValueError is value is not present.
"""
    # We use a simple bisection method here, which is still a lot faster
    # than searching one-by-one from the right in Python.
    value = bool(value)
    if value not in a:
        raise ValueError("rindex(bitarray, x): x not in bitarray")
    left, right = 0, len(a)
    while a[right - 1] != value:
        middle = (left + right) // 2
        try:
            a.index(value, middle, right)
            # upper half has value, so use middle as new left
            left = middle
        except ValueError:
            # uppler half has no valueerror, so it must be lower
            right = middle
    return right - 1


def strip(a, mode='right'):
    """strip(bitarray, mode='right', /) -> bitarray

Strip zeros from left, right or both ends.
Allowed values for mode are: 'left', 'right', 'both'
"""
    if not isinstance(a, (bitarray, frozenbitarray)):
        raise TypeError("bitarray expected")
    if not isinstance(mode, str):
        raise TypeError("string expected for mode")
    if mode not in ('left', 'right', 'both'):
        raise ValueError("allowed values 'left', 'right', 'both', got: %r" %
                         mode)
    first = 0
    if mode in ('left', 'both'):
        try:
            first = a.index(1)
        except ValueError:
            return bitarray(endian=a.endian())

    last = len(a) - 1
    if mode in ('right', 'both'):
        try:
            last = rindex(a)
        except ValueError:
            return bitarray(endian=a.endian())

    return a[first:last + 1]


def count_n(a, n):
    """count_n(bitarray, n, /) -> int

Find the smallest index i for which a.count(1, 0, i) == n.
"""
    if not isinstance(a, (bitarray, frozenbitarray)):
        raise TypeError("bitarray expected")
    if not isinstance(n, (int, long) if is_py2 else int):
        raise TypeError("integer expected")
    if n < 0:
        raise ValueError("non-negative integer expected")
    if n == 0:
        return 0
    total_count = a.count(1)
    if n > total_count:
        raise ValueError("n exceeds total count of %r" % total_count)

    cache = {0: 0, len(a): total_count}
    def cached_count(m, extra=''):
        "return count up to m"
        try:
            return cache[m]
        except KeyError:
            # find the closest cashed value
            below = max(k for k in cache.keys() if k < m)
            above = min(k for k in cache.keys() if k > m)
            if m - below < above - m:
                cache[m] = cache[below] + a.count(1, below, m)
            else:
                cache[m] = cache[above] - a.count(1, m, above)
            return cache[m]

    # starting values: note that the left index has to be at least n
    left, right = n, len(a)
    while not (cached_count(right) == n and a[right - 1]):
        middle = (left + right) // 2
        if cached_count(middle) < n:
            left = middle
        else:
            right = middle
    return right


def ba2hex(a):
    """ba2hex(bitarray, /) -> hexstr

Return a bytes object containing with hexadecimal representation of
the bitarray (which has to be multiple of 4 in length).
"""
    if not isinstance(a, (bitarray, frozenbitarray)):
        raise TypeError("bitarray expected")
    if a.endian() != 'big':
        raise ValueError("big-endian bitarray expected")
    la = len(a)
    if la % 4:
        raise ValueError("bitarray length not multiple of 4")
    if la % 8:
        # make sure we don't mutate the original argument
        a = a + bitarray(4, 'big')
    assert len(a) % 8 == 0

    s = binascii.hexlify(a.tobytes())
    if la % 8:
        s = s[:-1]
    return s


def hex2ba(s):
    """hex2ba(hexstr, /) -> bitarray

Bitarray of hexadecimal representation.
hexstr may contain any number of hex digits (upper or lower case).
"""
    if not isinstance(s, (str, bytes)):
        raise TypeError("string expected")

    ls = len(s)
    if ls % 2:
        s = s + ('0' if isinstance(s, str) else b'0')
    assert len(s) % 2 == 0

    a = bitarray(endian='big')
    a.frombytes(binascii.unhexlify(s))
    if ls % 2:
        del a[-4:]
    return a


def ba2int(a):
    """ba2int(bitarray, /) -> int

Convert the given bitarray into an integer.
The bit-endianness of the bitarray is respected.
"""
    if not isinstance(a, (bitarray, frozenbitarray)):
        raise TypeError("bitarray expected")
    if not a:
        raise ValueError("non-empty bitarray expected")

    endian = a.endian()
    big_endian = bool(endian == 'big')
    if len(a) % 8:
        # pad with leading zeros, such that length is multiple of 8
        if big_endian:
            a = zeros(8 - len(a) % 8, 'big') + a
        else:
            a = a + zeros(8 - len(a) % 8, 'little')
    assert len(a) % 8 == 0
    b = a.tobytes()

    if is_py2:
        c = bytearray(b)
        res = 0
        j = len(c) - 1 if big_endian else 0
        for x in c:
            res |= x << 8 * j
            j += -1 if big_endian else 1
        return res
    else: # py3
        return int.from_bytes(b, byteorder=endian)


def int2ba(i, length=None, endian='big'):
    """int2ba(int, /, length=None, endian='big') -> bitarray

Convert the given integer into a bitarray (with given endianness,
and no leading (big-endian) / trailing (little-endian) zeros).
If length is provided, the result will be of this length, and an
OverflowError will be raised, if the integer cannot be represented
within length bits.
"""
    if not isinstance(i, (int, long) if is_py2 else int):
        raise TypeError("integer expected")
    if i < 0:
        raise ValueError("non-negative integer expected")
    if length is not None:
        if not isinstance(length, int):
            raise TypeError("integer expected for length")
        if length <= 0:
            raise ValueError("integer larger than 0 expected for length")
    if not isinstance(endian, str):
        raise TypeError("string expected for endian")
    if endian not in ('big', 'little'):
        raise ValueError("endian can only be 'big' or 'little'")

    if i == 0:
        # there a special cases for 0 which we'd rather not deal with below
        return zeros(length or 1, endian=endian)

    big_endian = bool(endian == 'big')
    if is_py2:
        c = bytearray()
        while i:
            i, r = divmod(i, 256)
            c.append(r)
        if big_endian:
            c.reverse()
        b = bytes(c)
    else: # py3
        b = i.to_bytes(bits2bytes(i.bit_length()), byteorder=endian)

    a = bitarray(endian=endian)
    a.frombytes(b)
    la = len(a)
    if la == length:
        return a

    if length is None:
        return strip(a, 'left' if big_endian else 'right')

    if la > length:
        size = (la - a.index(1)) if big_endian else (rindex(a) + 1)
        if size > length:
            raise OverflowError("cannot represent %d bit integer in "
                                "%d bits" % (size, length))
        a = a[la - length:] if big_endian else a[:length - la]

    if la < length:
        if big_endian:
            a = zeros(length - la, 'big') + a
        else:
            a += zeros(length - la, 'little')

    assert len(a) == length
    return a
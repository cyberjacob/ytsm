import os
import os.path
import re
from configparser import Interpolation, NoSectionError, NoOptionError, InterpolationMissingOptionError, \
    InterpolationDepthError, InterpolationSyntaxError

MAX_INTERPOLATION_DEPTH = 10


class ExtendedInterpolatorWithEnv(Interpolation):
    """Advanced variant of interpolation, supports the syntax used by
    `zc.buildout'. Enables interpolation between sections.

    This modified version also allows specifying environment variables
    using ${env:...}, and allows adding additional options using 'set_additional_options'. """

    _KEYCRE = re.compile(r"\${([^}]+)\}")

    def before_get(self, parser, section, option, value, defaults):
        accum = []
        self._interpolate_some(parser, option, accum, value, section, defaults, 1)
        return ''.join(accum)

    def before_set(self, parser, section, option, value):
        tmp_value = value.replace('$$', '')  # escaped dollar signs
        tmp_value = self._KEYCRE.sub('', tmp_value)  # valid syntax
        if '$' in tmp_value:
            raise ValueError("invalid interpolation syntax in %r at "
                             "position %d" % (value, tmp_value.find('$')))
        return value

    @staticmethod
    def _resolve_option(option, defaults):
        return defaults[option]

    @staticmethod
    def _resolve_section_option(section, option, parser):
        if section == 'env':
            return os.getenv(option, '')
        return parser.get(section, parser.optionxform(option), raw=True)

    def _interpolate_some(self, parser, option, accum, rest, section, options,
                          depth):
        rawval = parser.get(section, option, raw=True, fallback=rest)
        if depth > MAX_INTERPOLATION_DEPTH:
            raise InterpolationDepthError(option, section, rawval)
        while rest:
            p = rest.find("$")
            if p < 0:
                accum.append(rest)
                return
            if p > 0:
                accum.append(rest[:p])
                rest = rest[p:]
            # p is no longer used
            c = rest[1:2]
            if c == "$":
                accum.append("$")
                rest = rest[2:]
            elif c == "{":
                m = self._KEYCRE.match(rest)
                if m is None:
                    raise InterpolationSyntaxError(option, section,
                                                   "bad interpolation variable reference %r" % rest)
                path = m.group(1).split(':')
                rest = rest[m.end():]
                sect = section

                try:
                    if len(path) == 1:
                        opt = parser.optionxform(path[0])
                        v = self._resolve_option(opt, options)
                    elif len(path) == 2:
                        sect = path[0]
                        opt = path[1]
                        v = self._resolve_section_option(sect, opt, parser)
                    else:
                        raise InterpolationSyntaxError(
                            option, section,
                            "More than one ':' found: %r" % (rest,))
                except (KeyError, NoSectionError, NoOptionError):
                    raise InterpolationMissingOptionError(
                        option, section, rawval, ":".join(path)) from None
                if "$" in v:
                    self._interpolate_some(parser, opt, accum, v, sect,
                                           dict(parser.items(sect, raw=True)),
                                           depth + 1)
                else:
                    accum.append(v)
            else:
                raise InterpolationSyntaxError(
                    option, section,
                    "'$' must be followed by '$' or '{', "
                    "found: %r" % (rest,))

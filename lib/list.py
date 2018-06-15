# coding=UTF-8
from __future__ import unicode_literals


def list_unify_in_order(options_list):
    """
    Return a reduced unified list of items from the given list of options while
    keeping the original order of items mostly intact.
    """
    result = []

    def _scan(options, index, direction):
        while True:
            index += direction

            if index < 0 or index > len(options) - 1:
                break

            try:
                return result.index(options[index])
            except ValueError:
                pass

        raise ValueError

    def _process_options(options_list):
        deferred = []
        connected = False
        for options in options_list:
            for i, option in enumerate(options):
                # option already processed
                if option in result:
                    continue

                try:
                    # scan upwards and insert after
                    index = _scan(options, i, -1)
                    result.insert(index + 1, option)
                    connected = True
                except ValueError:
                    try:
                        # scan downwards and insert before
                        index = _scan(options, i, 1)
                        result.insert(index, option)
                        connected = True
                    except ValueError:
                        # not able to connect
                        if result:
                            deferred.append(options)
                        else:
                            result.extend(options)

                        break

        if deferred:
            if connected:
                # process deferred options
                _process_options(deferred)
            else:
                # done, simply add remaining items to bottom
                for options in deferred:
                    for option in options:
                        if option not in result:
                            result.append(option)

    # collect result
    _process_options(options_list)

    return result
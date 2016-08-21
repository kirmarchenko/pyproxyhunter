# -*- coding: utf-8 -*-
import sys

from tqdm import tqdm, TqdmDeprecationWarning


class ModifiedTqdmProgressbar(tqdm):
    def __init__(self, proxy_list, **kwargs):
        super(ModifiedTqdmProgressbar, self).__init__(**kwargs)
        self.proxy_list = proxy_list

    def get_number_of_good_proxies(self):
        return len(self.proxy_list)

    def update(self, n=1):
        # Overriding this method to print number of good proxies already found.
        """
        Manually update the progress bar, useful for streams
        such as reading files.

        Parameters
        ----------
        n  : int
            Increment to add to the internal counter of iterations
            [default: 1].
        """
        if self.disable:
            return

        if n < 0:
            raise ValueError("n ({0}) cannot be negative".format(n))
        self.n += n

        if self.n - self.last_print_n >= self.miniters:
            # We check the counter first, to reduce the overhead of time()
            delta_t = self._time() - self.last_print_t
            if delta_t >= self.mininterval:
                cur_t = self._time()
                delta_it = self.n - self.last_print_n  # should be n?
                elapsed = cur_t - self.start_t
                # EMA (not just overall average)
                if self.smoothing and delta_t:
                    self.avg_time = delta_t / delta_it \
                        if self.avg_time is None \
                        else self.smoothing * delta_t / delta_it + \
                             (1 - self.smoothing) * self.avg_time

                if not hasattr(self, "sp"):
                    raise TqdmDeprecationWarning("""\
Please use `tqdm_gui(...)` instead of `tqdm(..., gui=True)`
""", fp_write=getattr(self.fp, 'write', sys.stderr.write))

                if self.pos:
                    self.moveto(self.pos)

                # Print bar's update
                bar = self.format_meter(self.n, self.total, elapsed,
                                        (self.dynamic_ncols(self.fp) if self.dynamic_ncols else self.ncols), self.desc,
                                        self.ascii, self.unit, self.unit_scale,
                                        1 / self.avg_time if self.avg_time else None, self.bar_format)
                proxies_found = " Collected good proxies: {}".format(self.get_number_of_good_proxies())
                final_bar = bar + proxies_found
                self.sp(final_bar)

                if self.pos:
                    self.moveto(-self.pos)

                # If no `miniters` was specified, adjust automatically to the
                # maximum iteration rate seen so far.
                # e.g.: After running `tqdm.update(5)`, subsequent
                # calls to `tqdm.update()` will only cause an update after
                # at least 5 more iterations.
                if self.dynamic_miniters:
                    if self.maxinterval and delta_t > self.maxinterval:
                        self.miniters = self.miniters * self.maxinterval \
                                        / delta_t
                    elif self.mininterval and delta_t:
                        self.miniters = self.smoothing * delta_it \
                                        * self.mininterval / delta_t + \
                                        (1 - self.smoothing) * self.miniters
                    else:
                        self.miniters = self.smoothing * delta_it + \
                                        (1 - self.smoothing) * self.miniters

                # Store old values for next call
                self.last_print_n = self.n
                self.last_print_t = cur_t
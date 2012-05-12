#include "random.h"

// RAND_MAX is guaranteed to be at least 32767
// but math with rand() is annoying.
// Here's a canned solution from
// http://www.azillionmonkeys.com/qed/random.html
// which gives uniform numbers in [0, r)

#define RS_SCALE (1.0 / (1.0 + RAND_MAX))

double drand (void) {
    double d;
    do {
       d = (((random() * RS_SCALE) + random()) * RS_SCALE + random()) * RS_SCALE;
    } while (d >= 1); /* Round off */
    return d;
}

// use this to construct a 32-bit thread-safe RNG
#define RAND32 ((uint32_t)irand(1ul<<32))
uint32_t random32() {
    return RAND32;
}

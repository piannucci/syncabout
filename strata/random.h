#include <cstdlib>
#include <stdint.h>

double drand (void);
#define irand(x) ((unsigned int) ((x) * drand()))
uint32_t random32();

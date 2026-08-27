#include <stdio.h>

#if !defined(__x86_64__) || defined(__ILP32__)
#error "This probe must be compiled for the x86_64 Linux ABI"
#endif

_Static_assert(sizeof(void *) == 8, "The Rosetta probe requires 64-bit pointers");

int main(void) {
    return puts("evolution-x86_64-probe-ok") == EOF ? 1 : 0;
}
